#!/usr/bin/env python3
"""
Baseline inference script for CodeReviewEnv.

Runs a code review agent (via HuggingFace Inference API) against all 3 tasks
and reports baseline scores. Uses temperature=0 for reproducibility.

Usage:
    export HF_TOKEN=your_huggingface_token
    python baseline.py

    # Or with a specific model:
    python baseline.py --model meta-llama/Llama-3.1-8B-Instruct

    # Or against a remote server:
    python baseline.py --base-url https://your-space.hf.space
"""

import argparse
import json
import os
import sys
import time
import requests


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

TASKS = ["simple_review", "logic_review", "security_review"]


def run_baseline_local(seed: int = 42):
    """
    Run baseline locally by importing the environment directly.
    No server needed — fastest for development.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from server.code_review_environment import CodeReviewEnvironment
    from models import ReviewAction

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    env = CodeReviewEnvironment()
    results = {}

    for task_id in TASKS:
        print(f"\n{'='*60}")
        print(f"Running baseline for task: {task_id}")
        print(f"{'='*60}")

        obs = env.reset(task_id=task_id, seed=seed)
        print(f"  Scenario: {obs.metadata.get('scenario_id', 'unknown')}")
        print(f"  Difficulty: {obs.metadata.get('difficulty', 'unknown')}")

        if hf_token:
            # Use HF Inference API for review
            comments = _get_llm_review(obs, hf_token)
            for comment in comments:
                action = ReviewAction(
                    action_type="add_comment",
                    line_number=comment.get("line_number"),
                    severity=comment.get("severity", "major"),
                    message=comment.get("message", ""),
                )
                step_result = env.step(action)
                print(f"  → Added comment on line {comment.get('line_number')}: {comment.get('message', '')[:50]}...")
                print(f"    Partial reward: {step_result.reward:.3f}")
        else:
            print("  ⚠ No HF_TOKEN found — using rule-based baseline")
            comments = _get_rule_based_review(obs)
            for comment in comments:
                action = ReviewAction(
                    action_type="add_comment",
                    line_number=comment.get("line_number"),
                    severity=comment.get("severity", "major"),
                    message=comment.get("message", ""),
                )
                step_result = env.step(action)
                print(f"  → Added comment on line {comment.get('line_number')}: {comment.get('message', '')[:50]}...")

        # End episode
        final_obs = env.step(ReviewAction(action_type="request_changes", reason="Issues found in review"))
        episode_results = env.get_episode_results()

        score = episode_results.get("composite_score", 0.0)
        results[task_id] = score

        print(f"\n  📊 Results for {task_id}:")
        print(f"     Composite Score: {score:.4f}")
        print(f"     F1 Score:        {episode_results.get('f1_score', 0):.4f}")
        print(f"     Precision:       {episode_results.get('precision', 0):.4f}")
        print(f"     Recall:          {episode_results.get('recall', 0):.4f}")
        print(f"     Severity Acc:    {episode_results.get('severity_accuracy', 0):.4f}")
        print(f"     Comment Sim:     {episode_results.get('comment_similarity', 0):.4f}")
        print(f"     Issues Found:    {episode_results.get('issues_found', 0)}/{episode_results.get('issues_total', 0)}")

    print(f"\n{'='*60}")
    print("BASELINE SCORES SUMMARY")
    print(f"{'='*60}")
    for task_id, score in results.items():
        print(f"  {task_id}: {score:.4f}")
    print(f"\n  Output JSON:")
    print(f"  {json.dumps(results, indent=2)}")

    return results


def run_baseline_remote(base_url: str, seed: int = 42):
    """
    Run baseline against a remote CodeReviewEnv server.
    """
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    results = {}

    for task_id in TASKS:
        print(f"\n{'='*60}")
        print(f"Running baseline for task: {task_id}")
        print(f"{'='*60}")

        # Reset
        resp = requests.post(f"{base_url}/reset", json={"task_id": task_id, "seed": seed})
        resp.raise_for_status()
        obs = resp.json()

        print(f"  Scenario: {obs.get('metadata', {}).get('scenario_id', 'unknown')}")

        if hf_token:
            # Build a mock observation object for _get_llm_review
            class MockObs:
                def __init__(self, data):
                    self.diff_text = data.get("diff_text", "")
                    self.pr_description = data.get("pr_description", "")
                    self.commit_message = data.get("commit_message", "")
                    self.file_context = data.get("file_context", "")

            comments = _get_llm_review(MockObs(obs), hf_token)
        else:
            print("  ⚠ No HF_TOKEN — using rule-based baseline")
            class MockObs:
                def __init__(self, data):
                    self.diff_text = data.get("diff_text", "")
            comments = _get_rule_based_review(MockObs(obs))

        for comment in comments:
            resp = requests.post(f"{base_url}/step", json={
                "action_type": "add_comment",
                "line_number": comment.get("line_number"),
                "severity": comment.get("severity", "major"),
                "message": comment.get("message", ""),
            })
            step_data = resp.json()
            print(f"  → Line {comment.get('line_number')}: reward={step_data.get('reward', 0):.3f}")

        # End episode
        resp = requests.post(f"{base_url}/step", json={
            "action_type": "request_changes",
            "reason": "Issues found",
        })

        # Get grader results
        resp = requests.get(f"{base_url}/grader")
        episode_results = resp.json()

        score = episode_results.get("composite_score", 0.0)
        results[task_id] = score
        print(f"  📊 Score: {score:.4f}")

    print(f"\n{'='*60}")
    print(json.dumps(results, indent=2))
    return results


def _get_llm_review(obs, hf_token: str) -> list[dict]:
    """Get code review comments from HuggingFace Inference API."""
    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(
            model=DEFAULT_MODEL,
            token=hf_token,
        )

        prompt = f"""You are an expert code reviewer. Review the following PR diff and identify ALL bugs, security issues, and problems.

