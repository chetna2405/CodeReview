"""
Pre-Submission Checklist Validator for CodeReviewEnv
Verifies all requirements from the hackathon checklist.
"""
import json
import os
import re
import subprocess
import sys
import requests

BASE = "https://chetna1910-codereviewenv.hf.space"
ROOT = os.path.dirname(os.path.abspath(__file__))
PASS = "✅"
FAIL = "❌"

results = []

def check(name, ok, detail=""):
    mark = PASS if ok else FAIL
    print(f"  {mark}  {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, ok))
    return ok

def section(title):
    print(f"\n{'═'*58}")
    print(f"  {title}")
    print(f"{'═'*58}")

# ─── 1. HF SPACE DEPLOYS ───────────────────────────────────────
section("1. HF Space Deploys")

r = requests.get(f"{BASE}/health", timeout=30)
check("Health returns 200", r.status_code == 200, r.text[:80])

r = requests.post(f"{BASE}/api/reset", json={"task_id": "simple_review"}, timeout=30)
check("reset() responds to ping", r.status_code == 200,
      f"task_id={r.json().get('task_id')}" if r.ok else r.text[:80])

# ─── 2. OPENENV SPEC COMPLIANCE ────────────────────────────────
section("2. OpenEnv Spec Compliance")

yaml_path = os.path.join(ROOT, "openenv.yaml")
check("openenv.yaml exists", os.path.isfile(yaml_path))
if os.path.isfile(yaml_path):
    with open(yaml_path) as f:
        content = f.read()
    check("  spec_version defined", "spec_version" in content)
    check("  observation_space defined", "observation_space" in content)
    check("  action_space defined", "action_space" in content)
    check("  reward_range defined", "reward_range" in content)
    check("  3 tasks defined", content.count("- id:") == 3)

check("Typed models.py exists", os.path.isfile(os.path.join(ROOT, "models.py")))

r = requests.post(f"{BASE}/api/reset", json={"task_id": "simple_review"}, timeout=30)
check("POST /api/reset (reset() endpoint)", r.status_code == 200)

r2 = requests.post(f"{BASE}/api/step",
                   json={"action_type": "add_comment", "line_number": 1,
                         "severity": "minor", "message": "test"}, timeout=30)
check("POST /api/step (step() endpoint)", r2.status_code == 200)

r3 = requests.get(f"{BASE}/api/state", timeout=30)
check("GET /api/state (state() endpoint)", r3.status_code == 200)

# ─── 3. DOCKERFILE BUILDS ──────────────────────────────────────
section("3. Dockerfile")

check("server/Dockerfile exists",
      os.path.isfile(os.path.join(ROOT, "server", "Dockerfile")))
with open(os.path.join(ROOT, "server", "Dockerfile")) as f:
    df = f.read()
check("  FROM python:3.11", "python:3.11" in df)
check("  EXPOSE 8000", "EXPOSE 8000" in df)
check("  uvicorn CMD", "uvicorn" in df)

# ─── 4. BASELINE / INFERENCE REPRODUCES ────────────────────────
section("4. Inference Script")

inf_path = os.path.join(ROOT, "inference.py")
check("inference.py exists in root", os.path.isfile(inf_path))

with open(inf_path) as f:
    inf_src = f.read()
check("  Uses OpenAI client", "from openai import OpenAI" in inf_src)
check("  Reads API_BASE_URL", "API_BASE_URL" in inf_src)
check("  Reads MODEL_NAME", "MODEL_NAME" in inf_src)
check("  Reads HF_TOKEN", "HF_TOKEN" in inf_src)
check("  Emits [START]", "[START]" in inf_src)
check("  Emits [STEP]", "[STEP]" in inf_src)
check("  Emits [END]", "[END]" in inf_src)
check("  Has log_start()", "def log_start" in inf_src)
check("  Has log_step()", "def log_step" in inf_src)
check("  Has log_end()", "def log_end" in inf_src)

# Validate log format matches spec exactly
start_re = re.search(r'\[START\] task=', inf_src)
step_re  = re.search(r'\[STEP\] step=', inf_src)
end_re   = re.search(r'\[END\] success=', inf_src)
check("  [START] format correct", bool(start_re))
check("  [STEP] format correct", bool(step_re))
check("  [END] format correct", bool(end_re))

# ─── 5. 3+ TASKS WITH GRADERS ──────────────────────────────────
section("5. Tasks with Graders (score in [0.0, 1.0])")

r = requests.get(f"{BASE}/tasks", timeout=30)
tasks = r.json().get("tasks", [])
check("3 tasks enumerable", len(tasks) == 3,
      f"tasks={[t.get('id') for t in tasks]}")

for t in tasks:
    tid = t.get("id")
    # Run a quick episode
    r = requests.post(f"{BASE}/api/reset", json={"task_id": tid}, timeout=30)
    if r.ok:
        requests.post(f"{BASE}/api/step",
                      json={"action_type": "approve", "reason": "test"}, timeout=30)
        gr = requests.get(f"{BASE}/grader", timeout=30)
        if gr.ok:
            score = gr.json().get("composite_score", -1)
            check(f"  {tid} grader returns score in [0,1]",
                  0.0 <= score <= 1.0, f"score={score:.4f}")
        else:
            check(f"  {tid} grader reachable", False, gr.text[:60])
    else:
        check(f"  {tid} reset ok", False, r.text[:60])

# ─── 6. MANDATORY VARS IN ENV CONFIG ───────────────────────────
section("6. Mandatory Env Variables")

check("API_BASE_URL referenced in inference.py",  "API_BASE_URL" in inf_src)
check("MODEL_NAME referenced in inference.py",    "MODEL_NAME"   in inf_src)
check("HF_TOKEN referenced in inference.py",      "HF_TOKEN"     in inf_src)
check("OpenAI client used (not huggingface_hub)", "from openai import OpenAI" in inf_src
      and "InferenceClient" not in inf_src)

# ─── SUMMARY ───────────────────────────────────────────────────
section("PRE-SUBMISSION CHECKLIST SUMMARY")

passed = sum(1 for _, ok in results if ok)
total  = len(results)
pct    = passed / total * 100 if total else 0

print(f"\n  {passed}/{total} checks passed  ({pct:.0f}%)\n")

failed = [n for n, ok in results if not ok]
if failed:
    print("  ── Failed ────────────────────────────────────────")
    for n in failed:
        print(f"  ❌  {n}")
    print()

if passed == total:
    print("  🎉  ALL CHECKLIST ITEMS PASSED — READY TO SUBMIT!")
elif pct >= 85:
    print(f"  ⚠️   MOSTLY READY — fix {len(failed)} item(s) before submitting")
else:
    print(f"  ❌  NOT READY — {len(failed)} critical items need attention")

print(f"{'═'*58}\n")
sys.exit(0 if passed == total else 1)
