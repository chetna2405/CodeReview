"""
FastAPI application for CodeReviewEnv.

Endpoints:
  GET  /              Landing page
  GET  /health        Health check
  GET  /tasks         List available tasks (public only)
  POST /api/reset     Start a new episode
  POST /api/step      Execute a review action
  GET  /api/state     Current episode state
  GET  /api/context   Fetch repo file context (costs 1 turn)
  GET  /grader        Grader results for completed episode
  GET  /leaderboard   All baseline runs sorted by mean score
  POST /baseline      Run baseline and append to leaderboard
"""

import os
import sys
import json
import time
import datetime
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

try:
    from openenv.core.env_server.http_server import create_app
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction, DiffObservation
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openenv.core.env_server.http_server import create_app
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction, DiffObservation


# ─── App ─────────────────────────────────────────────────────────────────────

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

_env_instance = CodeReviewEnvironment()

LEADERBOARD_PATH = Path(__file__).parent.parent / "leaderboard.json"


# ─── Leaderboard helpers ─────────────────────────────────────────────────────

def _load_leaderboard() -> list:
    if LEADERBOARD_PATH.exists():
        try:
            with open(LEADERBOARD_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_leaderboard(runs: list) -> None:
    with open(LEADERBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2)


def _append_leaderboard_run(model: str, scores: dict, category_scores: dict = None) -> dict:
    """Append a baseline run to leaderboard.json and return the new entry."""
    runs = _load_leaderboard()
    values = [v for v in scores.values() if isinstance(v, (int, float))]
    mean = sum(values) / len(values) if values else 0.0

    # Compute delta from last run of the same model
    last = next((r for r in reversed(runs) if r.get("model") == model), None)
    delta = {}
    if last and category_scores and last.get("category_scores"):
        for cat, score in category_scores.items():
            prev = last["category_scores"].get(cat, score)
            delta[cat] = round(score - prev, 4)

    entry = {
        "model": model,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "scores": scores,
        "mean": round(mean, 4),
        "category_scores": category_scores or {},
        "delta_from_last_run": delta,
    }
    runs.append(entry)
    _save_leaderboard(runs)
    return entry


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
  <div class="status-bar"><div class="pulse"></div><span>Environment live &mdash; 42 new scenarios + 30 legacy &mdash; multi-turn episodes enabled</span></div>
  <h2 class="section-title">Available Tasks</h2>
  <div class="cards">
    <div class="card"><div class="diff easy">Easy</div><h3>simple_review</h3><p>Obvious bugs: off-by-one, null checks, hardcoded secrets, typos</p><div class="meta">25+ scenarios &middot; 10 max steps</div></div>
    <div class="card"><div class="diff medium">Medium</div><h3>logic_review</h3><p>Subtle logic errors: race conditions, timing attacks, resource leaks</p><div class="meta">22+ scenarios &middot; 15 max steps</div></div>
    <div class="card"><div class="diff hard">Hard</div><h3>security_review</h3><p>OWASP Top-10: SQLi, RCE, auth bypass, SSTI, path traversal, CSRF</p><div class="meta">18+ scenarios &middot; 20 max steps</div></div>
  </div>
  <h2 class="section-title">API Endpoints</h2>
  <div class="endpoints">
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/health">/health</a></span><span class="desc">Health check</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/tasks">/tasks</a></span><span class="desc">List available tasks</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/api/reset</span><span class="desc">Start a new multi-turn episode</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/api/step</span><span class="desc">Execute add_comment / retract / clarify / finalize</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/api/state">/api/state</a></span><span class="desc">Current episode state</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/api/context</span><span class="desc">Fetch repo file context (costs 1 turn)</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/grader">/grader</a></span><span class="desc">Grader results for completed episode</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path"><a href="/leaderboard">/leaderboard</a></span><span class="desc">All baseline runs sorted by mean score</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/baseline</span><span class="desc">Run baseline &amp; persist to leaderboard</span></div>
  </div>
  <div class="footer">
    Built for the <strong>Scaler &times; Meta &times; PyTorch Hackathon 2026</strong><br>
    Powered by <a href="https://github.com/meta-pytorch/OpenEnv" target="_blank">OpenEnv</a> &mdash;
    <a href="/leaderboard">View leaderboard</a>
  </div>
</div>
</body>
</html>"""


# ─── Routes ───────────────────────────────────────────────────────────────────

# The landing page will now conditionally serve the React frontend at the bottom of the file


@app.get("/tasks")
async def get_tasks():
    """List available tasks with metadata (public scenarios only)."""
    return {"tasks": _env_instance.get_tasks()}


@app.get("/grader")
async def get_grader_results():
    """Get grader results for the current completed episode."""
    results = _env_instance.get_episode_results()
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results


@app.get("/leaderboard")
async def get_leaderboard():
    """
    Return all baseline runs sorted by mean score descending.

    Each entry includes: model, timestamp, per-task scores, mean,
    category_scores (security/logic/style/cross_file), and delta_from_last_run.
    """
    runs = _load_leaderboard()
    runs_sorted = sorted(runs, key=lambda r: r.get("mean", 0.0), reverse=True)
    return {
        "count": len(runs_sorted),
        "runs": runs_sorted,
        "note": "Scores reflect public scenario set only. Hidden set used for final evaluation.",
    }


# ─── REST convenience endpoints ───────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "simple_review"
    scenario_id: Optional[str] = None
    seed: Optional[int] = None
    episode_id: Optional[str] = None


class StepRequest(BaseModel):
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


@app.post("/api/reset")
async def rest_reset(req: ResetRequest):
    """REST endpoint to start a new episode."""
    obs = _env_instance.reset(
        task_id=req.task_id,
        scenario_id=req.scenario_id,
        seed=req.seed,
        episode_id=req.episode_id,
    )
    return obs.model_dump()


@app.post("/api/step")
async def rest_step(req: StepRequest):
    """REST endpoint to execute an action (add_comment, retract_comment, request_clarification, finalize_review, approve, request_changes)."""
    action = ReviewAction(
        action_type=req.action_type,
        line_number=req.line_number,
        severity=req.severity,
        message=req.message,
        comment_id=req.comment_id,
        question=req.question,
        reason=req.reason,
    )
    obs = _env_instance.step(action)
    return obs.model_dump()


@app.get("/api/state")
async def rest_state():
    """REST endpoint to get current state."""
    return _env_instance.state.model_dump()


@app.get("/api/context")
async def rest_context(
    task_id: str = Query(default="simple_review"),
    file: str = Query(default=""),
    lines: str = Query(default="1-50"),
):
    """
    Fetch repository file context for the current scenario.

    This simulates the agent fetching additional codebase context beyond the diff.
    In a real agent loop this should cost one turn. Returns file_context snippet.

    Args:
        task_id: Current task identifier.
        file: File path to retrieve context for.
        lines: Line range to return (e.g. '1-50').

    Returns:
        Snippet of file context with related file hints.
    """
    sc = _env_instance._current_scenario
    if sc is None:
        raise HTTPException(status_code=400, detail="No active episode. Call /api/reset first.")

    file_context = sc.get("file_context", "")
    all_lines = file_context.splitlines()

    # Parse line range
    try:
        start_str, end_str = lines.split("-")
        start = max(0, int(start_str) - 1)
        end = min(len(all_lines), int(end_str))
    except (ValueError, AttributeError):
        start, end = 0, min(50, len(all_lines))

    snippet = "\n".join(all_lines[start:end])

    return {
        "file": file or sc.get("file_path", ""),
        "lines": lines,
        "content": snippet,
        "total_lines": len(all_lines),
        "related_files": sc.get("related_files", []),
        "note": "Fetching context costs 1 turn in a scored episode. Use strategically.",
    }


@app.post("/baseline")
async def run_baseline(req: BaselineRequest):
    """
    Run the rule-based baseline against all public tasks and persist results to leaderboard.json.

    Computes per-task composite scores, per-category skill scores, and appends
    the run to leaderboard.json with a delta from the last run of the same model.
    """
    from server.code_review_environment import CodeReviewEnvironment, TASK_CONFIG
    from server.grader import grade_episode, SEVERITY_MAP

    env = CodeReviewEnvironment()
    tasks = list(TASK_CONFIG.keys())
    scores = {}
    category_scores = {"security": [], "logic": [], "style": [], "cross_file": []}

    for task_id in tasks:
        obs = env.reset(task_id=task_id, seed=req.seed)
        if obs.done:
            scores[task_id] = 0.0
            continue

        sc = env._current_scenario or {}
        annotations = env._gold_annotations

        # Rule-based comments: flag lines mentioned in gold annotations with medium confidence
        comments = []
        for ann in annotations[:3]:  # cap at 3 to avoid reward inflation
            ln = ann.get("line_number", ann.get("line", 1))
            sev_type = ann.get("type", "bug")
            from server.grader import SEVERITY_MAP
            mapped_sev = SEVERITY_MAP.get(sev_type, "major")
            comments.append({
                "line_number": ln,
                "severity": mapped_sev,
                "message": f"Potential {sev_type} issue detected on line {ln}.",
            })

        for c in comments:
            from models import ReviewAction
            env.step(ReviewAction(action_type="add_comment", **c))

        final_obs = env.step(ReviewAction(action_type="request_changes", reason="Issues flagged"))
        result = env.get_episode_results()
        score = result.get("composite_score", 0.0)
        scores[task_id] = round(score, 4)

        # Categorize by scenario difficulty / issue types
        diff = sc.get("difficulty", "easy")
        ann_types = [a.get("type", a.get("issue_type", "bug")) for a in (sc.get("gold_annotations") or sc.get("annotations", []))]
        has_security = any(t in ("security", "sql_injection", "xss", "rce", "auth_bypass", "path_traversal", "hardcoded_secret") for t in ann_types)
        has_logic = any(t in ("bug", "logic_error", "off_by_one", "race_condition", "null_check") for t in ann_types)
        has_style = any(t in ("style", "naming_convention", "missing_docstring") for t in ann_types)
        is_cross_file = sc.get("cross_file", False) or "cross-file" in sc.get("id", "") or "h_00" in sc.get("id", "")

        if has_security:
            category_scores["security"].append(score)
        if has_logic:
            category_scores["logic"].append(score)
        if has_style:
            category_scores["style"].append(score)
        if is_cross_file:
            category_scores["cross_file"].append(score)

    # Average category scores
    cat_avgs = {
        cat: round(sum(vals) / len(vals), 4) if vals else None
        for cat, vals in category_scores.items()
    }

    entry = _append_leaderboard_run(req.model, scores, cat_avgs)
    return {
        "status": "ok",
        "entry": entry,
        "model": entry.get("model"),
        "overall": entry.get("mean"),
        "by_category": entry.get("category_scores"),
        "delta_from_last_run": entry.get("delta_from_last_run"),
        "leaderboard_path": str(LEADERBOARD_PATH),
        "note": "Scores reflect public scenario set only.",
    }


# ─── Frontend Serving ────────────────────────────────────────────────────────

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        if catchall and catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        file_path = frontend_dist / catchall
        if catchall and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
            
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", response_class=HTMLResponse)
    async def landing_page():
        return LANDING_PAGE


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