## PR Description
{obs.pr_description}

## Commit Message
{obs.commit_message}

## Diff
```
{obs.diff_text}
```

## Full File Context
```python
{obs.file_context}
```

For each issue, respond with a JSON array. Each element must have:
- "line_number": the line number in the diff where the issue is
- "severity": one of "critical", "major", "minor", "nit"
- "message": a clear description of the bug or issue

Output ONLY the JSON array, no other text:"""

        response = client.text_generation(
            prompt,
            max_new_tokens=1024,
            temperature=0.01,
        )

        # Parse response
        text = response.strip()
        # Extract JSON from possible markdown code blocks
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                cleaned = part.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
                if cleaned.startswith("["):
                    text = cleaned
                    break

        comments = json.loads(text)
        if isinstance(comments, list):
            return comments
        return []

    except Exception as e:
        print(f"  ⚠ LLM review failed: {e}")
        return _get_rule_based_review(obs)


def _get_rule_based_review(obs) -> list[dict]:
    """
    Simple rule-based baseline that looks for common patterns in diffs.
    Used as fallback when no API key is available.
    """
    comments = []
    diff_text = obs.diff_text

    # Pattern: removed error handling
    if "except" in diff_text and "-" in diff_text:
        lines = diff_text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("-") and "except" in line:
                comments.append({
                    "line_number": i + 1,
                    "severity": "major",
                    "message": "Removed error handling. Exceptions will now propagate unhandled."
                })
                break

    # Pattern: removed validation
    if "if " in diff_text and ("None" in diff_text or "not " in diff_text):
        lines = diff_text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("-") and ("if " in line) and ("None" in line or "not " in line):
                comments.append({
                    "line_number": i + 1,
                    "severity": "critical",
                    "message": "Removed input validation check. This could allow invalid data through."
                })
                break

    # Pattern: hardcoded secrets
    for pattern in ["api_key", "secret", "password", "token"]:
        if pattern.lower() in diff_text.lower() and ("'" in diff_text or '"' in diff_text):
            lines = diff_text.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("+") and pattern.lower() in line.lower() and ("'" in line or '"' in line):
                    comments.append({
                        "line_number": i + 1,
                        "severity": "critical",
                        "message": f"Hardcoded {pattern} found. Use environment variables instead."
                    })
                    break
            break

    # If no specific patterns found, add a generic observation
    if not comments:
        comments.append({
            "line_number": 1,
            "severity": "minor",
            "message": "Review the changes for potential issues with error handling and edge cases."
        })

    return comments


def main():
    global DEFAULT_MODEL
    parser = argparse.ArgumentParser(description="CodeReviewEnv Baseline Inference")
    parser.add_argument("--base-url", default=None, help="Remote server URL (omit for local)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HuggingFace model to use")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    DEFAULT_MODEL = args.model

    if args.base_url:
        run_baseline_remote(args.base_url, seed=args.seed)
    else:
        run_baseline_local(seed=args.seed)


if __name__ == "__main__":
    main()
