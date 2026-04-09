"""
CodeReviewEnv — An OpenEnv environment for AI code review benchmarking.

Agents review GitHub-style PR diffs, flag bugs, classify severity,
and produce review comments — graded against expert annotations.
"""

from models import ReviewAction, DiffObservation, ReviewState

__all__ = ["ReviewAction", "DiffObservation", "ReviewState"]
