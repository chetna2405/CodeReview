"""
FastAPI application for CodeReviewEnv.

Uses OpenEnv's create_app helper for standard HTTP/WebSocket endpoints,
plus custom REST routes for tasks, grader, and baseline inference.
"""

import os
import sys
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

# Handle imports for both package and standalone modes
try:
    from openenv.core.env_server.http_server import create_app
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction, DiffObservation
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openenv.core.env_server.http_server import create_app
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction, DiffObservation


# ─── Create app using OpenEnv's create_app ────────────────────────────────────

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


# ─── Additional custom endpoints ─────────────────────────────────────────────

# We need a standalone instance for custom endpoints
_env_instance = CodeReviewEnvironment()


LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeReviewEnv</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #0a0a1a;
    color: #e2e8f0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .container { max-width: 900px; width: 100%; padding: 40px 24px; }
  .hero {
    text-align: center;
    padding: 60px 0 40px;
  }
  .hero h1 {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8, #6ee7b7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
  }
  .hero .badge {
    display: inline-block;
    background: rgba(110, 231, 183, 0.15);
    color: #6ee7b7;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.5px;
    margin-bottom: 16px;
    border: 1px solid rgba(110, 231, 183, 0.3);
  }
  .hero p {
    color: #94a3b8;
    font-size: 1.1rem;
    line-height: 1.6;
    max-width: 600px;
    margin: 0 auto;
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin: 32px 0;
  }
  .card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 24px;
    transition: all 0.2s;
  }
  .card:hover {
    border-color: rgba(129, 140, 248, 0.4);
    background: rgba(129, 140, 248, 0.06);
    transform: translateY(-2px);
  }
  .card .difficulty {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }
  .card .difficulty.easy { color: #6ee7b7; }
  .card .difficulty.medium { color: #fbbf24; }
  .card .difficulty.hard { color: #f87171; }
  .card h3 { font-size: 1.1rem; margin-bottom: 6px; color: #f1f5f9; }
  .card p { font-size: 0.85rem; color: #94a3b8; line-height: 1.5; }
  .card .scenarios {
    margin-top: 12px;
    font-size: 0.75rem;
    color: #64748b;
  }
  .section-title {
    font-size: 1.3rem;
    font-weight: 600;
    margin: 40px 0 16px;
    color: #f1f5f9;
  }
  .endpoints {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    overflow: hidden;
  }
  .endpoint {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.15s;
  }
  .endpoint:last-child { border-bottom: none; }
  .endpoint:hover { background: rgba(255,255,255,0.03); }
  .method {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    min-width: 48px;
    text-align: center;
    font-family: 'SF Mono', monospace;
  }
  .method.get { background: rgba(110,231,183,0.15); color: #6ee7b7; }
  .method.post { background: rgba(129,140,248,0.15); color: #818cf8; }
  .path {
    font-family: 'SF Mono', Consolas, monospace;
    font-size: 0.9rem;
    color: #e2e8f0;
    flex: 1;
  }
  .desc { font-size: 0.8rem; color: #64748b; }
  .status-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 32px 0;
    padding: 16px 20px;
    background: rgba(110, 231, 183, 0.08);
    border: 1px solid rgba(110, 231, 183, 0.2);
    border-radius: 10px;
  }
  .pulse {
    width: 8px; height: 8px;
    background: #6ee7b7;
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(110,231,183,0.4); }
    50% { opacity: 0.8; box-shadow: 0 0 0 8px rgba(110,231,183,0); }
  }
  .status-bar span { font-size: 0.85rem; color: #6ee7b7; font-weight: 500; }
  .footer {
    text-align: center;
    padding: 40px 0;
    color: #475569;
    font-size: 0.8rem;
  }
  .footer a { color: #818cf8; text-decoration: none; }
  a { color: #818cf8; }
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div class="badge">OPENENV ENVIRONMENT</div>
    <h1>CodeReviewEnv</h1>
    <p>AI code review benchmarking environment. Agents review PR diffs, flag bugs, classify severity, and produce review comments &mdash; graded against expert annotations.</p>
  </div>

  <div class="status-bar">
    <div class="pulse"></div>
    <span>Environment is live and accepting connections</span>
  </div>

  <h2 class="section-title">Available Tasks</h2>
  <div class="cards">
    <div class="card">
      <div class="difficulty easy">Easy</div>
      <h3>simple_review</h3>
      <p>Identify obvious bugs in short Python diffs: off-by-one errors, missing null checks, typos</p>
      <div class="scenarios">10 scenarios &middot; 10 max steps</div>
    </div>
    <div class="card">
      <div class="difficulty medium">Medium</div>
      <h3>logic_review</h3>
      <p>Detect subtle logic errors in realistic PRs: race conditions, edge-case misses, wrong operators</p>
      <div class="scenarios">10 scenarios &middot; 15 max steps</div>
    </div>
    <div class="card">
      <div class="difficulty hard">Hard</div>
      <h3>security_review</h3>
      <p>Find security vulnerabilities (OWASP Top-10): SQL injection, RCE, auth bypass, XSS</p>
      <div class="scenarios">10 scenarios &middot; 20 max steps</div>
    </div>
  </div>

  <h2 class="section-title">API Endpoints</h2>
  <div class="endpoints">
    <div class="endpoint">
      <span class="method get">GET</span>
      <span class="path"><a href="/health">/health</a></span>
      <span class="desc">Health check</span>
    </div>
    <div class="endpoint">
      <span class="method get">GET</span>
      <span class="path"><a href="/tasks">/tasks</a></span>
      <span class="desc">List available tasks</span>
    </div>
    <div class="endpoint">
      <span class="method post">POST</span>
      <span class="path">/api/reset</span>
      <span class="desc">Start a new episode</span>
    </div>
    <div class="endpoint">
      <span class="method post">POST</span>
      <span class="path">/api/step</span>
      <span class="desc">Execute a review action</span>
    </div>
    <div class="endpoint">
      <span class="method get">GET</span>
      <span class="path"><a href="/api/state">/api/state</a></span>
      <span class="desc">Get current episode state</span>
    </div>
    <div class="endpoint">
      <span class="method get">GET</span>
      <span class="path"><a href="/grader">/grader</a></span>
      <span class="desc">Grader results for completed episode</span>
    </div>
  </div>

  <div class="footer">
    Built for the <strong>Scaler &times; Meta &times; PyTorch Hackathon 2026</strong><br>
    Powered by <a href="https://github.com/meta-pytorch/OpenEnv">OpenEnv</a>
  </div>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the CodeReviewEnv landing page."""
    return LANDING_PAGE


@app.get("/tasks")
async def get_tasks():
    """List available tasks with metadata."""
    return {"tasks": _env_instance.get_tasks()}


@app.get("/grader")
async def get_grader_results():
    """Get grader results for the current completed episode."""
    results = _env_instance.get_episode_results()
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results


# ─── Convenience REST endpoints (in addition to OpenEnv WebSocket) ────────────

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
    reason: Optional[str] = None


@app.post("/api/reset")
async def rest_reset(req: ResetRequest):
    """REST endpoint to start a new episode (alternative to WebSocket)."""
    obs = _env_instance.reset(
        task_id=req.task_id,
        scenario_id=req.scenario_id,
        seed=req.seed,
        episode_id=req.episode_id,
    )
    return obs.model_dump()


@app.post("/api/step")
async def rest_step(req: StepRequest):
    """REST endpoint to execute an action (alternative to WebSocket)."""
    action = ReviewAction(
        action_type=req.action_type,
        line_number=req.line_number,
        severity=req.severity,
        message=req.message,
        reason=req.reason,
    )
    obs = _env_instance.step(action)
    return obs.model_dump()


@app.get("/api/state")
async def rest_state():
    """REST endpoint to get current state."""
    return _env_instance.state.model_dump()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    """Run the server directly."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
