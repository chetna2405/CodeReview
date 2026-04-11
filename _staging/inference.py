"""
CodeReviewEnv — Inference Script
===================================
MANDATORY environment variables:
    API_BASE_URL    The API endpoint for the LLM.
    MODEL_NAME      The model identifier to use for inference.
    HF_TOKEN        Your Hugging Face / API key.
    ENV_URL         CodeReviewEnv server URL (default: deployed HF Space)

STDOUT FORMAT (strictly enforced):
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
"""

import json
import os
import sys
import requests
from typing import List, Optional
from openai import OpenAI

# ── Config ─────────────────────────────────────────────────────────────────────
HF_TOKEN      = os.getenv("HF_TOKEN")
API_KEY       = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL  = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME    = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL       = os.getenv("ENV_URL", "https://chetna1910-codereviewenv.hf.space")

BENCHMARK             = "code-review-env"
TASKS                 = ["simple_review", "logic_review", "security_review"]
MAX_COMMENT_STEPS     = 7   # leave 1 slot for the closing action
SUCCESS_SCORE_THRESHOLD = 0.5

# ── Stdout log helpers ─────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool,
             error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float,
            rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── LLM review ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert code reviewer. Review the PR diff and identify ALL bugs, "
    "security vulnerabilities, logic errors, and code quality issues.\n\n"
    "Respond with ONLY a JSON array. Each element must have:\n"
    '  "line_number": integer (line in the diff where the issue is)\n'
    '  "severity": one of "critical", "major", "minor", "nit"\n'
    '  "message": concise description of the issue\n'
    '  "reason": brief explanation of why it is a problem\n\n'
    "Output ONLY the JSON array — no markdown, no explanation."
)

VALID_SEVERITIES = {"critical", "major", "minor", "nit"}


def get_llm_review(client: OpenAI, obs: dict) -> List[dict]:
    """Ask the LLM to review the diff; returns a list of comment dicts."""
    diff       = obs.get("diff_text", "")
    pr_desc    = obs.get("pr_description", "")
    commit_msg = obs.get("commit_message", "")
    file_ctx   = (obs.get("file_context") or "")[:3000]

    user_prompt = (
        f"## Commit Message\n{commit_msg}\n\n"
        f"## PR Description\n{pr_desc}\n\n"
        f"## Diff\n```\n{diff}\n```\n\n"
        f"## File Context\n```python\n{file_ctx}\n```\n\n"
        "Identify ALL issues and return a JSON array."
    )

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        # Extract JSON from possible markdown fencing
        if "```" in text:
            for part in text.split("```"):
                cleaned = part.strip().lstrip("json").strip()
                if cleaned.startswith("["):
                    text = cleaned
                    break

        comments = json.loads(text)
        return comments if isinstance(comments, list) else []

    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return []


# ── Single task episode ────────────────────────────────────────────────────────

def run_task(client: OpenAI, task_id: str) -> float:
    """Run a full episode for one task. Returns composite score in [0, 1]."""
    rewards:    List[float] = []
    steps_taken = 0
    score       = 0.0
    success     = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        # ── Reset ────────────────────────────────────────────────────────────
        r = requests.post(
            f"{ENV_URL}/api/reset",
            json={"task_id": task_id},
            timeout=60,
        )
        r.raise_for_status()
        obs  = r.json()
        done = bool(obs.get("done", False))

        # ── LLM review ───────────────────────────────────────────────────────
        comments = get_llm_review(client, obs)
        print(f"[DEBUG] LLM returned {len(comments)} comment(s) for {task_id}", flush=True)

        # ── Submit comments ───────────────────────────────────────────────────
        step = 1
        for comment in comments[:MAX_COMMENT_STEPS]:
            if done:
                break

            line     = comment.get("line_number") or 1
            severity = comment.get("severity", "major")
            if severity not in VALID_SEVERITIES:
                severity = "major"
            message  = str(comment.get("message", "")).strip()
            reason   = str(comment.get("reason", "")).strip()

            action_str = f"add_comment(line={line},severity={severity})"
            error_msg: Optional[str] = None

            try:
                r = requests.post(
                    f"{ENV_URL}/api/step",
                    json={
                        "action_type": "add_comment",
                        "line_number":  line,
                        "severity":     severity,
                        "message":      message,
                        "reason":       reason,
                    },
                    timeout=60,
                )
                r.raise_for_status()
                res    = r.json()
                reward = float(res.get("reward", 0.0))
                done   = bool(res.get("done", False))
            except Exception as exc:
                reward    = 0.0
                done      = False
                error_msg = str(exc)[:80]

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward,
                     done=done, error=error_msg)
            step += 1

        # ── Close episode ─────────────────────────────────────────────────────
        if not done:
            end_action = "request_changes" if comments else "approve"
            end_reason = ("Issues identified during review."
                          if comments else "No issues found — LGTM.")
            action_str = f"{end_action}()"
            error_msg   = None

            try:
                r = requests.post(
                    f"{ENV_URL}/api/step",
                    json={"action_type": end_action, "reason": end_reason},
                    timeout=60,
                )
                r.raise_for_status()
                res    = r.json()
                reward = float(res.get("reward", 0.0))
                done   = bool(res.get("done", False))
            except Exception as exc:
                reward    = 0.0
                done      = True
                error_msg = str(exc)[:80]

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward,
                     done=done, error=error_msg)

        # ── Get composite score from grader ───────────────────────────────────
        try:
            gr = requests.get(f"{ENV_URL}/grader", timeout=30)
            if gr.status_code == 200:
                grader_data = gr.json()
                score = float(grader_data.get("composite_score", 0.0))
                print(
                    f"[DEBUG] Grader: f1={grader_data.get('f1_score',0):.3f} "
                    f"severity={grader_data.get('severity_accuracy',0):.3f} "
                    f"similarity={grader_data.get('comment_similarity',0):.3f}",
                    flush=True,
                )
            else:
                # Fallback: use final reward
                score = rewards[-1] if rewards else 0.0
        except Exception as exc:
            print(f"[DEBUG] Grader fetch failed: {exc}", flush=True)
            score = rewards[-1] if rewards else 0.0

        score   = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task_id} failed: {exc}", flush=True)
        score   = 0.0
        success = False

    finally:
        log_end(success=success, steps=steps_taken,
                score=score, rewards=rewards)

    return score


# ── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    if not API_KEY:
        print("[DEBUG] WARNING: API_KEY/HF_TOKEN not set — LLM calls will fail", flush=True)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "dummy")

    all_scores: dict = {}
    for task_id in TASKS:
        all_scores[task_id] = run_task(client, task_id)

    # Final summary JSON to stdout
    print(json.dumps(all_scores, indent=2), flush=True)


if __name__ == "__main__":
    main()
