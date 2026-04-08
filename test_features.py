#!/usr/bin/env python3
"""Integration smoke test for all CodeReviewEnv features."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import ReviewAction, DiffObservation, ReviewState, TaskConfig, SEVERITY_LEVELS
from server.grader import grade_episode, _ordinal_severity_score, compute_partial_reward, SEVERITY_MAP
from server.code_review_environment import CodeReviewEnvironment, TASK_CONFIG, _get_scenarios
from server.difficulty_validator import validate_task_difficulty

PASS = lambda msg: print(f"PASS  {msg}")

# ── 1. Grader weights 0.5 / 0.3 / 0.2 ───────────────────────────────────────
r = grade_episode(
    [{"line_number": 5, "severity": "critical", "message": "SQL injection via f-string"}],
    [{"line": 5, "severity": "critical", "issue": "SQL injection via f-string interpolation"}],
    "finalize_review",
)
expected = round(0.5 * r.f1_score + 0.3 * r.severity_accuracy + 0.2 * r.comment_similarity, 9)
assert abs(r.composite_score - expected) < 1e-9
PASS(f"grader weights 0.5/0.3/0.2  composite={r.composite_score:.3f}  f1={r.f1_score:.3f}")

# ── 2. Ordinal severity ──────────────────────────────────────────────────────
assert _ordinal_severity_score("critical", "critical") == 1.0
assert _ordinal_severity_score("major", "critical") == 0.67
assert _ordinal_severity_score("minor", "critical") == 0.33
assert _ordinal_severity_score("nit", "critical") == 0.0
PASS("ordinal severity scoring (1.0 / 0.67 / 0.33 / 0.0)")

# ── 3. False positive penalty in partial reward ──────────────────────────────
spam = [{"line_number": i * 100, "severity": "major", "message": "x"} for i in range(10)]
gold = [{"line_number": 5}]
pr_spam = compute_partial_reward(spam, gold)
pr_good = compute_partial_reward([{"line_number": 5, "severity": "major", "message": "real bug"}], gold)
assert pr_good > pr_spam
PASS(f"FP penalty  spam_reward={pr_spam:.3f}  precise_reward={pr_good:.3f}")

# ── 4. Multi-turn episode: add / clarify / retract / finalize ─────────────────
env = CodeReviewEnvironment()
obs = env.reset(task_id="simple_review", seed=42)
assert not obs.done and obs.can_still_comment
sid = obs.metadata.get("scenario_id", "?")
PASS(f"reset  scenario={sid}  diff_len={len(obs.diff_text)}")

o1 = env.step(ReviewAction(action_type="add_comment", line_number=5, severity="critical", message="bug found"))
cid = env._agent_comments[0]["comment_id"]
assert len(env._agent_comments) == 1
PASS(f"add_comment  comment_id={cid}  partial_reward={o1.reward:.3f}")

o2 = env.step(ReviewAction(action_type="request_clarification", question="Is this intentional?"))
assert len(env.state.author_responses) == 1
resp_preview = env.state.author_responses[0][:40]
PASS(f"request_clarification  author replied: {resp_preview!r}")

o3 = env.step(ReviewAction(action_type="retract_comment", comment_id=cid))
assert len(env._agent_comments) == 0
PASS(f"retract_comment  comments_after={len(env._agent_comments)}")

env.step(ReviewAction(action_type="add_comment", line_number=5, severity="major", message="potential bug re-added"))
o4 = env.step(ReviewAction(action_type="finalize_review", reason="review complete"))
assert o4.done
PASS(f"finalize_review  final_score={o4.reward:.3f}")

# ── 5. Backward compat: approve / request_changes ────────────────────────────
env2 = CodeReviewEnvironment()
env2.reset(task_id="simple_review", seed=1)
env2.step(ReviewAction(action_type="add_comment", line_number=3, severity="minor", message="check"))
final = env2.step(ReviewAction(action_type="request_changes", reason="needs fix"))
assert final.done
PASS(f"legacy request_changes still works  score={final.reward:.3f}")

env3 = CodeReviewEnvironment()
env3.reset(task_id="simple_review", seed=2)
afinal = env3.step(ReviewAction(action_type="approve"))
assert afinal.done
PASS(f"legacy approve still works  score={afinal.reward:.3f}")

# ── 6. Scenario corpus counts ────────────────────────────────────────────────
base = os.path.join("data", "scenarios")
checks = [("public/easy", 15), ("public/medium", 12), ("public/hard", 8), ("hidden/easy", 3), ("hidden/medium", 2), ("hidden/hard", 2)]
for tier, min_count in checks:
    full = os.path.join(base, tier)
    files = [f for f in os.listdir(full) if f.endswith(".json")]
    assert len(files) >= min_count, f"{tier}: only {len(files)} (need {min_count})"
    with open(os.path.join(full, files[0])) as f:
        s = json.load(f)
    assert "gold_annotations" in s and "diff_text" in s and "source" in s, f"Bad schema in {tier}/{files[0]}"
PASS(f"scenario corpus  all {sum(c for _,c in checks)}+ files with correct schema")

# ── 7. Hidden scenarios never served ─────────────────────────────────────────
pub_scenarios = _get_scenarios("simple_review")
hidden_ids = {"scenario_h_001", "scenario_h_002", "scenario_h_003"}
served_ids = {s.get("id", "") for s in pub_scenarios}
assert not (hidden_ids & served_ids), f"Hidden leaked: {hidden_ids & served_ids}"
PASS(f"hidden scenarios not served  public_simple_review_count={len(pub_scenarios)}")

# ── 8. Difficulty validator ──────────────────────────────────────────────────
warn = validate_task_difficulty("easy", num_files=5, lines_changed=300, num_hidden_issues=6)
assert len(warn) >= 3
ok = validate_task_difficulty("easy", num_files=1, lines_changed=20, num_hidden_issues=1)
assert ok == []
PASS(f"difficulty_validator  overspec_warnings={len(warn)}  clean_task_warnings={len(ok)}")

# ── 9. SEVERITY_MAP spot-checks ──────────────────────────────────────────────
assert SEVERITY_MAP["sql_injection"] == "critical"
assert SEVERITY_MAP["naming_convention"] == "nit"
assert SEVERITY_MAP["off_by_one"] == "major"
PASS("SEVERITY_MAP spot-checks")

# ── 10. Models new fields ────────────────────────────────────────────────────
a = ReviewAction(action_type="retract_comment", comment_id="abc123")
assert a.comment_id == "abc123"
a2 = ReviewAction(action_type="request_clarification", question="why?")
assert a2.question == "why?"
st = ReviewState(episode_id="ep1", step_count=0)
assert st.can_still_comment and st.turn == 0 and st.comments_so_far == []
tc = TaskConfig(id="t1", difficulty="easy", description="x", max_steps=10, num_files=1, lines_changed=20)
assert tc.cross_file_deps == False
PASS("models -- all new fields validated")

print()
print("=" * 55)
print("ALL 10 INTEGRATION TESTS PASSED")
print("=" * 55)
