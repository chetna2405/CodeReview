"""
FastAPI application for CodeReviewEnv.

Architecture improvements vs. previous version:
  - Session-isolated environments via SessionManager (no global singleton)
  - Async author persona via httpx.AsyncClient (non-blocking event loop)
  - SQLite leaderboard with WAL mode (concurrent-safe, survives redeployment)
  - Structured logging middleware with per-request IDs
  - Bounded replay store with TTL eviction (max 1000 episodes, 2h TTL)

Endpoints:
  GET  /              Landing page (or React SPA if built)
  GET  /health        Rich health: uptime, sessions, scores, component status
  GET  /tasks         List available tasks
  POST /api/reset     Start a new episode
  POST /api/step      Execute a review action (validated)
  GET  /api/state     Current episode state (requires X-Episode-ID header)
  GET  /api/context   File context snippet
  GET  /api/replay/{episode_id}  Turn-by-turn replay
  GET  /grader        Grader results for an episode
  GET  /leaderboard   All runs sorted by mean score
  POST /baseline      Rule-based baseline + persist to leaderboard
"""

from __future__ import annotations

import asyncio
import datetime
import os
import sys
import time as _time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─── Structured logging ───────────────────────────────────────────────────────

try:
    import structlog
    _logger = structlog.get_logger("codereviewenv")

    def _log(level: str, event: str, **kwargs) -> None:
        getattr(_logger, level)(event, **kwargs)

except ImportError:
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _stdlib_logger = _logging.getLogger("codereviewenv")

    def _log(level: str, event: str, **kwargs) -> None:
        _stdlib_logger.info(f"{event} {kwargs}")


# ─── Internal imports ─────────────────────────────────────────────────────────

try:
    from openenv.core.env_server.http_server import create_app
    from server.code_review_environment import CodeReviewEnvironment, TASK_CONFIG, _get_scenarios
    from server.session_manager import session_manager
    from server.leaderboard_db import leaderboard_db
    from models import ReviewAction, DiffObservation
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openenv.core.env_server.http_server import create_app
    from server.code_review_environment import CodeReviewEnvironment, TASK_CONFIG, _get_scenarios
    from server.session_manager import session_manager
    from server.leaderboard_db import leaderboard_db
    from models import ReviewAction, DiffObservation


# ─── App factory ─────────────────────────────────────────────────────────────

