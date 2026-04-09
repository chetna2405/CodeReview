---
title: CodeReviewEnv
emoji: "🔍"
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 8000
---

# CodeReviewEnv 🔍

**An OpenEnv-compliant environment for AI code review benchmarking.**

Agents review GitHub-style PR diffs, flag bugs, classify severity, debate with a simulated PR author — graded against expert annotations using a multi-signal composite score.

> Built for the **Scaler × Meta × PyTorch Hackathon 2026**

---

## 🎯 What This Environment Does

CodeReviewEnv presents an agent with a PR diff and asks it to perform a thorough, multi-turn code review. Each episode runs for up to `MAX_STEPS` turns. The agent can:

1. **Add comments** — flag specific lines with a severity level and descriptive message
2. **Retract comments** — remove a previously added comment by `comment_id`
3. **Request clarification** — ask the PR author a question (simulated response returned)
4. **Finalize review** — submit the review (ends the episode, triggers grader)
5. **Approve / Request changes** — legacy terminal actions (backward compatible)

The grader evaluates the agent's review against expert annotations:

| Signal | Weight | Description |
|--------|--------|-------------|
| Issue Detection F1 | **50%** | Precision & recall of flagged issues. Spamming kills precision. |
| Severity Accuracy | **30%** | Ordinal penalty: off-by-one = 0.67, off-by-two = 0.33 |
| Comment Quality | **20%** | Word overlap + n-gram similarity vs expert description |

**Formula:** `0.5 × F1 + 0.3 × severity_acc + 0.2 × comment_quality`

---

## 🚀 Quick Start

### Install

```bash
pip install openenv-core
pip install -e .
```

### Run Locally

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/tasks
curl http://localhost:8000/leaderboard
```

### Run with Docker

```bash
docker build -t code-review-env -f server/Dockerfile .
docker run -p 8000:8000 code-review-env
```

---

## 📋 Available Tasks

| Task ID | Difficulty | Public Scenarios | Description |
|---------|-----------|-----------------|-------------|
| `simple_review` | Easy | 25+ | Obvious bugs: off-by-one, null checks, hardcoded secrets, typos |
| `logic_review` | Medium | 22+ | Subtle logic errors: race conditions, timing attacks, resource leaks |
| `security_review` | Hard | 18+ | OWASP Top-10: SQLi, RCE, auth bypass, SSTI, path traversal, CSRF |
| `cross_file_review` | Hard | 3+ | Cross-file dependency bugs spanning multiple files |

> **Hidden set:** 20% of scenarios are held back and never served via any API endpoint. They are used for final evaluation only. Baseline scores reflect the public set only.

---

## 🔌 API Endpoints

### `POST /api/reset`
Start a new multi-turn code review episode.

```json
{ "task_id": "simple_review", "seed": 42 }
```

**Response:** `DiffObservation` with the PR diff, commit message, and file context.

### `POST /api/step`
Execute a review action.

```json
{ "action_type": "add_comment", "line_number": 15, "severity": "critical",
  "message": "SQL injection via f-string interpolation" }
