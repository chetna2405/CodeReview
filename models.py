"""
Typed data models for CodeReviewEnv.

Defines Action, Observation, and State dataclasses following
the OpenEnv specification using Python dataclasses.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal

from openenv.core.env_server.types import Action, Observation, State


# ─── Action ───────────────────────────────────────────────────────────────────

@dataclass
class ReviewAction(Action):
    """
    An action the agent takes during a code review episode.

    Supported action types:
        - add_comment: Flag a specific line with a severity and message.
        - approve: Approve the PR (ends the episode).
        - request_changes: Request changes with a reason (ends the episode).
    """
    action_type: Literal["add_comment", "approve", "request_changes"] = "add_comment"

    # For add_comment actions
    line_number: Optional[int] = None
    severity: Optional[Literal["critical", "major", "minor", "nit"]] = None
    message: Optional[str] = None

    # For request_changes actions
    reason: Optional[str] = None


# ─── Observation ──────────────────────────────────────────────────────────────

@dataclass
class DiffObservation(Observation):
    """
    What the agent sees at each step of a code review episode.

    Contains the PR diff, context, and feedback from previous actions.
    """
    # Core PR content
    diff_text: str = ""
    commit_message: str = ""
    pr_description: str = ""
    file_path: str = ""
    file_context: str = ""

    # Task metadata
    task_id: str = ""
    step_num: int = 0
    max_steps: int = 10

    # Agent's prior actions this episode
    existing_comments: list = field(default_factory=list)

    # Episode signals
    done: bool = False
    reward: float = 0.0
    metadata: dict = field(default_factory=dict)


# ─── State ────────────────────────────────────────────────────────────────────

@dataclass
class ReviewState(State):
    """
    Internal episode state tracked by the environment.
    """
    episode_id: str = ""
    step_count: int = 0
    task_id: str = ""
    scenario_id: str = ""
    comments_made: int = 0
    issues_found: int = 0
    max_steps: int = 10
    is_done: bool = False
    final_score: Optional[float] = None


# ─── Gold Annotation (internal, not exposed to agent) ────────────────────────

@dataclass
class GoldAnnotation:
    """
    Expert annotation for a single issue in a diff scenario.
    Used by the grader to evaluate agent performance.
    """
    line_number: int = 0
    severity: str = "major"
    issue_type: str = "bug"
    description: str = ""
    explanation: str = ""


@dataclass
class DiffScenario:
    """
    A complete diff scenario with metadata and gold annotations.
    Loaded from JSON files in the data/ directory.
    """
    id: str = ""
    difficulty: str = "easy"
    diff_text: str = ""
    commit_message: str = ""
    pr_description: str = ""
    file_path: str = ""
    file_context: str = ""
    language: str = "python"
    annotations: list = field(default_factory=list)  # List[GoldAnnotation]

    def get_annotations(self) -> list:
        """Parse annotations into GoldAnnotation objects."""
        result = []
        for ann in self.annotations:
            if isinstance(ann, dict):
                result.append(GoldAnnotation(**ann))
            elif isinstance(ann, GoldAnnotation):
                result.append(ann)
        return result