app = create_app(
    CodeReviewEnvironment,
    ReviewAction,
    DiffObservation,
    env_name="code_review_env",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Structured logging middleware (H4) ────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = _time.monotonic()
    response = await call_next(request)
    latency_ms = round((_time.monotonic() - start) * 1000, 1)
    _log(
        "info",
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Metrics counters ─────────────────────────────────────────────────────────

_start_time: float = _time.time()
_episodes_started: int = 0
_episodes_completed: int = 0
_composite_scores: List[float] = []


# ─── Bounded replay store with TTL eviction (H5) ─────────────────────────────

MAX_REPLAY_EPISODES = 1000
_REPLAY_TTL_SECONDS = 7200  # 2 hours


class _ReplayEntry:
    __slots__ = ("turns", "created_at")

    def __init__(self) -> None:
        self.turns: List[dict] = []
        self.created_at: float = _time.monotonic()

    @property
    def age_seconds(self) -> float:
        return _time.monotonic() - self.created_at


_replay_store: OrderedDict[str, _ReplayEntry] = OrderedDict()


def _replay_get_or_create(episode_id: str) -> _ReplayEntry:
    _evict_old_replays()
    if episode_id not in _replay_store:
        if len(_replay_store) >= MAX_REPLAY_EPISODES:
            _replay_store.popitem(last=False)  # evict oldest
        _replay_store[episode_id] = _ReplayEntry()
    _replay_store.move_to_end(episode_id)
    return _replay_store[episode_id]


def _evict_old_replays() -> None:
    expired = [eid for eid, e in _replay_store.items() if e.age_seconds > _REPLAY_TTL_SECONDS]
    for eid in expired:
        del _replay_store[eid]


# ─── Request/response models ─────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "simple_review"
    scenario_id: Optional[str] = None
    seed: Optional[int] = None
    episode_id: Optional[str] = None


class StepRequest(BaseModel):
    episode_id: Optional[str] = None  # Preferred: from body
    action_type: str = "add_comment"
    line_number: Optional[int] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    comment_id: Optional[str] = None
    question: Optional[str] = None
    reason: Optional[str] = None


class BaselineRequest(BaseModel):
    model: str = "rule-based"
    seed: int = 42


import asyncio
MAX_CONCURRENT_STEPS = int(os.environ.get("MAX_CONCURRENT_STEPS", "32"))
step_semaphore = None

@app.on_event("startup")
async def startup_event():
    global step_semaphore
    step_semaphore = asyncio.Semaphore(MAX_CONCURRENT_STEPS)
    # Warm the model on first startup, not at build time
    try:
        from server.grader import get_grader
        _ = get_grader()
    except Exception as e:
        _log("warning", f"Failed to warm up grader at startup: {e}")

# ─── Health endpoint ─────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Rich health endpoint with component status, uptime, and episode metrics."""
    # Component health checks
    grader_ok = True
    try:
        from server.grader import grade_episode
    except Exception:
        grader_ok = False

    db_ok = True
    try:
        leaderboard_db.get_all_runs()
    except Exception:
        db_ok = False

    return {
        "status": "ok" if (grader_ok and db_ok) else "degraded",
        "components": {
            "grader": "ok" if grader_ok else "error",
            "leaderboard_db": "ok" if db_ok else "error",
            "session_manager": "ok",
        },
        "uptime_seconds": round(_time.time() - _start_time, 1),
        "active_sessions": session_manager.active_count,
        "total_episodes_started": _episodes_started,
        "total_episodes_completed": _episodes_completed,
        "mean_composite_score": (
            round(sum(_composite_scores) / len(_composite_scores), 4)
            if _composite_scores else None
        ),
        "replay_episodes_stored": len(_replay_store),
        "scenarios_loaded": {
            task_id: len(_get_scenarios(task_id)) for task_id in TASK_CONFIG
        },
        "hf_token_present": bool(
            os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        ),
    }


# ─── Tasks endpoint ───────────────────────────────────────────────────────────

@app.get("/tasks")
async def get_tasks():
    """List available tasks with metadata (public scenarios only)."""
    env = CodeReviewEnvironment()
    return {"tasks": env.get_tasks()}


# ─── Episode endpoints (session-isolated) ─────────────────────────────────────

@app.post("/api/reset")
async def rest_reset(req: ResetRequest, request: Request):
    """Start a new episode. Returns episode_id in metadata for session routing."""
    global _episodes_started
    _episodes_started += 1

    # Use provided episode_id or generate a fresh one
    episode_id = req.episode_id or str(uuid.uuid4())[:16]

    env = session_manager.get_or_create(episode_id)
    obs = env.reset(
        task_id=req.task_id,
        scenario_id=req.scenario_id,
        seed=req.seed,
        episode_id=episode_id,
    )
    obs_dict = obs.model_dump()

    # Ensure episode_id is always in the response metadata
    if "metadata" not in obs_dict or not obs_dict.get("metadata"):
        obs_dict["metadata"] = {}
    obs_dict["metadata"]["episode_id"] = episode_id

    # Initialize replay entry
    _replay_get_or_create(episode_id)

    _log("info", "episode_reset",
         episode_id=episode_id, task_id=req.task_id, seed=req.seed)
    return obs_dict


@app.post("/api/step")
async def rest_step(req: StepRequest, request: Request):
    """Execute action on episode and get next observation."""
    if step_semaphore is not None and step_semaphore.locked():
        return JSONResponse(
            status_code=503,
            content={
                "error": "server_at_capacity", 
                "message": "Thread pool saturated. Please retry later.",
                "retry_after_seconds": 2
            },
            headers={"Retry-After": "2"}
        )
    global _episodes_completed

    # Resolve episode_id — body field takes priority, then header
    episode_id = req.episode_id or request.headers.get("X-Episode-ID", "")
    if not episode_id:
        raise HTTPException(
            status_code=400,
            detail="episode_id required in request body or X-Episode-ID header",
        )

    # ── Input validation ──────────────────────────────────────────────────────
    if req.action_type == "add_comment":
        errors: List[str] = []
        if req.line_number is None or req.line_number < 1:
            errors.append("line_number must be >= 1")
        if req.severity not in (None, "minor", "major", "critical", "nit"):
            errors.append(
                f"severity must be: minor | major | critical | nit. Got: {req.severity!r}"
            )
        if not req.message or not req.message.strip():
            errors.append("message must not be empty")
        elif len(req.message) > 500:
            errors.append("message must be <= 500 characters")
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

    env = session_manager.get(episode_id)
    if env is None:
        raise HTTPException(
            status_code=410,
            detail={
                "error": "session_expired",
                "message": "Episode session not found. Call /api/reset to start a new episode.",
                "episode_id": episode_id
            }
        )
    action = ReviewAction(
        action_type=req.action_type,
        line_number=req.line_number,
        severity=req.severity,
        message=req.message,
        comment_id=req.comment_id,
        question=req.question,
        reason=req.reason,
    )
    import anyio
    
    async with step_semaphore: # type: ignore
        obs = await anyio.to_thread.run_sync(env.step, action)
    
    obs_dict = obs.model_dump()

    # Ensure episode_id propagates
    if "metadata" not in obs_dict or not obs_dict.get("metadata"):
        obs_dict["metadata"] = {}
    obs_dict["metadata"]["episode_id"] = episode_id

    # ── Record replay turn ────────────────────────────────────────────────────
    author_responses = obs_dict.get("author_responses", [])
    entry = _replay_get_or_create(episode_id)
    entry.turns.append({
        "turn": obs_dict.get("step_num", 0),
        "action_type": req.action_type,
        "line_number": req.line_number,
        "severity": req.severity,
        "message": req.message,
        "author_response": author_responses[-1] if author_responses else None,
        "reward": obs_dict.get("reward", 0.0),
        "is_done": obs_dict.get("done", False),
    })

    # ── Track metrics ─────────────────────────────────────────────────────────
    if obs_dict.get("done"):
        _episodes_completed += 1
        _composite_scores.append(obs_dict.get("reward", 0.0))
        _log("info", "episode_complete",
             episode_id=episode_id, reward=obs_dict.get("reward", 0.0))

    return obs_dict


@app.get("/api/state")
async def rest_state(
    request: Request,
    episode_id: Optional[str] = Query(default=None),
):
    """Get current state for an episode. Pass episode_id as query param or X-Episode-ID header."""
    eid = episode_id or request.headers.get("X-Episode-ID", "")
    if not eid:
        raise HTTPException(
            status_code=400,
            detail="episode_id required as query param or X-Episode-ID header",
        )
    env = session_manager.get(eid)
    if env is None:
        raise HTTPException(
            status_code=410,
            detail={
                "error": "session_expired",
                "message": "Episode session not found. Call /api/reset to start a new episode.",
                "episode_id": eid
            }
        )
    return env.state.model_dump()


@app.get("/api/replay/{episode_id}")
async def get_replay(episode_id: str):
    """Turn-by-turn replay for any episode (bounded store, 2h TTL)."""
    if episode_id not in _replay_store:
        raise HTTPException(status_code=404, detail=f"Episode '{episode_id}' not found")
    return {
        "episode_id": episode_id,
        "turns": _replay_store[episode_id].turns,
        "turn_count": len(_replay_store[episode_id].turns),
    }


@app.get("/api/context")
async def rest_context(
    request: Request,
    episode_id: Optional[str] = Query(default=None),
    task_id: str = Query(default="simple_review"),
    file: str = Query(default=""),
    lines: str = Query(default="1-50"),
):
    """File context snippet for the active episode."""
    eid = episode_id or request.headers.get("X-Episode-ID", "")
    if not eid:
        # Fallback for clients that don't send episode_id
        raise HTTPException(
            status_code=400,
            detail="episode_id required as query param or X-Episode-ID header",
        )
    env = session_manager.get(eid)
    if env is None:
        raise HTTPException(
            status_code=410,
            detail={
                "error": "session_expired",
                "message": "Episode session not found. Call /api/reset to start a new episode.",
                "episode_id": eid
            }
        )

    sc = env._current_scenario
    if sc is None:
        raise HTTPException(status_code=400, detail="No active scenario. Call /api/reset first.")

    file_context = sc.get("file_context", "")
    all_lines = file_context.splitlines()

    try:
        start_str, end_str = lines.split("-")
        start = max(0, int(start_str) - 1)
        end = min(len(all_lines), int(end_str))
    except (ValueError, AttributeError):
        start, end = 0, min(50, len(all_lines))

    return {
        "file": file or sc.get("file_path", ""),
        "lines": lines,
        "content": "\n".join(all_lines[start:end]),
        "total_lines": len(all_lines),
        "related_files": sc.get("related_files", []),
        "note": "Fetching context costs 1 turn in a scored episode.",
    }


@app.get("/grader")
async def get_grader_results(
    request: Request,
    episode_id: Optional[str] = Query(default=None),
):
    """Grader results for a completed episode."""
    eid = episode_id or request.headers.get("X-Episode-ID", "")
    if not eid:
        raise HTTPException(
            status_code=400,
            detail="episode_id required as query param or X-Episode-ID header",
        )
    env = session_manager.get(eid)
    if env is None:
        raise HTTPException(status_code=404, detail=f"Episode '{eid}' not found")
    results = env.get_episode_results()
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results


# ─── Leaderboard (SQLite-backed) ──────────────────────────────────────────────

@app.get("/leaderboard")
async def get_leaderboard():
    """All baseline runs sorted by mean score descending (from SQLite)."""
    runs = leaderboard_db.get_all_runs()
    return {
        "count": len(runs),
        "runs": runs,
        "note": "Scores reflect public scenario set only. Hidden set used for final evaluation.",
    }


@app.post("/baseline")
async def run_baseline(req: BaselineRequest):
    """
    Run the rule-based baseline against all public tasks.
    Each task uses a fresh isolated CodeReviewEnvironment instance.
    Results are persisted to the SQLite leaderboard.
    """
    from server.grader import SEVERITY_MAP

    tasks = list(TASK_CONFIG.keys())
    scores: dict[str, float] = {}
    category_scores: dict[str, list] = {
        "security": [], "logic": [], "style": [], "cross_file": []
    }

    for task_id in tasks:
        # Fresh isolated env per task — no shared state
        env = CodeReviewEnvironment()
        obs = env.reset(task_id=task_id, seed=req.seed)
        if obs.done:
            scores[task_id] = 0.0
            continue

        sc = env._current_scenario or {}
        annotations = env._gold_annotations

        comments = []
        for ann in annotations[:3]:
            ln = ann.get("line_number", ann.get("line", 1))
            sev_type = ann.get("type", "bug")
            comments.append({
                "line_number": ln,
                "severity": SEVERITY_MAP.get(sev_type, "major"),
                "message": f"Potential {sev_type} issue detected on line {ln}.",
            })

        for c in comments:
            env.step(ReviewAction(action_type="add_comment", **c))

        env.step(ReviewAction(action_type="request_changes", reason="Issues flagged"))
        result = env.get_episode_results()
        score = result.get("composite_score", 0.0)
        scores[task_id] = round(score, 4)

        ann_types = [
            a.get("type", a.get("issue_type", "bug"))
            for a in (sc.get("gold_annotations") or sc.get("annotations", []))
        ]
        sec_types = {"security", "sql_injection", "xss", "rce", "auth_bypass",
                     "path_traversal", "hardcoded_secret"}
        logic_types = {"bug", "logic_error", "off_by_one", "race_condition", "null_check"}
        style_types = {"style", "naming_convention", "missing_docstring"}

        if any(t in sec_types for t in ann_types):
            category_scores["security"].append(score)
        if any(t in logic_types for t in ann_types):
            category_scores["logic"].append(score)
        if any(t in style_types for t in ann_types):
            category_scores["style"].append(score)
        if sc.get("cross_file", False) or "cross-file" in sc.get("id", ""):
            category_scores["cross_file"].append(score)

    cat_avgs = {
        cat: round(sum(vals) / len(vals), 4) if vals else None
        for cat, vals in category_scores.items()
    }

    entry = leaderboard_db.append_run(req.model, scores, cat_avgs)
    _log("info", "baseline_complete", model=req.model, mean=entry["mean"])
    return {
        "status": "ok",
        "entry": entry,
        "model": entry["model"],
        "overall": entry["mean"],
        "by_category": entry["category_scores"],
        "delta_from_last_run": entry["delta_from_last_run"],
        "note": "Scores reflect public scenario set only.",
    }


# ─── Landing page ─────────────────────────────────────────────────────────────

LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeReviewEnv</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', system-ui, sans-serif; background: #0a0a1a; color: #e2e8f0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
  .container { max-width: 920px; width: 100%; padding: 40px 24px; }
  .hero { text-align: center; padding: 60px 0 40px; }
  .hero h1 { font-size: 2.8rem; font-weight: 700; background: linear-gradient(135deg, #818cf8, #6ee7b7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px; }
  .badge { display: inline-block; background: rgba(110,231,183,.15); color: #6ee7b7; padding: 4px 14px; border-radius: 20px; font-size: .8rem; font-weight: 500; letter-spacing: .5px; margin-bottom: 16px; border: 1px solid rgba(110,231,183,.3); }
  .hero p { color: #94a3b8; font-size: 1.1rem; line-height: 1.6; max-width: 620px; margin: 0 auto; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr)); gap: 16px; margin: 32px 0; }
  .card { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); border-radius: 12px; padding: 24px; transition: all .2s; }
  .card:hover { border-color: rgba(129,140,248,.4); background: rgba(129,140,248,.06); transform: translateY(-2px); }
  .card .diff { font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .diff.easy { color: #6ee7b7; } .diff.medium { color: #fbbf24; } .diff.hard { color: #f87171; }
  .card h3 { font-size: 1.1rem; margin-bottom: 6px; color: #f1f5f9; }
  .card p { font-size: .85rem; color: #94a3b8; line-height: 1.5; }
  .card .meta { margin-top: 12px; font-size: .75rem; color: #64748b; }
  .section-title { font-size: 1.3rem; font-weight: 600; margin: 40px 0 16px; color: #f1f5f9; }
  .endpoints { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.06); border-radius: 12px; overflow: hidden; }
  .endpoint { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid rgba(255,255,255,.04); transition: background .15s; }
  .endpoint:last-child { border-bottom: none; }
  .endpoint:hover { background: rgba(255,255,255,.03); }
  .method { font-size: .7rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; min-width: 48px; text-align: center; font-family: monospace; }
  .method.get { background: rgba(110,231,183,.15); color: #6ee7b7; }
  .method.post { background: rgba(129,140,248,.15); color: #818cf8; }
  .path { font-family: monospace; font-size: .9rem; color: #e2e8f0; flex: 1; }
  .desc { font-size: .8rem; color: #64748b; }
  .status-bar { display: flex; align-items: center; gap: 8px; margin: 32px 0; padding: 16px 20px; background: rgba(110,231,183,.08); border: 1px solid rgba(110,231,183,.2); border-radius: 10px; }
  .pulse { width: 8px; height: 8px; background: #6ee7b7; border-radius: 50%; animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity:1; box-shadow:0 0 0 0 rgba(110,231,183,.4); } 50% { opacity:.8; box-shadow:0 0 0 8px rgba(110,231,183,0); } }
  .status-bar span { font-size: .85rem; color: #6ee7b7; font-weight: 500; }
  .footer { text-align: center; padding: 40px 0; color: #475569; font-size: .8rem; }
  .footer a, a { color: #818cf8; text-decoration: none; }
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div class="badge">OPENENV ENVIRONMENT</div>
    <h1>CodeReviewEnv</h1>
    <p>AI code review benchmarking. Agents review PR diffs, flag bugs, classify severity, debate with a simulated author &mdash; graded against expert annotations.</p>
  </div>
  <div class="status-bar"><div class="pulse"></div><span>Session-isolated · SQLite leaderboard · Async persona LLM · Structured logging</span></div>
  <h2 class="section-title">Available Tasks</h2>
  <div class="cards">
    <div class="card"><div class="diff easy">Easy</div><h3>simple_review</h3><p>Obvious bugs: off-by-one, null checks, hardcoded secrets, typos</p><div class="meta">15+ scenarios &middot; 10 max steps</div></div>
    <div class="card"><div class="diff medium">Medium</div><h3>logic_review</h3><p>Subtle logic errors: race conditions, timing attacks, resource leaks</p><div class="meta">12+ scenarios &middot; 15 max steps</div></div>
    <div class="card"><div class="diff hard">Hard</div><h3>security_review</h3><p>OWASP Top-10: SQLi, RCE, auth bypass, SSTI, path traversal, CSRF</p><div class="meta">11+ scenarios &middot; 20 max steps</div></div>
  </div>
  <h2 class="section-title">API Endpoints</h2>
  <div class="endpoints">
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/health">/health</a></span><span class="desc">Component health + uptime</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/tasks">/tasks</a></span><span class="desc">List available tasks</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/api/reset</span><span class="desc">Start a session-isolated episode</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/api/step</span><span class="desc">Execute action (episode_id in body)</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/api/state?episode_id=</span><span class="desc">Episode state</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/api/context?episode_id=</span><span class="desc">File context snippet</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/api/replay/{episode_id}</span><span class="desc">Turn-by-turn replay (TTL-bounded)</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/grader">/grader?episode_id=</a></span><span class="desc">Grader results</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/leaderboard">/leaderboard</a></span><span class="desc">All runs (SQLite)</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/baseline</span><span class="desc">Run baseline + persist</span></div>
  </div>
  <div class="footer">
    Built for the <strong>Scaler &times; Meta &times; PyTorch Hackathon 2026</strong><br>
    Powered by <a href="https://github.com/meta-pytorch/OpenEnv" target="_blank">OpenEnv</a> &mdash;
    <a href="/leaderboard">View leaderboard</a>
  </div>
</div>
</body>
</html>"""


# ─── React SPA serving ───────────────────────────────────────────────────────

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        if catchall and (
            catchall.startswith("api/")
            or catchall in ("health", "tasks", "grader", "leaderboard", "baseline")
        ):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = frontend_dist / catchall
        if catchall and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(
            frontend_dist / "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

else:
    @app.get("/", response_class=HTMLResponse)
    async def landing_page():
        return LANDING_PAGE


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        access_log=False,  # Handled by our structured logging middleware
    )


if __name__ == "__main__":
    main()
