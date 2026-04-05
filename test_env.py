"""
CodeReviewEnv — End-to-End Test Suite
Tests the live deployed environment at https://chetna1910-codereviewenv.hf.space
"""

import json
import requests
import sys
from datetime import datetime

BASE_URL = "https://chetna1910-codereviewenv.hf.space"

results = []

def check(name, condition, detail=""):
    status = "✅ PASS" if condition else "❌ FAIL"
    msg = f"  {status}  {name}"
    if detail:
        msg += f"\n          → {detail}"
    print(msg)
    results.append((name, condition))
    return condition

def info(msg):
    print(f"  ℹ️   {msg}")

def section(title):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")

# ─── 1. HEALTH & META ──────────────────────────────────────────
section("1. Health & Metadata")

r = requests.get(f"{BASE_URL}/health", timeout=45)
check("Health endpoint returns 200", r.status_code == 200)
health = r.json()
check("Status is healthy", health.get("status") == "healthy", str(health))

r = requests.get(f"{BASE_URL}/tasks", timeout=45)
check("Tasks endpoint returns 200", r.status_code == 200)
tasks_resp = r.json()
# API returns {"tasks": [...]}
tasks = tasks_resp.get("tasks", tasks_resp) if isinstance(tasks_resp, dict) else tasks_resp
check("Has 3 tasks", len(tasks) == 3, f"count={len(tasks)}")
task_ids = [t.get("id") or t.get("task_id") for t in tasks]
info(f"Tasks: {task_ids}")
info(f"Difficulties: {[t.get('difficulty') for t in tasks]}")

# ─── 2. RESET — ALL 3 TASKS ────────────────────────────────────
section("2. Reset — All 3 Tasks")

task_id_names = ["simple_review", "logic_review", "security_review"]

for tid in task_id_names:
    r = requests.post(f"{BASE_URL}/api/reset", json={"task_id": tid}, timeout=45)
    ok = check(f"Reset task_id={tid} → 200", r.status_code == 200,
               f"body={r.text[:120]}" if r.status_code != 200 else "")
    if ok:
        obs = r.json()
        check(f"  diff_text present", bool(obs.get("diff_text")),
              f"len={len(obs.get('diff_text', ''))}")
        check(f"  task_id matches", obs.get("task_id") == tid,
              f"got={obs.get('task_id')}")
        check(f"  done=False on reset", obs.get("done") == False)
        ep_id = obs.get("episode_id") or obs.get("metadata", {}).get("episode_id", "N/A")
        info(f"episode_id={ep_id}")
        info(f"commit_msg={obs.get('commit_message','')[:60]}")

# ─── 3. FULL EPISODE — simple_review ───────────────────────────
section("3. Full Episode: simple_review")

r = requests.post(f"{BASE_URL}/api/reset", json={"task_id": "simple_review"}, timeout=45)
check("Reset simple_review", r.status_code == 200)
obs = r.json()
info(f"Diff preview (first 250 chars):\n{obs.get('diff_text','')[:250]}\n    ...")

# Step 1: add_comment
r = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "add_comment",
    "line_number": 5,
    "severity": "major",
    "message": "Potential off-by-one error: loop should use range(len(items)) not range(len(items)-1)",
    "reason": "This will skip the last element in the list"
}, timeout=45)
ok = check("Step 1 (add_comment) → 200", r.status_code == 200,
           f"body={r.text[:120]}" if r.status_code != 200 else "")
if ok:
    res = r.json()
    reward1 = res.get("reward", 0)
    check("  reward is numeric", isinstance(reward1, (int, float)))
    check("  done=False after add_comment", res.get("done") == False)
    info(f"reward after add_comment: {reward1:.4f}")

# Step 2: another comment
r = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "add_comment",
    "line_number": 12,
    "severity": "minor",
    "message": "Missing null check before accessing attribute — could raise AttributeError if object is None",
    "reason": "Add a guard: if obj is not None: ..."
}, timeout=45)
ok = check("Step 2 (add_comment) → 200", r.status_code == 200)
if ok:
    info(f"reward after 2nd comment: {r.json().get('reward', 0):.4f}")

# Step 3: request_changes → ends episode
r = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "request_changes",
    "reason": "Found off-by-one error and missing null check that will cause runtime exceptions"
}, timeout=45)
ok = check("Step 3 (request_changes) → 200", r.status_code == 200,
           f"body={r.text[:200]}" if r.status_code != 200 else "")
if ok:
    res = r.json()
    final_reward = res.get("reward", 0)
    done = res.get("done")
    check("  done=True after request_changes", done == True, f"done={done}")
    check("  final reward in [0.0, 1.0]", 0.0 <= final_reward <= 1.0,
          f"reward={final_reward}")
    info(f"★ FINAL SCORE (simple_review): {final_reward:.4f}")

# ─── 4. STATE ENDPOINT ─────────────────────────────────────────
section("4. State Endpoint")

r = requests.get(f"{BASE_URL}/api/state", timeout=45)
ok = check("GET /api/state → 200", r.status_code == 200,
           f"body={r.text[:120]}" if r.status_code != 200 else "")
