"""
CodeReviewEnvironment — Core environment logic.

Implements the OpenEnv Environment interface:
  - reset(task_id, scenario_id, seed): Start a new multi-turn code review episode
  - step(action): Process a review action
      Supported: add_comment, retract_comment, request_clarification,
                 finalize_review, approve, request_changes
  - state: Return current episode state

Episodes support up to MAX_STEPS turns. The agent accumulates comments across
turns and receives a cumulative partial reward each step. Final reward is
computed by grade_episode() on the complete comment set.
"""

import json
import os
import random
import sys
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

from openenv.core.env_server import Environment
from openenv.core.env_server.types import Action, Observation, State

try:
    from models import ReviewAction, DiffObservation, ReviewState
    from server.grader import grade_episode, compute_partial_reward
    from server.author_persona import generate_author_response
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import ReviewAction, DiffObservation, ReviewState
    from server.grader import grade_episode, compute_partial_reward
    from server.author_persona import generate_author_response


# ─── Data loading ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
PUBLIC_SCENARIOS_DIR = DATA_DIR / "scenarios" / "public"

TASK_CONFIG = {
    "simple_review": {
        "difficulty": "easy",
        "data_dirs": [
            PUBLIC_SCENARIOS_DIR / "easy",
            DATA_DIR / "easy",               # legacy fallback
        ],
        "max_steps": 10,
        "description": "Identify obvious bugs in short Python diffs (< 50 lines changed)",
        "num_files": 1,
        "lines_changed_range": "<50",
        "num_hidden_issues_range": "1-2",
        "cross_file_deps": False,
        "author_persona": "defensive",
    },
    "logic_review": {
        "difficulty": "medium",
        "data_dirs": [
            PUBLIC_SCENARIOS_DIR / "medium",
            DATA_DIR / "medium",
        ],
        "max_steps": 15,
        "description": "Detect subtle logic errors in realistic PRs (50-200 lines, 2-4 issues)",
        "num_files": 2,
        "lines_changed_range": "50-200",
        "num_hidden_issues_range": "2-4",
        "cross_file_deps": True,
        "author_persona": "defensive",
    },
    "security_review": {
        "difficulty": "hard",
        "data_dirs": [
            PUBLIC_SCENARIOS_DIR / "hard",
            DATA_DIR / "hard",
        ],
        "max_steps": 20,
        "description": "Find security vulnerabilities (OWASP Top-10): SQLi, RCE, auth bypass, XSS",
        "num_files": 3,
        "lines_changed_range": "50-200+",
        "num_hidden_issues_range": "2-5",
        "cross_file_deps": True,
        "author_persona": "defensive",
    },
    "cross_file_review": {
        "difficulty": "hard",
        "data_dirs": [
            PUBLIC_SCENARIOS_DIR / "hard",
        ],
        "max_steps": 20,
        "description": "Cross-file dependency bugs that span multiple files",
        "num_files": 2,
        "lines_changed_range": "50-200",
        "num_hidden_issues_range": "1-2",
        "cross_file_deps": True,
        "cross_file": True,
        "author_persona": "defensive",
    },
}

# Simulated author responses to agent clarification requests
_AUTHOR_RESPONSES = [
    "Good question — I introduced this change to handle the edge case described in the PR description.",
    "You're right to flag that. The intent was to simplify the code, but I may have missed something.",
    "This was intentional — we handle that case upstream before calling this function.",
    "I can add more context in the PR description. The change was reviewed by the team lead.",
    "Actually, you've identified a real issue there. I'll fix it before merging.",
    "That line was copied from the legacy codebase. I'm not sure if it's correct either.",
    "We have tests covering that code path. Let me double-check they still pass.",
    "Fair point — I'll add a comment explaining the reason for this pattern.",
]


