"""
Typed data models for CodeReviewEnv.

Defines Action, Observation, and State as Pydantic models extending
the OpenEnv base types, plus TaskConfig and related helpers.
"""

from typing import Optional, Literal, Any, List
from pydantic import BaseModel, Field
from uuid import uuid4

from openenv.core.env_server.types import Action, Observation, State


# ─── Severity ────────────────────────────────────────────────────────────────

SEVERITY_LEVELS: List[str] = ["nit", "minor", "major", "critical"]
"""Ordered severity levels from least to most severe."""


# ─── Action ───────────────────────────────────────────────────────────────────

class ReviewAction(Action):
    """
    An action the agent takes during a code review episode.

    Supported action types:
        - add_comment: Flag a specific line with a severity and message.
        - retract_comment: Remove a previously added comment by comment_id.
        - stand_firm: Keep the comment active despite the author's response.
        - escalate: Add a stronger comment or modify severity after an author response.
        - request_clarification: Ask the author a question (legacy, simplified to persona-driven response per comment).
        - fetch_context: Request more lines around a given file to see outside the diff.
        - finalize_review: Submit the review and end the episode.
        - approve: Approve the PR (ends the episode). Legacy alias.
        - request_changes: Request changes (ends the episode). Legacy alias.
    """
    action_type: str = "add_comment"

    # For add_comment actions
    line_number: Optional[int] = None
    severity: Optional[str] = None
    message: Optional[str] = None

    # For retract_comment actions
    comment_id: Optional[str] = None

    # For fetch_context actions
    file: Optional[str] = None
    lines: Optional[str] = None

    # For request_clarification actions
    question: Optional[str] = None

    # For finalize_review / request_changes actions
    reason: Optional[str] = None


# ─── Observation ──────────────────────────────────────────────────────────────

class DiffObservation(Observation):
    """
    What the agent sees at each step of a code review episode.

    Contains the PR diff, context, feedback from previous actions,
    and any author responses to clarification requests.
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
    existing_comments: List[dict] = Field(default_factory=list)

    # Author responses to clarification requests (simulated)
    author_responses: List[str] = Field(default_factory=list)

    # Whether the agent can still add comments
    can_still_comment: bool = True


# ─── State ────────────────────────────────────────────────────────────────────

class ReviewState(State):
    """
    Internal episode state tracked by the environment.

    Tracks the full multi-turn context including all comments, author
    responses, and episode progress.
    """
    task_id: str = ""
    scenario_id: str = ""

    # Multi-turn tracking
    turn: int = 0                                   # Current turn number
    comments_so_far: List[dict] = Field(default_factory=list)  # All comments added
    author_responses: List[str] = Field(default_factory=list)  # Simulated responses
    author_response_map: dict = Field(default_factory=dict)         # map from comment_id to response
    context_fetch_count: int = 0                    # Number of times context was fetched
    can_still_comment: bool = True                  # False after finalize

    # Legacy fields (preserved for backward compat)
    comments_made: int = 0
    issues_found: int = 0
    max_steps: int = 10
    is_done: bool = False
    final_score: Optional[float] = None


# ─── TaskConfig ───────────────────────────────────────────────────────────────

class TaskConfig(BaseModel):
    """
    Structural configuration for a task difficulty level.

    Used by the difficulty validator to verify that task metadata
    is consistent with the difficulty label.
    """
    id: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    max_steps: int

    # Structural difficulty axes
    num_files: int = 1
    lines_changed: int = 0
    num_hidden_issues: int = 1
    issue_types: List[str] = Field(default_factory=list)
    cross_file_deps: bool = False


# ─── Internal models (not exposed to agent) ──────────────────────────────────

class GoldAnnotation(BaseModel):
    """Expert annotation for a single issue in a diff scenario."""
    line_number: int = 0
    severity: str = "major"
    issue_type: str = "bug"
    description: str = ""
    explanation: str = ""
    reference: str = ""  # OWASP or other reference


class Comment(BaseModel):
    """A single review comment added by the agent during an episode."""
    comment_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    line_number: int = 0
    severity: str = "major"
    message: str = ""
    step: int = 0


class DiffScenario(BaseModel):
    """A complete diff scenario with metadata and gold annotations."""
    id: str = ""
    source: dict = Field(default_factory=dict)       # {"repo": "...", "note": "..."}
    difficulty: str = "easy"
    diff_text: str = ""
    commit_message: str = ""
    pr_description: str = ""
    file_path: str = ""
    file_context: str = ""
    language: str = "python"
    annotations: List[dict] = Field(default_factory=list)
    gold_annotations: List[dict] = Field(default_factory=list)  # new format alias

    def get_annotations(self) -> list:
        """Parse annotations into GoldAnnotation objects (handles both formats)."""
        raw = self.gold_annotations or self.annotations
        result = []
        for ann in raw:
            if isinstance(ann, dict):
                # Normalize new format (line → line_number, issue → description)
                normalized = {
                    "line_number": ann.get("line_number", ann.get("line", 0)),
                    "severity": ann.get("severity", "major"),
                    "issue_type": ann.get("type", ann.get("issue_type", "bug")),
                    "description": ann.get("description", ann.get("issue", "")),
                    "explanation": ann.get("explanation", ""),
                    "reference": ann.get("reference", ""),
                }
                result.append(GoldAnnotation(**normalized))
            elif isinstance(ann, GoldAnnotation):
                result.append(ann)
        return result