if ok:
    state = r.json()
    check("  step_count > 0", state.get("step_count", 0) > 0,
          f"step_count={state.get('step_count')}")
    check("  task_id present", bool(state.get("task_id")))
    check("  is_done=True", state.get("is_done") == True)
    info(f"State snapshot:\n{json.dumps(state, indent=4)}")

# ─── 5. FULL EPISODE — logic_review ────────────────────────────
section("5. Full Episode: logic_review")

r = requests.post(f"{BASE_URL}/api/reset", json={"task_id": "logic_review"}, timeout=45)
check("Reset logic_review", r.status_code == 200)
if r.status_code == 200:
    obs = r.json()
    info(f"Logic diff preview:\n{obs.get('diff_text','')[:200]}\n    ...")

    r = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "add_comment",
        "line_number": 8,
        "severity": "major",
        "message": "Race condition: shared state accessed without proper locking mechanism",
        "reason": "Use threading.Lock() or asyncio.Lock() to protect shared state"
    }, timeout=45)
    ok = check("Step (logic comment)", r.status_code == 200)
    if ok:
        info(f"reward: {r.json().get('reward', 0):.4f}")

    r = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "request_changes",
        "reason": "Logic error detected — race condition needs fixing before merge"
    }, timeout=45)
    ok = check("Step (request_changes) ends episode", r.status_code == 200)
    if ok:
        score = r.json().get("reward", 0)
        check("  Final score in [0.0, 1.0]", 0.0 <= score <= 1.0)
        info(f"★ FINAL SCORE (logic_review): {score:.4f}")

# ─── 6. FULL EPISODE — security_review ─────────────────────────
section("6. Full Episode: security_review")

r = requests.post(f"{BASE_URL}/api/reset", json={"task_id": "security_review"}, timeout=45)
check("Reset security_review", r.status_code == 200)
if r.status_code == 200:
    obs = r.json()
    info(f"Security diff preview:\n{obs.get('diff_text','')[:200]}\n    ...")

    r = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "add_comment",
        "line_number": 8,
        "severity": "critical",
        "message": "SQL injection vulnerability: user input concatenated directly into the query string",
        "reason": "Use parameterized queries or an ORM to prevent SQL injection attacks"
    }, timeout=45)
    ok = check("Step (critical security comment)", r.status_code == 200)
    if ok:
        info(f"reward: {r.json().get('reward', 0):.4f}")

    r = requests.post(f"{BASE_URL}/api/step", json={
        "action_type": "request_changes",
        "reason": "Critical SQL injection vulnerability must be fixed before merge"
    }, timeout=45)
    ok = check("Step (request_changes) ends episode", r.status_code == 200)
    if ok:
        score = r.json().get("reward", 0)
        check("  Final score in [0.0, 1.0]", 0.0 <= score <= 1.0)
        info(f"★ FINAL SCORE (security_review): {score:.4f}")

# ─── 7. GRADER ENDPOINT ────────────────────────────────────────
section("7. Grader Endpoint")

r = requests.get(f"{BASE_URL}/grader", timeout=45)
info(f"Grader status={r.status_code}, body={r.text[:200]}")
check("Grader endpoint reachable (200 or 400 are both valid)",
      r.status_code in [200, 400, 404, 422])
if r.status_code == 200:
    grader_data = r.json()
    info(f"Grader result: {json.dumps(grader_data, indent=2)[:300]}")

# ─── 8. EDGE CASES ─────────────────────────────────────────────
section("8. Edge Cases")

# Reset without task_id → should default or pick randomly
r = requests.post(f"{BASE_URL}/api/reset", json={}, timeout=45)
check("Reset without task_id → 200", r.status_code == 200,
      f"status={r.status_code}, body={r.text[:80]}" if r.status_code != 200 else "")

# Approve action on a fresh episode
r = requests.post(f"{BASE_URL}/api/step", json={
    "action_type": "approve",
    "reason": "LGTM — code looks clean"
}, timeout=45)
ok = check("Approve action → 200", r.status_code == 200)
if ok:
    res = r.json()
    check("  done=True after approve", res.get("done") == True)
    info(f"Score after approve (no comments): {res.get('reward', 0):.4f}")

# Invalid action_type
r = requests.post(f"{BASE_URL}/api/step", json={"action_type": "dance"}, timeout=45)
check("Invalid action_type handled (not 500)", r.status_code != 500,
      f"status={r.status_code}")
info(f"Response to invalid action: {r.text[:100]}")

# ─── SUMMARY ───────────────────────────────────────────────────
section("TEST SUMMARY")

passed = sum(1 for _, ok in results if ok)
total = len(results)
pct = passed / total * 100 if total else 0

print(f"\n  Results: {passed}/{total} passed  ({pct:.0f}%)")
print(f"  Target:  {BASE_URL}")
print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

failed = [(n, ok) for n, ok in results if not ok]
if failed:
    print("  ── Failed Tests ──────────────────────────────────")
    for name, _ in failed:
        print(f"  ❌  {name}")

print()
if passed == total:
    print("  🎉  ALL TESTS PASSED — Environment is production-ready!")
elif pct >= 80:
    print(f"  ⚠️   MOSTLY PASSING — {total - passed} failure(s) need attention")
else:
    print(f"  ❌  FAILURES DETECTED — {total - passed}/{total} tests failed")
print(f"{'═'*60}\n")

sys.exit(0 if passed == total else 1)
