"""
Typed data models for CodeReviewEnv.

Defines Action, Observation, and State as Pydantic models extending
the OpenEnv base types.
"""

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field

from openenv.core.env_server.types import Action, Observation, State


# ─── Action ───────────────────────────────────────────────────────────────────

class ReviewAction(Action):
    """
    An action the agent takes during a code review episode.

    Supported action types:
        - add_comment: Flag a specific line with a severity and message.
        - approve: Approve the PR (ends the episode).
        - request_changes: Request changes with a reason (ends the episode).
    """
    action_type: str = "add_comment"

    # For add_comment actions
    line_number: Optional[int] = None
    severity: Optional[str] = None
    message: Optional[str] = None

    # For request_changes actions
    reason: Optional[str] = None


# ─── Observation ──────────────────────────────────────────────────────────────

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
    existing_comments: list = Field(default_factory=list)


# ─── State ────────────────────────────────────────────────────────────────────

class ReviewState(State):
    """
    Internal episode state tracked by the environment.
    """
    task_id: str = ""
    scenario_id: str = ""
    comments_made: int = 0
    issues_found: int = 0
    max_steps: int = 10
    is_done: bool = False
    final_score: Optional[float] = None


# ─── Internal models (not exposed to agent) ──────────────────────────────────

class GoldAnnotation(BaseModel):
    """Expert annotation for a single issue in a diff scenario."""
    line_number: int = 0
    severity: str = "major"
    issue_type: str = "bug"
    description: str = ""
    explanation: str = ""


class DiffScenario(BaseModel):
    """A complete diff scenario with metadata and gold annotations."""
    id: str = ""
    difficulty: str = "easy"
    diff_text: str = ""
    commit_message: str = ""
    pr_description: str = ""
    file_path: str = ""
    file_context: str = ""
    language: str = "python"
    annotations: list = Field(default_factory=list)

    def get_annotations(self) -> list:
        """Parse annotations into GoldAnnotation objects."""
        result = []
        for ann in self.annotations:
            if isinstance(ann, dict):
                result.append(GoldAnnotation(**ann))
            elif isinstance(ann, GoldAnnotation):
                result.append(ann)
        return result
