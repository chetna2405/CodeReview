"""
CodeReviewEnvironment — Core environment logic.

Implements the OpenEnv Environment interface:
  - reset(task_id): Start a new code review episode
  - step(action): Process a review action (add_comment, approve, request_changes)
  - state: Return current episode state
"""

import json
import os
import random
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.types import Action, Observation, State
from openenv.core.env_server.environment import Environment

# Use relative imports when running as a package, fallback to direct imports
try:
    from models import ReviewAction, DiffObservation, ReviewState, DiffScenario
    from server.grader import grade_episode, compute_partial_reward
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import ReviewAction, DiffObservation, ReviewState, DiffScenario
    from server.grader import grade_episode, compute_partial_reward


# ─── Data loading ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"

TASK_CONFIG = {
    "simple_review": {
        "difficulty": "easy",
        "data_dir": DATA_DIR / "easy",
        "max_steps": 10,
        "description": "Identify obvious bugs in short Python diffs (<50 lines)",
    },
    "logic_review": {
        "difficulty": "medium",
        "data_dir": DATA_DIR / "medium",
        "max_steps": 15,
        "description": "Detect subtle logic errors in realistic PRs (100-200 lines)",
    },
    "security_review": {
        "difficulty": "hard",
        "data_dir": DATA_DIR / "hard",
        "max_steps": 20,
        "description": "Find security vulnerabilities (OWASP Top-10)",
    },
}


