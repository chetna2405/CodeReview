"""
Grader module for CodeReviewEnv.

Evaluates agent performance using a multi-signal composite score:
  - Issue Detection F1 (50%): precision + recall of flagged issues vs gold annotations
  - Severity Accuracy (30%): ordinal severity penalty for detected issues
  - Comment Quality (20%): semantic similarity of agent comments vs gold descriptions

Weights: 0.5 * F1 + 0.3 * severity_acc + 0.2 * comment_quality

All components are deterministic (fixed scoring logic, no models required).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


# ─── Severity ────────────────────────────────────────────────────────────────

SEVERITY_LEVELS = ["nit", "minor", "major", "critical"]
"""Ordered severity levels from least (nit) to most (critical) severe."""

SEVERITY_MAP: dict[str, str] = {
    # Security issues → always critical
    "sql_injection": "critical",
    "rce": "critical",
    "command_injection": "critical",
    "auth_bypass": "critical",
    "authentication_bypass": "critical",
    "xss": "critical",
    "xxe": "critical",
    "deserialization": "critical",
    "path_traversal": "critical",
    "hardcoded_secret": "critical",
    "hardcoded_credentials": "critical",
    "insecure_direct_object_reference": "critical",
    # Logic bugs → major
    "off_by_one": "major",
    "logic_error": "major",
    "null_pointer": "major",
    "null_check": "major",
    "race_condition": "major",
    "memory_leak": "major",
    "resource_leak": "major",
    "integer_overflow": "major",
    "type_error": "major",
    "silent_failure": "major",
    "exception_swallowed": "major",
    # Style / minor issues
    "missing_docstring": "nit",
    "naming_convention": "nit",
    "unused_variable": "nit",
    "unused_import": "nit",
    "formatting": "nit",
    "typo": "minor",
    "missing_validation": "minor",
    "missing_error_handling": "minor",
    "deprecation": "minor",
    # Default catch-all
    "bug": "major",
    "security": "critical",
    "performance": "minor",
    "style": "nit",
}
"""Maps issue types to their expected severity level."""


def _ordinal_severity_score(agent_sev: str, gold_sev: str) -> float:
    """
    Score severity classification with ordinal distance penalty.

    Args:
        agent_sev: Agent's predicted severity label.
        gold_sev: Gold (expert) severity label.

    Returns:
        1.0 for exact match, 0.67 off-by-one, 0.33 off-by-two, 0.0 off-by-three.
    """
    try:
        agent_idx = SEVERITY_LEVELS.index(agent_sev.lower())
    except ValueError:
        agent_idx = SEVERITY_LEVELS.index("major")  # default unknown → major
    try:
        gold_idx = SEVERITY_LEVELS.index(gold_sev.lower())
    except ValueError:
        gold_idx = SEVERITY_LEVELS.index("major")

    diff = abs(agent_idx - gold_idx)
    penalties = {0: 1.0, 1: 0.67, 2: 0.33, 3: 0.0}
    return penalties.get(diff, 0.0)


# ─── Weights ─────────────────────────────────────────────────────────────────

W_F1 = 0.50
W_SEVERITY = 0.30
W_COMMENT = 0.20

# Line number tolerance for matching agent comments to gold annotations
LINE_TOLERANCE = 3


# ─── Similarity helpers ───────────────────────────────────────────────────────

def _compute_word_overlap(text_a: str, text_b: str) -> float:
    """
    Compute word-level Jaccard similarity between two texts.
    Fast, deterministic, no model required.
    """
    if not text_a or not text_b:
        return 0.0
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _compute_ngram_similarity(text_a: str, text_b: str, n: int = 2) -> float:
    """
    Compute character n-gram similarity (Dice coefficient).
    More robust than word overlap for partial matches.
    """
    if not text_a or not text_b:
        return 0.0

    def ngrams(text: str, n: int):
        text = text.lower().strip()
        return set(text[i : i + n] for i in range(len(text) - n + 1))

    ng_a = ngrams(text_a, n)
    ng_b = ngrams(text_b, n)
    if not ng_a or not ng_b:
        return 0.0
    intersection = ng_a & ng_b
    return 2 * len(intersection) / (len(ng_a) + len(ng_b))


def _compute_comment_similarity(agent_message: str, gold_description: str) -> float:
    """
    Compute similarity between agent's comment and gold annotation.
    Uses a blend of word overlap and n-gram similarity.
    """
    word_sim = _compute_word_overlap(agent_message, gold_description)
    ngram_sim = _compute_ngram_similarity(agent_message, gold_description)
    return 0.4 * word_sim + 0.6 * ngram_sim


# ─── Matching ─────────────────────────────────────────────────────────────────

def _match_comments_to_annotations(
    agent_comments: List[dict], gold_annotations: List[dict]
) -> List[Tuple[int, int, int]]:
    """
    Match agent comments to gold annotations using line number proximity.

    Returns a list of (agent_comment_idx, gold_annotation_idx, line_distance).
    Each gold annotation is matched to at most one agent comment (greedy closest).
    """
    if not agent_comments or not gold_annotations:
        return []

    candidates = []
    for ci, comment in enumerate(agent_comments):
        comment_line = comment.get("line_number", -1)
        if comment_line is None or comment_line < 0:
            continue
        for ai, annotation in enumerate(gold_annotations):
            ann_line = annotation.get("line_number", annotation.get("line", -1))
            if ann_line is None or ann_line < 0:
                continue
            distance = abs(comment_line - ann_line)
            if distance <= LINE_TOLERANCE:
                candidates.append((ci, ai, distance))

    candidates.sort(key=lambda x: x[2])
    matched_comments: set = set()
    matched_annotations: set = set()
    matches: List[Tuple[int, int, int]] = []

    for ci, ai, dist in candidates:
        if ci not in matched_comments and ai not in matched_annotations:
            matches.append((ci, ai, dist))
            matched_comments.add(ci)
            matched_annotations.add(ai)

    return matches


# ─── Result ───────────────────────────────────────────────────────────────────

@dataclass
class GraderResult:
    """Result from the grader after evaluating an episode."""
    composite_score: float = 0.0
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    severity_accuracy: float = 0.0
    comment_similarity: float = 0.0
    issues_found: int = 0
    issues_total: int = 0
    false_positives: int = 0
    details: dict = field(default_factory=dict)


# ─── Core grader ─────────────────────────────────────────────────────────────

def grade_episode(
    agent_comments: List[dict],
    gold_annotations: List[dict],
    final_verdict: str = "approve",
    scenario: dict = None,
) -> GraderResult:
    """
    Grade a completed code review episode.

    Formula: 0.5 * F1 + 0.3 * severity_acc + 0.2 * comment_quality

    Args:
        agent_comments: List of dicts with keys: line_number, severity, message.
        gold_annotations: List of dicts with keys: line_number, severity, description.
        final_verdict: Agent's final action type (approve/request_changes/finalize_review/timeout).
        scenario: The current scenario being evaluated.

    Returns:
        GraderResult with composite score and component breakdown.
    """
    result = GraderResult()
    is_cross_file = scenario is not None and scenario.get("cross_file", False)
    # Normalize gold annotation field names (support both old and new format)
    normalized_gold = []
    for ann in gold_annotations:
        normalized_gold.append({
            "line_number": ann.get("line_number", ann.get("line", 0)),
            "severity": ann.get("severity", "major"),
            "description": ann.get("description", ann.get("issue", "")),
            "type": ann.get("type", ann.get("issue_type", "bug")),
            "file": ann.get("file", ""),
            "causal_chain": ann.get("causal_chain", {}),
        })

    if is_cross_file:
        result.issues_total = 1
        causal_desc = ""
        files_involved = set()
        for ann in normalized_gold:
            if ann.get("file"): files_involved.add(ann["file"])
            if ann.get("causal_chain"):
                chain = ann["causal_chain"]
                if chain.get("description"): causal_desc = chain["description"]
                if chain.get("root_file"): files_involved.add(chain["root_file"])
                if chain.get("downstream_file"): files_involved.add(chain["downstream_file"])

        agent_flagged_files = set(c.get("file", "") for c in agent_comments if c.get("file"))
        
        flagged_count = len([f for f in files_involved if f in agent_flagged_files])
        best_overlap = 0.0
        for c in agent_comments:
            score = _compute_word_overlap(c.get("message", ""), causal_desc)
            if score > best_overlap:
                best_overlap = score

        is_causal_match = best_overlap >= 0.35

        if flagged_count >= 2 and is_causal_match:
            result.composite_score = 1.0
            result.issues_found = 1
        elif flagged_count >= 1:
            result.composite_score = 0.4
            result.issues_found = 0
        else:
            result.composite_score = 0.0
            result.issues_found = 0

        result.f1_score = result.composite_score
        result.severity_accuracy = result.composite_score
        result.comment_similarity = result.composite_score
        return result

    result.issues_total = len(normalized_gold)

    if not normalized_gold:
        # No issues to find — agent should approve
        if final_verdict in ("approve", "finalize_review"):
            result.composite_score = 1.0
            result.f1_score = 1.0
            result.severity_accuracy = 1.0
            result.comment_similarity = 1.0
        else:
            result.composite_score = 0.5  # Unnecessary request_changes
        return result

    if not agent_comments:
        result.composite_score = 0.0
        return result

    # 1. Match agent comments to gold annotations
    matches = _match_comments_to_annotations(agent_comments, normalized_gold)
    true_positives = len(matches)
    false_positives = len(agent_comments) - true_positives
    false_negatives = len(normalized_gold) - true_positives

    result.issues_found = true_positives
    result.false_positives = false_positives

    # 2. F1 Score
    if true_positives == 0:
        result.precision = 0.0
        result.recall = 0.0
        result.f1_score = 0.0
    else:
        result.precision = true_positives / (true_positives + false_positives)
        result.recall = true_positives / (true_positives + false_negatives)
        result.f1_score = (
            2 * result.precision * result.recall
            / (result.precision + result.recall)
        )

    # 3. Severity Accuracy — ordinal penalty (off-by-one = 0.67, etc.)
    if true_positives > 0:
        severity_scores = []
        for ci, ai, _ in matches:
            agent_sev = agent_comments[ci].get("severity", "major")
            gold_sev = normalized_gold[ai].get("severity", "major")
            severity_scores.append(_ordinal_severity_score(agent_sev, gold_sev))
        result.severity_accuracy = sum(severity_scores) / len(severity_scores)
    else:
        result.severity_accuracy = 0.0

    # 4. Comment Quality — semantic similarity for matched issues
    if true_positives > 0:
        similarities = []
        for ci, ai, _ in matches:
            agent_msg = agent_comments[ci].get("message", "")
            gold_desc = normalized_gold[ai].get("description", "")
            similarities.append(_compute_comment_similarity(agent_msg, gold_desc))
        result.comment_similarity = sum(similarities) / len(similarities)
    else:
        result.comment_similarity = 0.0

    # 5. Composite Score: 0.5*F1 + 0.3*severity_acc + 0.2*comment_quality
    result.composite_score = (
        W_F1 * result.f1_score
        + W_SEVERITY * result.severity_accuracy
        + W_COMMENT * result.comment_similarity
    )
    result.composite_score = max(0.0, min(1.0, result.composite_score))

    result.details = {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "matches": [(ci, ai) for ci, ai, _ in matches],
    }

    return result


def compute_partial_reward(
    agent_comments: List[dict],
    gold_annotations: List[dict],
) -> float:
    """
    Compute partial reward signal after each add_comment action.

    Returns a value in [0.0, 1.0] representing recall progress.
    Spamming every line loses precision and does NOT inflate this — it only
    reflects true positive recall fraction.
    """
    if not gold_annotations:
        return 0.0
    # Normalize gold
    normalized = [
        {"line_number": a.get("line_number", a.get("line", 0))}
        for a in gold_annotations
    ]
    matches = _match_comments_to_annotations(agent_comments, normalized)
    tp = len(matches)
    fp = len(agent_comments) - tp
    if tp == 0:
        return 0.0
    # Penalize false positives: precision-weighted recall
    precision = tp / (tp + fp)
    recall = tp / len(normalized)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
