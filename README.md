---
title: CodeReviewEnv
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
app_file: server/app.py
app_port: 8000
pinned: false
---

# CodeReviewEnv 🔍

**An OpenEnv-compliant environment for AI code review benchmarking.**

Agents review GitHub-style PR diffs, flag bugs, classify severity, and produce review comments — graded against expert annotations using a multi-signal composite score.

> Built for the **Scaler × Meta × PyTorch Hackathon 2026**

---

## 🎯 What This Environment Does

CodeReviewEnv presents an agent with a PR diff and asks it to perform a thorough code review. The agent can:

1. **Add comments** — flag specific lines with a severity level and descriptive message
2. **Approve** — approve the PR (ends the episode)
3. **Request changes** — request changes with a reason (ends the episode)

The grader evaluates the agent's review against expert annotations using three signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| Issue Detection F1 | 50% | Precision & recall of flagged issues vs gold annotations |
| Severity Accuracy | 25% | Correct severity classification for detected issues |
| Comment Quality | 25% | Semantic similarity of comments vs expert descriptions |

---

## 🚀 Quick Start

### Install

```bash
pip install openenv-core
pip install -e .
```

### Run Locally

```bash
# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# In another terminal — test the API
curl http://localhost:8000/health
curl http://localhost:8000/tasks
```

### Run with Docker

```bash
docker build -t code-review-env -f server/Dockerfile .
docker run -p 8000:8000 code-review-env
```

---

## 📋 Available Tasks

| Task ID | Difficulty | Scenarios | Description |
|---------|-----------|-----------|-------------|
| `simple_review` | Easy | 10 | Obvious bugs: off-by-one, null checks, typos |
| `logic_review` | Medium | 10 | Subtle logic errors: race conditions, edge cases |
| `security_review` | Hard | 10 | Security vulnerabilities: SQLi, RCE, auth bypass |

---

## 🔌 API Endpoints

### `POST /reset`
Start a new code review episode.

```json
{
  "task_id": "simple_review",
  "seed": 42
}
```

**Response:** `DiffObservation` with the PR diff, commit message, and file context.

### `POST /step`
Execute a review action.

```json
{
  "action_type": "add_comment",
  "line_number": 15,
  "severity": "critical",
  "message": "Off-by-one error: should be range(len(user_ids)) not range(len(user_ids) - 1)"
}
```

**Response:** Updated observation with partial reward signal.

### `GET /state`
Get current episode state (step count, comments made, etc).

### `GET /grader`
Get detailed grader results after episode completion.

### `GET /tasks`
List available tasks with metadata.

### `POST /baseline`
Run baseline inference using HuggingFace Inference API (requires `HF_TOKEN`).

---

## 📊 Action & Observation Spaces

### Action Space (`ReviewAction`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action_type` | `"add_comment" \| "approve" \| "request_changes"` | Yes | Type of review action |
| `line_number` | `int` | For add_comment | Line number in the diff |
| `severity` | `"critical" \| "major" \| "minor" \| "nit"` | For add_comment | Issue severity |
| `message` | `str` | For add_comment | Description of the issue |
| `reason` | `str` | For request_changes | Why changes are needed |

### Observation Space (`DiffObservation`)

| Field | Type | Description |
|-------|------|-------------|
| `diff_text` | `str` | Unified diff format |
| `commit_message` | `str` | PR commit message |
| `pr_description` | `str` | PR description |
| `file_path` | `str` | File being reviewed |
| `file_context` | `str` | Full file content |
| `task_id` | `str` | Current task |
| `step_num` | `int` | Current step in episode |
| `max_steps` | `int` | Maximum steps allowed |
| `existing_comments` | `list` | Agent's comments so far |
| `done` | `bool` | Episode complete? |
| `reward` | `float` | Reward signal (0.0–1.0) |

---

## 📊 Baseline Results (Qwen2.5-72B)

Evaluated across 30 scenarios (10 per task) using the Hugging Face Inference API.

| Task ID | Difficulty | Composite Score |
|---------|------------|-----------------|
| `simple_review` | Easy | **0.6680** |
| `logic_review` | Medium | **0.5239** |
| `security_review` | Hard | **0.5562** |

**Average Baseline Score: 0.5827**

---

## 🏃 Running the Baseline

```bash
# With HuggingFace Inference API
export HF_TOKEN=your_hf_token
python baseline.py

# Without API key (uses rule-based fallback)
python baseline.py

# Against a remote server
python baseline.py --base-url https://your-space.hf.space
```

---

## 🏗️ Project Structure

```
OpenEnv/
├── __init__.py              # Package exports
├── models.py                # Typed dataclasses (Action, Observation, State)
├── client.py                # EnvClient subclass for remote use
├── baseline.py              # Baseline inference script
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Dependencies
├── README.md                # This file
├── data/
│   ├── easy/scenarios.json  # 10 easy diff scenarios
│   ├── medium/scenarios.json # 10 medium diff scenarios
│   └── hard/scenarios.json  # 10 hard diff scenarios
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI application
    ├── code_review_environment.py  # Environment logic
    ├── grader.py            # Multi-signal grader
    ├── Dockerfile           # Container image
    └── requirements.txt     # Server dependencies
```

---

## 🧪 Grader Details

The grader is fully **deterministic** — no LLM required for grading. It uses:

1. **Line-number matching** (±3 line tolerance) to match agent comments to gold annotations
2. **Exact string matching** for severity classification
3. **Word overlap + n-gram Dice coefficient** for comment quality scoring

A random-flag agent scores ~0.08, confirming the grader is exploit-resistant.

---

## 📜 License

MIT License — built for the Scaler × Meta × PyTorch Hackathon 2026.