```

```json
{ "action_type": "retract_comment", "comment_id": "a3f1b2c4" }
```

```json
{ "action_type": "request_clarification", "question": "Was this intentional?" }
```

```json
{ "action_type": "stand_firm", "comment_id": "a3f1b2c4" }
```

```json
{ "action_type": "escalate", "comment_id": "a3f1b2c4", "severity": "critical", "message": "This is definitely a blocker." }
```

```json
{ "action_type": "fetch_context", "file": "utils.py", "lines": "1-50" }
```

```json
{ "action_type": "finalize_review", "reason": "Two critical issues found" }
```

**Response:** Updated observation with partial reward, `author_responses` (for clarifications), and `comment_id` (for new comments).

### `GET /api/context`
Fetch repository file context beyond the diff (simulates real codebase navigation).

```
GET /api/context?task_id=simple_review&file=utils.py&lines=1-80
```

> ⚠️ In a scored episode, fetching context should cost one turn. Use strategically.

### `GET /grader`
Detailed grader results after episode completion.

### `GET /leaderboard`
All baseline runs sorted by mean score descending. Includes per-category skill scores and delta from the last run of the same model.

### `POST /baseline`
Run the rule-based baseline against all public tasks and persist to `leaderboard.json`.

```json
{ "model": "my-model-name", "seed": 42 }
```

---

## 📊 Action & Observation Spaces

### Action Space (`ReviewAction`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action_type` | `str` | Yes | `add_comment` \| `retract_comment` \| `fetch_context` \| `stand_firm` \| `escalate` \| `request_clarification` \| `finalize_review` \| `approve` \| `request_changes` |
| `line_number` | `int` | For add_comment | Line number in the diff |
| `severity` | `str` | For add_comment, escalate | `critical` \| `major` \| `minor` \| `nit` |
| `message` | `str` | For add_comment, escalate | Description of the issue |
| `file` | `str` | For add_comment, fetch_context | Filename the line or context belongs to |
| `lines` | `str` | For fetch_context | Line range to fetch (e.g. `1-50`) |
| `comment_id` | `str` | For retract/stand_firm/escalate | ID of comment |
| `question` | `str` | For request_clarification | Question for the author |
| `reason` | `str` | For finalize_review | Summary of review findings |

### Observation Space (`DiffObservation`)

| Field | Type | Description |
|-------|------|-------------|
| `diff_text` | `str` | Unified diff format |
| `commit_message` | `str` | PR commit message |
| `pr_description` | `str` | PR description |
| `file_context` | `str` | Full file content for context |
| `existing_comments` | `list` | Agent's comments so far (each has `comment_id`) |
| `author_responses` | `list[str]` | Simulated author replies to clarification requests |
| `can_still_comment` | `bool` | False after finalize_review |
| `step_num` / `max_steps` | `int` | Episode progress |
| `done` | `bool` | Episode complete? |
| `reward` | `float` | Cumulative reward signal (0.0–1.0) |

---

## 🧪 Severity System

4-level ordinal severity with penalty scoring:

| Severity | Examples | Ordinal |
|----------|----------|---------|
| `critical` | SQL injection, auth bypass, RCE, hardcoded secrets | 3 |
| `major` | Off-by-one, race condition, memory leak, silent failure | 2 |
| `minor` | Missing validation, poor error message, bad retry logic | 1 |
| `nit` | Missing docstring, naming convention, unused variable | 0 |

Severity score: `exact=1.0`, `off-by-one=0.67`, `off-by-two=0.33`, `off-by-three=0.0`

---

## 🏆 Leaderboard & Skill Regression Tracking

The `/leaderboard` endpoint returns all runs sorted by mean score, with **per-category skill breakdown**:

```json
{
  "model": "gpt-4o-mini",
  "timestamp": "2026-04-07T18:00:00Z",
  "scores": { "simple_review": 0.71, "logic_review": 0.52, "security_review": 0.44 },
  "mean": 0.557,
  "category_scores": { "security": 0.61, "logic": 0.55, "style": 0.72, "cross_file": 0.38 },
  "delta_from_last_run": { "security": +0.08, "logic": -0.03 }
}
```

This lets you diagnose *what* improved or regressed between fine-tuning runs — not just total score.

---

## 🤖 Simulated PR Author Persona

When the agent evaluates code, the environment will automatically generate an author response for each comment using an LLM (requires `HF_TOKEN`). 
The agent will see these responses mapped to their comments and can decide to:
- **Stand firm** — keep the comment and finalize (bonus for standing firm on true positives incorrectly disputed by the author)
- **Retract** — remove the comment if the author's response is convincing (penalty for retracting a true positive)
- **Escalate** — modify a comment's severity or message based on the author response

