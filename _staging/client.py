"""
CodeReviewEnv Client — Typed client for remote interaction.

Usage:
    from client import CodeReviewEnv
    from models import ReviewAction

    with CodeReviewEnv(base_url="http://localhost:8000").sync() as client:
        result = client.reset(task_id="simple_review")
        print(result.observation.diff_text)

        result = client.step(ReviewAction(
            action_type="add_comment",
            line_number=15,
            severity="critical",
            message="Off-by-one error"
        ))
        print(result.reward)
"""

from openenv.core import EnvClient, StepResult
from models import ReviewAction, DiffObservation, ReviewState


class CodeReviewEnv(EnvClient[ReviewAction, DiffObservation, ReviewState]):
    """Typed client for CodeReviewEnv remote environment."""

    def _step_payload(self, action: ReviewAction) -> dict:
        """Serialize action to dict for HTTP transport."""
        payload = {"action_type": action.action_type}
        if action.line_number is not None:
            payload["line_number"] = action.line_number
        if action.severity is not None:
            payload["severity"] = action.severity
        if action.message is not None:
            payload["message"] = action.message
        if action.reason is not None:
            payload["reason"] = action.reason
        return payload

    def _parse_result(self, payload: dict) -> StepResult[DiffObservation]:
        """Parse HTTP response into StepResult with typed observation."""
        obs = DiffObservation(
            diff_text=payload.get("diff_text", ""),
            commit_message=payload.get("commit_message", ""),
            pr_description=payload.get("pr_description", ""),
            file_path=payload.get("file_path", ""),
            file_context=payload.get("file_context", ""),
            task_id=payload.get("task_id", ""),
            step_num=payload.get("step_num", 0),
            max_steps=payload.get("max_steps", 10),
            existing_comments=payload.get("existing_comments", []),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=payload.get("metadata", {}),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> ReviewState:
        """Parse HTTP response into typed ReviewState."""
        return ReviewState(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id", ""),
            scenario_id=payload.get("scenario_id", ""),
            comments_made=payload.get("comments_made", 0),
            issues_found=payload.get("issues_found", 0),
            max_steps=payload.get("max_steps", 10),
            is_done=payload.get("is_done", False),
            final_score=payload.get("final_score"),
        )
