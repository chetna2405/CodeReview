#!/usr/bin/env python3
"""
LLM-based scenario generator for CodeReviewEnv.

Generates realistic Python diff scenarios with deliberate bugs using the
HuggingFace Inference API (Mistral-7B-Instruct-v0.3).

Usage:
    python generate_scenarios_llm.py --difficulty easy --count 5 --out-dir data/scenarios/public/easy
    python generate_scenarios_llm.py --difficulty hard --count 3 --out-dir data/scenarios/public/hard --token hf_xxx
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)


HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

REQUIRED_KEYS = {"id", "diff_text", "commit_message", "pr_description", "file_path", "file_context", "difficulty", "gold_annotations"}
VALID_SEVERITIES = {"minor", "major", "critical"}

DIFFICULTY_PROMPTS = {
    "easy": (
        "Generate a simple Python code diff with 1 deliberate bug. "
        "The bug should be obvious: off-by-one error, missing null check, hardcoded secret, or typo. "
        "The diff should be < 30 lines."
    ),
    "medium": (
        "Generate a medium-complexity Python code diff with 2 deliberate bugs. "
        "The bugs should be subtle: race conditions, logic errors, wrong conditions, resource leaks. "
        "The diff should be 30-80 lines."
    ),
    "hard": (
        "Generate a complex Python code diff with 2-3 deliberate security vulnerabilities. "
        "Include OWASP Top-10 issues: SQL injection, command injection, auth bypass, SSTI, path traversal. "
        "The diff should be 50-100 lines."
    ),
}


def _build_prompt(difficulty: str, scenario_id: str) -> str:
    """Build the prompt for the LLM."""
    diff_instruction = DIFFICULTY_PROMPTS.get(difficulty, DIFFICULTY_PROMPTS["easy"])
    return (
        f"<s>[INST] You are a code review benchmark generator. "
        f"{diff_instruction}\n\n"
        f"Return ONLY a valid JSON object (no markdown, no explanation) with exactly these keys:\n"
        f"- id: \"{scenario_id}\"\n"
        f"- diff_text: a unified diff string (with --- a/ and +++ b/ headers)\n"
        f"- commit_message: a realistic one-line commit message\n"
        f"- pr_description: a 1-2 sentence PR description\n"
        f"- file_path: the Python filename (e.g. \"utils.py\")\n"
        f"- file_context: the full file content after the change\n"
        f"- difficulty: \"{difficulty}\"\n"
        f"- gold_annotations: a list of objects, each with:\n"
        f"  - line_number (int > 0): the line in the diff where the bug is\n"
        f"  - severity: one of \"minor\", \"major\", \"critical\"\n"
        f"  - type: bug category (e.g. \"off_by_one\", \"sql_injection\", \"null_check\")\n"
        f"  - description: clear explanation of the bug\n\n"
        f"Return ONLY the JSON. [/INST]"
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def _validate_scenario(data: Any, difficulty: str) -> list[str]:
    """Validate a scenario JSON object. Returns list of error strings."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Root object is not a dict"]

    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    if "gold_annotations" in data:
        anns = data["gold_annotations"]
        if not isinstance(anns, list) or len(anns) == 0:
            errors.append("gold_annotations must be a non-empty list")
        else:
            for i, ann in enumerate(anns):
                if not isinstance(ann, dict):
                    errors.append(f"Annotation {i} is not a dict")
                    continue
                ln = ann.get("line_number")
                if not isinstance(ln, int) or ln < 1:
                    errors.append(f"Annotation {i}: line_number must be int > 0, got {ln}")
                sev = ann.get("severity", "")
                if sev not in VALID_SEVERITIES:
                    errors.append(f"Annotation {i}: severity must be in {VALID_SEVERITIES}, got '{sev}'")

    if "difficulty" in data and data["difficulty"] != difficulty:
        errors.append(f"Difficulty mismatch: expected '{difficulty}', got '{data['difficulty']}'")

    return errors


def generate_scenario(
    difficulty: str,
    scenario_id: str,
    token: str,
    timeout: float = 60.0,
) -> Optional[dict]:
    """Generate a single scenario via the HF Inference API."""
    prompt = _build_prompt(difficulty, scenario_id)

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1500,
            "temperature": 0.8,
            "return_full_text": False,
        },
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                HF_INFERENCE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"  ✗ API request failed: {e}")
        return None

    # Parse response
    if isinstance(data, list) and data:
        raw_text = data[0].get("generated_text", "")
    elif isinstance(data, dict):
        raw_text = data.get("generated_text", "")
    else:
        print(f"  ✗ Unexpected response format: {type(data)}")
        return None

    # Strip markdown fences and parse JSON
    cleaned = _strip_markdown_fences(raw_text)
    try:
        scenario = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        print(f"    Raw output (first 200 chars): {cleaned[:200]}")
        return None

    # Validate
    errors = _validate_scenario(scenario, difficulty)
    if errors:
        print(f"  ✗ Validation errors:")
        for err in errors:
            print(f"    - {err}")
        return None

    # Ensure ID
    scenario["id"] = scenario_id
    return scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate code review scenarios using LLM")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], required=True)
    parser.add_argument("--count", type=int, required=True, help="Number of scenarios to generate")
    parser.add_argument("--out-dir", type=str, required=True, help="Output directory for scenario files")
    parser.add_argument("--token", type=str, default=None, help="HuggingFace API token (defaults to HF_TOKEN env var)")
    args = parser.parse_args()

    token = args.token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("Error: HF_TOKEN not provided. Use --token or set HF_TOKEN env var.")
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find next available index
    existing = sorted(out_dir.glob("scenario_*.json"))
    start_idx = len(existing) + 1

    success_count = 0
    fail_count = 0

    print(f"Generating {args.count} {args.difficulty} scenarios → {out_dir}")
    print(f"Starting at index {start_idx}\n")

    for i in range(args.count):
        idx = start_idx + i
        scenario_id = f"llm_{args.difficulty}_{idx:03d}"
        out_file = out_dir / f"scenario_{idx:03d}.json"

        print(f"[{i + 1}/{args.count}] Generating {scenario_id}...")

        scenario = generate_scenario(args.difficulty, scenario_id, token)
        if scenario is None:
            fail_count += 1
            print(f"  ✗ Skipped (generation failed)")
            continue

        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(scenario, f, indent=2)
            success_count += 1
            n_anns = len(scenario.get("gold_annotations", []))
            print(f"  ✓ Written to {out_file} ({n_anns} annotations)")
        except OSError as e:
            fail_count += 1
            print(f"  ✗ Write failed: {e}")

        # Rate limiting
        if i < args.count - 1:
            time.sleep(2)

    print(f"\nDone: {success_count} succeeded, {fail_count} failed")


if __name__ == "__main__":
    main()