def _load_scenarios(data_dir: Path) -> list[dict]:
    """Load all scenario JSON files from a directory."""
    scenarios = []
    scenarios_file = data_dir / "scenarios.json"
    if scenarios_file.exists():
        with open(scenarios_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                scenarios.extend(data)
    return scenarios


# Pre-load all scenarios at module level
_SCENARIOS_CACHE: dict[str, list[dict]] = {}


def _get_scenarios(task_id: str) -> list[dict]:
    """Get scenarios for a task, loading from cache if available."""
    if task_id not in _SCENARIOS_CACHE:
        config = TASK_CONFIG.get(task_id)
        if config:
            _SCENARIOS_CACHE[task_id] = _load_scenarios(config["data_dir"])
        else:
            _SCENARIOS_CACHE[task_id] = []
    return _SCENARIOS_CACHE[task_id]


# ─── Environment ──────────────────────────────────────────────────────────────

class CodeReviewEnvironment(Environment):
    """
    OpenEnv environment for AI code review benchmarking.

    Agents review GitHub-style PR diffs, flag bugs, classify severity,
    and produce review comments — graded against expert annotations.
    """

    def __init__(self):
        super().__init__()
        self._state = ReviewState()
        self._current_scenario: Optional[dict] = None
        self._agent_comments: list[dict] = []
        self._gold_annotations: list[dict] = []
        self._final_verdict: str = ""
        self._episode_results: dict[str, Any] = {}

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Reset the environment and start a new code review episode.

        Args:
            seed: Random seed for scenario selection
            episode_id: Optional episode ID (auto-generated if not provided)
            task_id: Which task to run (simple_review, logic_review, security_review)
            scenario_id: Specific scenario ID to load (random if not provided)

        Returns:
            DiffObservation with the PR diff and context
        """
        # Default to simple_review if no task specified
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
                metadata={"error": f"No scenarios found for task {task_id}"},
            )

        # Select scenario
        if seed is not None:
            random.seed(seed)

        if scenario_id:
            scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
            if scenario is None:
                scenario = random.choice(scenarios)
        else:
            scenario = random.choice(scenarios)

        # Initialize episode state
        self._current_scenario = scenario
        self._agent_comments = []
        self._gold_annotations = scenario.get("annotations", [])
        self._final_verdict = ""

        self._state = ReviewState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=task_id,
            scenario_id=scenario["id"],
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
            done=False,
            reward=0.0,
            metadata={
                "status": "ready",
                "scenario_id": scenario["id"],
                "difficulty": scenario.get("difficulty", config["difficulty"]),
                "episode_id": self._state.episode_id,
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Process a review action.

        Args:
            action: ReviewAction (add_comment, approve, or request_changes)

        Returns:
            DiffObservation with updated state and reward signal
        """
        # Check if episode is already done
        if self._state.is_done:
            return DiffObservation(
                done=True,
                reward=0.0,
                metadata={"error": "Episode is already complete. Call reset() to start a new one."},
            )

        # Increment step count
        self._state.step_count += 1

        # Parse action — handle both ReviewAction and dict-like actions
        if isinstance(action, ReviewAction):
            action_type = action.action_type
            line_number = action.line_number
            severity = action.severity
            message = action.message
            reason = action.reason
        elif isinstance(action, dict):
            action_type = action.get("action_type", "add_comment")
            line_number = action.get("line_number")
            severity = action.get("severity")
            message = action.get("message")
            reason = action.get("reason")
        elif hasattr(action, "arguments"):
            # MCP-style CallToolAction
            args = action.arguments if isinstance(action.arguments, dict) else {}
            action_type = args.get("action_type", "add_comment")
            line_number = args.get("line_number")
            severity = args.get("severity")
            message = args.get("message")
            reason = args.get("reason")
        else:
            return DiffObservation(
                done=False,
                reward=0.0,
                metadata={"error": f"Unknown action type: {type(action).__name__}"},
            )

        # Validate action type
        if action_type not in ("add_comment", "approve", "request_changes"):
            return DiffObservation(
                diff_text=self._current_scenario.get("diff_text", "") if self._current_scenario else "",
                task_id=self._state.task_id,
                step_num=self._state.step_count,
                max_steps=self._state.max_steps,
                existing_comments=list(self._agent_comments),
                done=False,
                reward=0.0,
                metadata={
                    "error": f"Invalid action_type: {action_type}. Must be add_comment, approve, or request_changes.",
                    "validation_error": True,
                },
            )

        # Process action
        reward = 0.0

        if action_type == "add_comment":
            # Validate required fields
            if line_number is None or message is None:
                return DiffObservation(
                    diff_text=self._current_scenario.get("diff_text", "") if self._current_scenario else "",
                    task_id=self._state.task_id,
                    step_num=self._state.step_count,
                    max_steps=self._state.max_steps,
                    existing_comments=list(self._agent_comments),
                    done=False,
                    reward=0.0,
                    metadata={
                        "error": "add_comment requires line_number and message fields.",
                        "validation_error": True,
                    },
                )

            comment = {
                "line_number": line_number,
                "severity": severity or "major",
                "message": message,
                "step": self._state.step_count,
            }
            self._agent_comments.append(comment)
            self._state.comments_made += 1

            # Compute partial reward (how many gold issues found so far)
            reward = compute_partial_reward(self._agent_comments, self._gold_annotations)

        elif action_type in ("approve", "request_changes"):
            # Terminal actions — end episode and run grader
            self._final_verdict = action_type
            self._state.is_done = True

            grader_result = grade_episode(
                agent_comments=self._agent_comments,
                gold_annotations=self._gold_annotations,
                final_verdict=action_type,
            )

            self._state.final_score = grader_result.composite_score
            self._state.issues_found = grader_result.issues_found
            reward = grader_result.composite_score

            self._episode_results = {
                "composite_score": grader_result.composite_score,
                "f1_score": grader_result.f1_score,
                "precision": grader_result.precision,
                "recall": grader_result.recall,
                "severity_accuracy": grader_result.severity_accuracy,
                "comment_similarity": grader_result.comment_similarity,
                "issues_found": grader_result.issues_found,
                "issues_total": grader_result.issues_total,
                "false_positives": grader_result.false_positives,
                "verdict": action_type,
            }

        # Check if max steps reached
        is_done = self._state.is_done or self._state.step_count >= self._state.max_steps
        if is_done and not self._state.is_done:
            # Max steps reached without explicit verdict — auto-grade
            self._state.is_done = True
            grader_result = grade_episode(
                agent_comments=self._agent_comments,
                gold_annotations=self._gold_annotations,
                final_verdict="timeout",
            )
            self._state.final_score = grader_result.composite_score
            self._state.issues_found = grader_result.issues_found
            reward = grader_result.composite_score
            self._episode_results = {
                "composite_score": grader_result.composite_score,
                "f1_score": grader_result.f1_score,
                "precision": grader_result.precision,
                "recall": grader_result.recall,
                "severity_accuracy": grader_result.severity_accuracy,
                "comment_similarity": grader_result.comment_similarity,
                "issues_found": grader_result.issues_found,
                "issues_total": grader_result.issues_total,
                "false_positives": grader_result.false_positives,
                "verdict": "timeout",
            }

        return DiffObservation(
            diff_text=self._current_scenario.get("diff_text", "") if self._current_scenario else "",
            commit_message=self._current_scenario.get("commit_message", "") if self._current_scenario else "",
            pr_description=self._current_scenario.get("pr_description", "") if self._current_scenario else "",
            file_path=self._current_scenario.get("file_path", "") if self._current_scenario else "",
            file_context=self._current_scenario.get("file_context", "") if self._current_scenario else "",
            task_id=self._state.task_id,
            step_num=self._state.step_count,
            max_steps=self._state.max_steps,
            existing_comments=list(self._agent_comments),
            done=is_done,
            reward=reward,
            metadata={
                "episode_id": self._state.episode_id,
                "action_processed": action_type,
                **({"episode_results": self._episode_results} if is_done else {}),
            },
        )

    @property
    def state(self) -> State:
        """Return current episode state."""
        return self._state

    def get_tasks(self) -> list[dict]:
        """Return list of available tasks with metadata."""
        tasks = []
        for task_id, config in TASK_CONFIG.items():
            scenarios = _get_scenarios(task_id)
            tasks.append({
                "id": task_id,
                "difficulty": config["difficulty"],
                "description": config["description"],
                "max_steps": config["max_steps"],
                "num_scenarios": len(scenarios),
            })
        return tasks

    def get_episode_results(self) -> dict:
        """Return grader results for the current (completed) episode."""
        if not self._state.is_done:
            return {"error": "Episode not complete. Submit approve or request_changes first."}
        return self._episode_results
