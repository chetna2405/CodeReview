"""
Difficulty validator for CodeReviewEnv.

Validates that a task's structural axes are consistent with its difficulty label.
Easy/medium/hard labels must comply with defined thresholds on num_files,
lines_changed, num_hidden_issues, and cross_file_deps.
"""

from __future__ import annotations
from typing import List


# ─── Thresholds per difficulty level ─────────────────────────────────────────

DIFFICULTY_RULES: dict[str, dict] = {
    "easy": {
        "max_files": 1,
        "max_lines": 49,
        "max_issues": 2,
        "allow_cross_file": False,
    },
    "medium": {
        "max_files": 3,
        "max_lines": 200,
        "max_issues": 4,
        "allow_cross_file": True,
    },
    "hard": {
        # Hard has no upper bounds — any complexity is valid
        "max_files": float("inf"),
        "max_lines": float("inf"),
        "max_issues": float("inf"),
        "allow_cross_file": True,
    },
}

MIN_ISSUES = {
    "easy": 1,
    "medium": 2,
    "hard": 4,
}


def validate_task_difficulty(
    difficulty: str,
    num_files: int = 1,
    lines_changed: int = 0,
    num_hidden_issues: int = 1,
    cross_file_deps: bool = False,
    issue_types: list | None = None,
) -> List[str]:
    """
    Validate that a task's structural parameters are consistent with its difficulty label.

    Args:
        difficulty: One of "easy", "medium", "hard".
        num_files: Number of files included in the diff.
        lines_changed: Total lines changed in the diff.
        num_hidden_issues: Number of hidden gold-annotated issues.
        cross_file_deps: Whether the bugs span multiple files.
        issue_types: List of issue type strings.

    Returns:
        A list of warning strings. Empty list means consistent.
    """
    warnings: List[str] = []
    rules = DIFFICULTY_RULES.get(difficulty)
    if rules is None:
        warnings.append(f"Unknown difficulty '{difficulty}'. Must be easy/medium/hard.")
        return warnings

    if num_files > rules["max_files"]:
        warnings.append(
            f"num_files={num_files} exceeds max for '{difficulty}' "
            f"(max {rules['max_files']}). Consider upgrading to a harder tier."
        )

    if lines_changed > rules["max_lines"]:
        warnings.append(
            f"lines_changed={lines_changed} exceeds max for '{difficulty}' "
            f"(max {rules['max_lines']}). Consider upgrading to a harder tier."
        )

    if num_hidden_issues > rules["max_issues"]:
        warnings.append(
            f"num_hidden_issues={num_hidden_issues} exceeds max for '{difficulty}' "
            f"(max {rules['max_issues']}). Consider upgrading to a harder tier."
        )

    min_issues = MIN_ISSUES.get(difficulty, 1)
    if num_hidden_issues < min_issues:
        warnings.append(
            f"num_hidden_issues={num_hidden_issues} is below minimum for '{difficulty}' "
            f"(min {min_issues}). Task may be too trivial."
        )

    if cross_file_deps and not rules["allow_cross_file"]:
        warnings.append(
            f"cross_file_deps=True is not expected for '{difficulty}' tasks. "
            "Consider upgrading to medium or hard."
        )

    return warnings


def validate_scenario(scenario: dict) -> List[str]:
    """
    Validate a scenario dict against difficulty consistency rules.

    Args:
        scenario: A scenario dict loaded from JSON.

    Returns:
        List of warning strings. Empty list means valid.
    """
    difficulty = scenario.get("difficulty", "easy")
    diff_text = scenario.get("diff_text", "")
    num_files = _count_files_in_diff(diff_text)
    lines_changed = _count_lines_changed(diff_text)
    annotations = scenario.get("gold_annotations", scenario.get("annotations", []))
    num_issues = len(annotations)
    issue_types = [a.get("type", a.get("issue_type", "bug")) for a in annotations]
    cross_file = num_files > 1

    return validate_task_difficulty(
        difficulty=difficulty,
        num_files=num_files,
        lines_changed=lines_changed,
        num_hidden_issues=num_issues,
        cross_file_deps=cross_file,
        issue_types=issue_types,
    )


def _count_files_in_diff(diff_text: str) -> int:
    """Count the number of distinct files in a unified diff."""
    count = sum(1 for line in diff_text.splitlines() if line.startswith("+++ "))
    return max(count, 1)


def _count_lines_changed(diff_text: str) -> int:
    """Count added + removed lines in a unified diff."""
    return sum(
        1
        for line in diff_text.splitlines()
        if line.startswith("+") or line.startswith("-")
        if not line.startswith("+++") and not line.startswith("---")
    )