Each episode simulates an author with a randomly assigned persona (`defensive`, `collaborative`, or `dismissive`), forcing agents to adapt their pushback accordingly.

---

## 🗂️ Cross-file Dependency Bugs

The `cross_file_review` task introduces a new tier of difficulty. To successfully find these bugs, agents must:
- Detect the causal root in one file.
- Detect the downstream silent failure in another file.
- Flag BOTH files with an explanation of the causal chain matching the gold annotation.
- Use the new `fetch_context` action to look up surrounding file contexts beyond the diff lines provided to correlate changes. 
*(Note: Excessive use of context fetches is penalized algorithmically).*

---

## 🎓 RL Training with TRL

Connect CodeReviewEnv to a real PPO training loop:

```bash
# Start the env server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# In another terminal — run PPO training
python trl_example.py \
  --model-name Qwen/Qwen2.5-0.5B-Instruct \
  --task-id simple_review \
  --episodes 50 \
  --env-url http://localhost:8000
```

The `collect_episode()` function in `trl_example.py` resets the env, runs the model, and collects step-level rewards for PPO updates.

> 📓 **Colab notebook:** [Open in Colab](https://colab.research.google.com/github/your-org/CodeReviewEnv/blob/main/colab_ppo_example.ipynb)

---

## 📊 Baseline Results

Evaluated on the public scenario set. Hidden set used for final evaluation.

| Task ID | Difficulty | Composite Score |
|---------|------------|-----------------|
| `simple_review` | Easy | **0.6680** |
| `logic_review` | Medium | **0.5239** |
| `security_review` | Hard | **0.5562** |

**Average: 0.5827** (Qwen2.5-72B, public set)

---

## 🏗️ Project Structure

```
OpenEnv/
├── models.py                     # Typed Pydantic models (Action, Observation, State, TaskConfig)
├── client.py                     # EnvClient subclass for remote use
├── baseline.py                   # Standalone baseline inference script
├── trl_example.py                # 🆕 PPO training loop via TRL
├── generate_scenarios.py         # 🆕 Scenario corpus generator
├── leaderboard.json              # 🆕 Persisted baseline runs (auto-created)
├── data/
│   ├── easy/scenarios.json       # Legacy 10x easy scenarios
│   ├── medium/scenarios.json     # Legacy 10x medium scenarios
│   ├── hard/scenarios.json       # Legacy 10x hard scenarios
│   └── scenarios/
│       ├── public/               # 🆕 35 new public scenarios (80%)
│       │   ├── easy/             # 15 scenarios
│       │   ├── medium/           # 12 scenarios
│       │   └── hard/             # 8 scenarios
│       └── hidden/               # 🆕 7 hidden scenarios (20%) — never served via API
│           ├── easy/             # 3 scenarios
│           ├── medium/           # 2 scenarios
│           └── hard/             # 2 scenarios
└── server/
    ├── app.py                    # FastAPI app — /leaderboard, /baseline, /api/context
    ├── code_review_environment.py # Multi-turn environment (retract, clarify, finalize)
    ├── grader.py                 # 🆕 Ordinal severity scoring, updated weights 0.5/0.3/0.2
    ├── difficulty_validator.py   # 🆕 Structural difficulty consistency checker
    ├── Dockerfile
    └── requirements.txt
```

---

## 🧪 Grader Details

The grader is fully **deterministic** — no LLM required. It uses:

1. **Line-number matching** (±3 line tolerance) to match agent comments to gold annotations
2. **Ordinal severity penalty** — off-by-one level = 0.67 (not binary match/miss)
3. **Word overlap + n-gram Dice coefficient** for comment quality
4. **False positive penalty** — precision is part of F1; spamming every line is penalized

A random-flag agent scores ~0.08, confirming exploit-resistance.

---

## 📜 License

MIT License — built for the Scaler × Meta × PyTorch Hackathon 2026.
