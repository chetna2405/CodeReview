"""
FastAPI application for CodeReviewEnv.

Exposes the CodeReviewEnvironment over HTTP endpoints:
  - POST /reset          — Start a new episode
  - POST /step           — Execute a review action
  - GET  /state          — Get current episode state
  - GET  /tasks          — List available tasks
  - GET  /grader         — Get grader results for completed episode
  - POST /baseline       — Run baseline inference (requires HF token)
  - GET  /health         — Health check
"""

import os
import sys
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any

# Handle imports for both package and standalone modes
try:
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction, DiffObservation, ReviewState
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction, DiffObservation, ReviewState


# ─── Pydantic request/response models for FastAPI ────────────────────────────

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

class ObservationResponse(BaseModel):
    diff_text: str = ""
    commit_message: str = ""
    pr_description: str = ""
    file_path: str = ""
    file_context: str = ""
    task_id: str = ""
    step_num: int = 0
    max_steps: int = 10
    existing_comments: list = []
    done: bool = False
    reward: float = 0.0
    metadata: dict = {}

class StateResponse(BaseModel):
    episode_id: str = ""
    step_count: int = 0
    task_id: str = ""
    scenario_id: str = ""
    comments_made: int = 0
    issues_found: int = 0
    max_steps: int = 10
    is_done: bool = False
    final_score: Optional[float] = None


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CodeReviewEnv",
    description="OpenEnv environment for AI code review benchmarking",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single environment instance per server
env = CodeReviewEnvironment()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "environment": "CodeReviewEnv", "version": "1.0.0"}


@app.get("/tasks")
async def get_tasks():
    """List available tasks with metadata."""
    return {"tasks": env.get_tasks()}


@app.post("/reset", response_model=ObservationResponse)
async def reset(req: ResetRequest):
    """
    Start a new code review episode.

    Pass task_id to select difficulty:
    - simple_review (easy): obvious bugs
    - logic_review (medium): subtle logic errors
    - security_review (hard): security vulnerabilities
    """
    obs = env.reset(
        task_id=req.task_id,
        scenario_id=req.scenario_id,
        seed=req.seed,
        episode_id=req.episode_id,
    )

    return ObservationResponse(
        diff_text=obs.diff_text,
        commit_message=obs.commit_message,
        pr_description=obs.pr_description,
        file_path=obs.file_path,
        file_context=obs.file_context,
        task_id=obs.task_id,
        step_num=obs.step_num,
        max_steps=obs.max_steps,
        existing_comments=obs.existing_comments,
        done=obs.done,
        reward=obs.reward,
        metadata=obs.metadata,
    )


@app.post("/step", response_model=ObservationResponse)
async def step(req: StepRequest):
    """
    Execute a review action.

    Action types:
    - add_comment: Flag a line with severity and message
    - approve: Approve the PR (ends episode)
    - request_changes: Request changes (ends episode)
    """
    action = ReviewAction(
        action_type=req.action_type,
        line_number=req.line_number,
        severity=req.severity,
        message=req.message,
        reason=req.reason,
    )

    obs = env.step(action)

    return ObservationResponse(
        diff_text=obs.diff_text,
        commit_message=obs.commit_message,
        pr_description=obs.pr_description,
        file_path=obs.file_path,
        file_context=obs.file_context,
        task_id=obs.task_id,
        step_num=obs.step_num,
        max_steps=obs.max_steps,
        existing_comments=obs.existing_comments,
        done=obs.done,
        reward=obs.reward,
        metadata=obs.metadata,
    )


@app.get("/state", response_model=StateResponse)
async def get_state():
    """Get current episode state."""
    s = env.state
    return StateResponse(
        episode_id=s.episode_id,
        step_count=s.step_count,
        task_id=s.task_id,
        scenario_id=s.scenario_id,
        comments_made=s.comments_made,
        issues_found=s.issues_found,
        max_steps=s.max_steps,
        is_done=s.is_done,
        final_score=s.final_score,
    )


@app.get("/grader")
async def get_grader_results():
    """Get grader results for the current completed episode."""
    results = env.get_episode_results()
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results


@app.post("/baseline")
async def run_baseline():
    """
    Run baseline inference using HuggingFace Inference API.

    Requires HF_TOKEN environment variable.
    Returns baseline scores for all 3 tasks.
    """
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    if not hf_token:
        raise HTTPException(
            status_code=400,
            detail="HF_TOKEN environment variable required for baseline inference."
        )

    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(
            model="meta-llama/Llama-3.1-8B-Instruct",
            token=hf_token,
        )

        baseline_scores = {}

        for task_id in ["simple_review", "logic_review", "security_review"]:
            obs = env.reset(task_id=task_id, seed=42)

            # Build prompt for the LLM
            prompt = f"""You are an expert code reviewer. Review the following PR diff and identify all bugs, issues, and potential problems.

## PR Description
{obs.pr_description}

## Commit Message
{obs.commit_message}

## Diff
```
{obs.diff_text}
```

## File Context
```python
{obs.file_context}
```

For each issue found, respond in JSON format:
[
  {{"line_number": <int>, "severity": "<critical|major|minor|nit>", "message": "<description of the issue>"}}
]

Only output the JSON array, nothing else."""

            response = client.text_generation(
                prompt,
                max_new_tokens=1024,
                temperature=0.01,
            )

            # Parse LLM response into actions
            try:
                # Try to extract JSON from response
                text = response.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                comments = json.loads(text)

                if isinstance(comments, list):
                    for comment in comments:
                        action = ReviewAction(
                            action_type="add_comment",
                            line_number=comment.get("line_number"),
                            severity=comment.get("severity", "major"),
                            message=comment.get("message", ""),
                        )
                        env.step(action)
            except (json.JSONDecodeError, Exception):
                pass

            # End episode
            final_obs = env.step(ReviewAction(action_type="request_changes", reason="Issues found"))
            results = env.get_episode_results()
            baseline_scores[task_id] = round(results.get("composite_score", 0.0), 4)

        return {"baseline_scores": baseline_scores, "model": "meta-llama/Llama-3.1-8B-Instruct"}

    except ImportError:
        raise HTTPException(status_code=500, detail="huggingface_hub package not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline inference failed: {str(e)}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    """Run the server directly."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