def _load_scenarios(data_dirs: List[Path]) -> List[dict]:
    """
    Load all scenario JSON files from multiple directories.
    Supports both:
      - A single scenarios.json array file (legacy format)
      - Individual scenario_NNN.json files (new format)
    """
    scenarios: List[dict] = []
    seen_ids: set = set()

    for data_dir in data_dirs:
        if not data_dir.exists():
            continue

        # Try individual JSON files first (new format)
        json_files = sorted(data_dir.glob("scenario_*.json"))
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    scenario = json.load(f)
                    if isinstance(scenario, dict):
                        sid = scenario.get("id", json_file.stem)
                        if sid not in seen_ids:
                            scenarios.append(scenario)
                            seen_ids.add(sid)
            except (json.JSONDecodeError, OSError):
                pass

        # Also try monolithic scenarios.json (legacy)
        scenarios_file = data_dir / "scenarios.json"
        if scenarios_file.exists():
            try:
                with open(scenarios_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for s in data:
                            sid = s.get("id", "")
                            if sid not in seen_ids:
                                scenarios.append(s)
                                seen_ids.add(sid)
            except (json.JSONDecodeError, OSError):
                pass

    return scenarios


_SCENARIOS_CACHE: dict[str, List[dict]] = {}


def _get_scenarios(task_id: str) -> List[dict]:
    """Get public scenarios for a task (cached). Never returns hidden scenarios."""
    if task_id not in _SCENARIOS_CACHE:
        config = TASK_CONFIG.get(task_id)
        if config:
            _SCENARIOS_CACHE[task_id] = _load_scenarios(config["data_dirs"])
        else:
            _SCENARIOS_CACHE[task_id] = []
    return _SCENARIOS_CACHE[task_id]


def _normalize_annotations(scenario: dict) -> List[dict]:
    """Normalize gold annotation field names across old and new formats."""
    raw = scenario.get("gold_annotations") or scenario.get("annotations") or []
    normalized = []
    for ann in raw:
        normalized.append({
            "line_number": ann.get("line_number", ann.get("line", 0)),
            "severity": ann.get("severity", "major"),
            "description": ann.get("description", ann.get("issue", "")),
            "type": ann.get("type", ann.get("issue_type", "bug")),
            "reference": ann.get("reference", ""),
        })
    return normalized


# ─── Environment ──────────────────────────────────────────────────────────────

class CodeReviewEnvironment(Environment[ReviewAction, DiffObservation, ReviewState]):
    """
    OpenEnv environment for AI code review benchmarking.

    Supports multi-turn episodes where the agent can:
      - add_comment: Flag a line with severity + message
      - retract_comment: Remove a previously added comment by comment_id
      - request_clarification: Ask the author a question (simulated response)
      - finalize_review: Submit the review (terminates episode, triggers grader)
      - approve: Legacy terminal — approve the PR
      - request_changes: Legacy terminal — request changes

    Reward is cumulative across turns. Final reward = F1-based composite score.
    """

    TERMINAL_ACTIONS = {"approve", "request_changes", "finalize_review"}

    def __init__(self):
        super().__init__()
        self._state = ReviewState(episode_id=str(uuid4()), step_count=0)
        self._current_scenario: Optional[dict] = None
        self._agent_comments: List[dict] = []
        self._gold_annotations: List[dict] = []
        self._final_verdict: str = ""
        self._episode_results: dict[str, Any] = {}
        self._reward_bonus: float = 0.0
        self._reward_penalty: float = 0.0

    # ─── reset ────────────────────────────────────────────────────────────────

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DiffObservation:
        """Reset the environment and start a new multi-turn code review episode."""
        if task_id is None:
            task_id = kwargs.get("task_id", "simple_review")

        if task_id not in TASK_CONFIG:
            return DiffObservation(
                done=True,
                reward=0.0,
                metadata={"error": f"Unknown task_id: {task_id}. Valid: {list(TASK_CONFIG.keys())}"},
            )

        config = TASK_CONFIG[task_id]
        scenarios = _get_scenarios(task_id)

        if not scenarios:
            return DiffObservation(
                done=True,
                reward=0.0,
                metadata={"error": f"No scenarios found for task '{task_id}'"},
            )

        if seed is not None:
            random.seed(seed)

        if scenario_id:
            scenario = next((s for s in scenarios if s.get("id") == scenario_id), None)
            if scenario is None:
                scenario = random.choice(scenarios)
        else:
            scenario = random.choice(scenarios)

        self._current_scenario = scenario
        self._agent_comments = []
        self._gold_annotations = _normalize_annotations(scenario)
        self._final_verdict = ""
        self._episode_results = {}
        self._reward_bonus = 0.0
        self._reward_penalty = 0.0

        eid = episode_id or str(uuid4())
        self._state = ReviewState(
            episode_id=eid,
            step_count=0,
            turn=0,
            task_id=task_id,
            scenario_id=scenario.get("id", ""),
            comments_so_far=[],
            author_responses=[],
            author_response_map={},
            context_fetch_count=0,
            can_still_comment=True,
            comments_made=0,
            issues_found=0,
            max_steps=config["max_steps"],
            is_done=False,
            final_score=None,
        )

        return DiffObservation(
            diff_text=scenario.get("diff_text", ""),
            commit_message=scenario.get("commit_message", ""),
            pr_description=scenario.get("pr_description", ""),
            file_path=scenario.get("file_path", ""),
            file_context=scenario.get("file_context", ""),
            task_id=task_id,
            step_num=0,
            max_steps=config["max_steps"],
            existing_comments=[],
            author_responses=[],
            can_still_comment=True,
            done=False,
            reward=0.0,
            metadata={
                "status": "ready",
                "scenario_id": scenario.get("id", ""),
                "difficulty": scenario.get("difficulty", config["difficulty"]),
                "episode_id": eid,
                "source": scenario.get("source", {}),
            },
        )

    # ─── step ─────────────────────────────────────────────────────────────────

    def step(
        self,
        action: ReviewAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> DiffObservation:
        """
        Process a review action.

        Supported action types:
          add_comment, retract_comment, request_clarification,
          finalize_review, approve, request_changes
        """
        if self._state.is_done:
            return DiffObservation(
                done=True,
                reward=0.0,
                metadata={"error": "Episode already complete. Call reset() to start a new one."},
            )

        # Parse action
        action_type, line_number, severity, message, comment_id, question, reason, file, lines = \
            self._parse_action(action)

        if action_type not in (
            "add_comment", "retract_comment", "request_clarification",
            "stand_firm", "escalate", "fetch_context",
            "finalize_review", "approve", "request_changes"
        ):
            return self._make_obs(
                reward=0.0,
                metadata={"error": f"Invalid action_type: '{action_type}'. "
                          "Valid: add_comment, retract_comment, stand_firm, escalate, fetch_context, request_clarification, "
                          "finalize_review, approve, request_changes"},
            )

        # Advance turn counter
        self._state = self._state.model_copy(update={
            "step_count": self._state.step_count + 1,
            "turn": self._state.turn + 1,
        })

        reward = 0.0

        # ── add_comment ──────────────────────────────────────────────────────
        if action_type == "add_comment":
            if line_number is None or message is None:
                return self._make_obs(
                    reward=0.0,
                    metadata={"error": "add_comment requires line_number and message."},
                )
            from uuid import uuid4
            cid = str(uuid4())[:8]
            comment = {
                "comment_id": cid,
                "line_number": line_number,
                "severity": severity or "major",
                "message": message,
                "step": self._state.step_count,
            }
            self._agent_comments.append(comment)
            
            # Author persona response
            persona = TASK_CONFIG[self._state.task_id].get("author_persona", "defensive")
            is_true_positive = any(abs(ann.get("line_number", ann.get("line", 0)) - line_number) <= 3 for ann in self._gold_annotations)
            hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            response = generate_author_response(persona, message, is_true_positive, hf_token)
            
            new_comments = list(self._state.comments_so_far) + [comment]
            new_responses = list(self._state.author_responses) + [response]
            new_map = dict(self._state.author_response_map)
            new_map[cid] = response
            
            self._state = self._state.model_copy(update={
                "comments_so_far": new_comments,
                "comments_made": self._state.comments_made + 1,
                "author_responses": new_responses,
                "author_response_map": new_map,
            })
            reward = compute_partial_reward(self._agent_comments, self._gold_annotations)

        # ── retract_comment ──────────────────────────────────────────────────
        elif action_type == "retract_comment":
            if comment_id is None:
                return self._make_obs(
                    reward=0.0,
                    metadata={"error": "retract_comment requires comment_id."},
                )
            
            # Feature 1 bonus/penalty logic
            if comment_id in self._state.author_response_map:
                comment_line = next((c.get("line_number", 0) for c in self._agent_comments if c.get("comment_id") == comment_id), 0)
                is_true_positive = any(abs(ann.get("line_number", ann.get("line", 0)) - comment_line) <= 3 for ann in self._gold_annotations)
                if is_true_positive:
                    self._reward_penalty += 0.1
            
            before = len(self._agent_comments)
            self._agent_comments = [
                c for c in self._agent_comments if c.get("comment_id") != comment_id
            ]
            removed = before - len(self._agent_comments)
            new_comments = [
                c for c in self._state.comments_so_far if c.get("comment_id") != comment_id
            ]
            self._state = self._state.model_copy(update={
                "comments_so_far": new_comments,
                "comments_made": max(0, self._state.comments_made - removed),
            })
            reward = compute_partial_reward(self._agent_comments, self._gold_annotations)

        # ── stand_firm ───────────────────────────────────────────────────────
        elif action_type == "stand_firm":
            if comment_id not in self._state.author_response_map:
                return self._make_obs(
                    reward=0.0,
                    metadata={"error": "stand_firm requires a valid comment_id with an author response."},
                )
            comment_line = next((c.get("line_number", 0) for c in self._agent_comments if c.get("comment_id") == comment_id), 0)
            is_true_positive = any(abs(ann.get("line_number", ann.get("line", 0)) - comment_line) <= 3 for ann in self._gold_annotations)
            if is_true_positive:
                self._reward_bonus += 0.05
            reward = compute_partial_reward(self._agent_comments, self._gold_annotations)

        # ── escalate ─────────────────────────────────────────────────────────
        elif action_type == "escalate":
            if comment_id not in self._state.author_response_map:
                return self._make_obs(
                    reward=0.0,
                    metadata={"error": "escalate requires a valid comment_id with an author response."},
                )
            for c in self._agent_comments:
                if c.get("comment_id") == comment_id:
                    if severity: c["severity"] = severity
                    if message: c["message"] = message
            
            reward = compute_partial_reward(self._agent_comments, self._gold_annotations)

        # ── fetch_context ────────────────────────────────────────────────────
        elif action_type == "fetch_context":
            self._state = self._state.model_copy(update={
                "context_fetch_count": self._state.context_fetch_count + 1
            })
            reward = compute_partial_reward(self._agent_comments, self._gold_annotations)

        # ── request_clarification ────────────────────────────────────────────
        elif action_type == "request_clarification":
            response = random.choice(_AUTHOR_RESPONSES)
            new_responses = list(self._state.author_responses) + [response]
            self._state = self._state.model_copy(update={
                "author_responses": new_responses,
            })
            reward = 0.0  # No reward for clarification itself

        # ── terminal actions (finalize_review / approve / request_changes) ───
        elif action_type in self.TERMINAL_ACTIONS:
            self._final_verdict = action_type
            self._state = self._state.model_copy(update={
                "is_done": True,
                "can_still_comment": False,
            })
            grader_result = grade_episode(
                agent_comments=self._agent_comments,
                gold_annotations=self._gold_annotations,
                final_verdict=action_type,
                scenario=self._current_scenario,
            )
            
            # Apply context penalty and persona bonuses
            final_reward = grader_result.composite_score + self._reward_bonus - self._reward_penalty
            
            diff_level = TASK_CONFIG[self._state.task_id].get("difficulty", "easy")
            if diff_level == "easy" and self._state.context_fetch_count > 3:
                excess_calls = self._state.context_fetch_count - 3
                final_reward -= (0.05 * excess_calls)
            
            final_reward = max(0.0, min(1.0, final_reward))
            
            self._state = self._state.model_copy(update={
                "final_score": final_reward,
                "issues_found": grader_result.issues_found,
            })
            reward = final_reward
            self._episode_results = self._build_episode_results(grader_result, action_type)
            self._episode_results["composite_score"] = final_reward

        # Check max steps reached (auto-terminate)
        is_done = self._state.is_done or self._state.step_count >= self._state.max_steps
        if is_done and not self._state.is_done:
            self._state = self._state.model_copy(update={"is_done": True, "can_still_comment": False})
            grader_result = grade_episode(
                agent_comments=self._agent_comments,
                gold_annotations=self._gold_annotations,
                final_verdict="timeout",
                scenario=self._current_scenario,
            )
            
            final_reward = grader_result.composite_score + self._reward_bonus - self._reward_penalty
            diff_level = TASK_CONFIG[self._state.task_id].get("difficulty", "easy")
            if diff_level == "easy" and self._state.context_fetch_count > 3:
                final_reward -= (0.05 * (self._state.context_fetch_count - 3))
            final_reward = max(0.0, min(1.0, final_reward))
            
            self._state = self._state.model_copy(update={
                "final_score": final_reward,
                "issues_found": grader_result.issues_found,
            })
            reward = final_reward
            self._episode_results = self._build_episode_results(grader_result, "timeout")
            self._episode_results["composite_score"] = final_reward

        return self._make_obs(reward=reward, done=is_done)

    # ─── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_action(action):
        """Extract fields from ReviewAction, dict, or duck-typed object."""
        if isinstance(action, dict):
            return (
                action.get("action_type", "add_comment"),
                action.get("line_number"),
                action.get("severity"),
                action.get("message"),
                action.get("comment_id"),
                action.get("question"),
                action.get("reason"),
                action.get("file"),
                action.get("lines"),
            )
        return (
            getattr(action, "action_type", "add_comment"),
            getattr(action, "line_number", None),
            getattr(action, "severity", None),
            getattr(action, "message", None),
            getattr(action, "comment_id", None),
            getattr(action, "question", None),
            getattr(action, "reason", None),
            getattr(action, "file", None),
            getattr(action, "lines", None),
        )

    def _build_episode_results(self, grader_result, verdict: str) -> dict:
        """Build the episode results dict from a GraderResult."""
        return {
            "composite_score": grader_result.composite_score,
            "f1_score": grader_result.f1_score,
            "precision": grader_result.precision,
            "recall": grader_result.recall,
            "severity_accuracy": grader_result.severity_accuracy,
            "comment_similarity": grader_result.comment_similarity,
            "issues_found": grader_result.issues_found,
            "issues_total": grader_result.issues_total,
            "false_positives": grader_result.false_positives,
            "verdict": verdict,
        }

    def _make_obs(
        self,
        reward: float = 0.0,
        done: bool = False,
        metadata: dict | None = None,
    ) -> DiffObservation:
        """Build a DiffObservation from current state."""
        meta = metadata or {}
        meta["episode_id"] = self._state.episode_id
        if self._state.is_done and self._episode_results:
            meta["episode_results"] = self._episode_results

        sc = self._current_scenario or {}
        return DiffObservation(
            diff_text=sc.get("diff_text", ""),
            commit_message=sc.get("commit_message", ""),
            pr_description=sc.get("pr_description", ""),
            file_path=sc.get("file_path", ""),
            file_context=sc.get("file_context", ""),
            task_id=self._state.task_id,
            step_num=self._state.step_count,
            max_steps=self._state.max_steps,
            existing_comments=list(self._agent_comments),
            author_responses=list(self._state.author_responses),
            can_still_comment=self._state.can_still_comment,
            done=done or self._state.is_done,
            reward=reward,
            metadata=meta,
        )

    # ─── public accessors ─────────────────────────────────────────────────────

    @property
    def state(self) -> ReviewState:
        """Return current episode state."""
        return self._state

    def get_tasks(self) -> List[dict]:
        """Return list of available tasks with metadata (public scenarios only)."""
        tasks = []
        for task_id, config in TASK_CONFIG.items():
            scenarios = _get_scenarios(task_id)
            tasks.append({
                "id": task_id,
                "difficulty": config["difficulty"],
                "description": config["description"],
                "max_steps": config["max_steps"],
                "num_scenarios": len(scenarios),
                "structural": {
                    "num_files": config.get("num_files", 1),
                    "lines_changed_range": config.get("lines_changed_range", ""),
                    "num_hidden_issues_range": config.get("num_hidden_issues_range", ""),
                    "cross_file_deps": config.get("cross_file_deps", False),
                },
            })
        return tasks

    def get_episode_results(self) -> dict:
        """Return grader results for the current (completed) episode."""
        if not self._state.is_done:
            return {"error": "Episode not complete. Submit finalize_review, approve, or request_changes first."}
        return self._episode_results
