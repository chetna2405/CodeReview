"""
Grader module for CodeReviewEnv.

Evaluates agent performance using a multi-signal composite score:
  - Issue Detection F1 (50%): precision + recall of flagged issues vs gold annotations
  - Severity Accuracy (25%): correct severity classification for detected issues
  - Comment Quality (25%): semantic similarity of agent comments vs gold descriptions

All components are deterministic (fixed embeddings, fixed scoring logic).
"""

import math
from dataclasses import dataclass, field


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


# Weights for composite score
W_F1 = 0.50
W_SEVERITY = 0.25
W_COMMENT = 0.25

# Line number tolerance for matching agent comments to gold annotations
LINE_TOLERANCE = 3


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

    def ngrams(text, n):
        text = text.lower().strip()
        return set(text[i:i+n] for i in range(len(text) - n + 1))

    ng_a = ngrams(text_a, n)
    ng_b = ngrams(text_b, n)

    if not ng_a or not ng_b:
        return 0.0

    intersection = ng_a & ng_b
    return 2 * len(intersection) / (len(ng_a) + len(ng_b))


def _compute_comment_similarity(agent_message: str, gold_description: str) -> float:
    """
    Compute similarity between agent's comment and gold annotation.
    Uses a blend of word overlap and n-gram similarity for robustness.
    """
    word_sim = _compute_word_overlap(agent_message, gold_description)
    ngram_sim = _compute_ngram_similarity(agent_message, gold_description)
    # Weighted blend: n-gram is more robust to paraphrasing
    return 0.4 * word_sim + 0.6 * ngram_sim


def _match_comments_to_annotations(agent_comments: list, gold_annotations: list) -> list:
    """
    Match agent comments to gold annotations using line number proximity.

    Returns a list of (agent_comment_idx, gold_annotation_idx, line_distance) tuples.
    Each gold annotation is matched to at most one agent comment (greedy closest match).
    """
    if not agent_comments or not gold_annotations:
        return []

    # Build all valid (comment, annotation) pairs within tolerance
    candidates = []
    for ci, comment in enumerate(agent_comments):
        comment_line = comment.get("line_number", -1)
        if comment_line is None or comment_line < 0:
            continue
        for ai, annotation in enumerate(gold_annotations):
            ann_line = annotation.get("line_number", -1)
            if ann_line is None or ann_line < 0:
                continue
            distance = abs(comment_line - ann_line)
            if distance <= LINE_TOLERANCE:
                candidates.append((ci, ai, distance))

    # Greedy matching: sort by distance, then match without replacement
    candidates.sort(key=lambda x: x[2])
    matched_comments = set()
    matched_annotations = set()
    matches = []

    for ci, ai, dist in candidates:
        if ci not in matched_comments and ai not in matched_annotations:
            matches.append((ci, ai, dist))
            matched_comments.add(ci)
            matched_annotations.add(ai)

    return matches


def grade_episode(
    agent_comments: list[dict],
    gold_annotations: list[dict],
    final_verdict: str = "approve",
) -> GraderResult:
    """
    Grade a completed code review episode.

    Args:
        agent_comments: List of dicts with keys: line_number, severity, message
        gold_annotations: List of dicts with keys: line_number, severity, description
        final_verdict: Agent's final action type ("approve" or "request_changes")

    Returns:
        GraderResult with composite score and component breakdown.
    """
    result = GraderResult()
    result.issues_total = len(gold_annotations)

    if not gold_annotations:
        # No issues to find — agent should approve
        if final_verdict == "approve":
            result.composite_score = 1.0
            result.f1_score = 1.0
            result.severity_accuracy = 1.0
            result.comment_similarity = 1.0
        else:
            result.composite_score = 0.5  # Unnecessary request_changes
        return result

    if not agent_comments:
        # Agent found nothing — score is 0
        result.composite_score = 0.0
        return result

    # 1. Match agent comments to gold annotations
    matches = _match_comments_to_annotations(agent_comments, gold_annotations)
    true_positives = len(matches)
    false_positives = len(agent_comments) - true_positives
    false_negatives = len(gold_annotations) - true_positives

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

    # 3. Severity Accuracy (among matched issues)
    if true_positives > 0:
        severity_correct = 0
        for ci, ai, _ in matches:
            agent_sev = agent_comments[ci].get("severity", "").lower()
            gold_sev = gold_annotations[ai].get("severity", "").lower()
            if agent_sev == gold_sev:
                severity_correct += 1
        result.severity_accuracy = severity_correct / true_positives
    else:
        result.severity_accuracy = 0.0

    # 4. Comment Quality (semantic similarity for matched issues)
    if true_positives > 0:
        similarities = []
        for ci, ai, _ in matches:
            agent_msg = agent_comments[ci].get("message", "")
            gold_desc = gold_annotations[ai].get("description", "")
            sim = _compute_comment_similarity(agent_msg, gold_desc)
            similarities.append(sim)
        result.comment_similarity = sum(similarities) / len(similarities)
    else:
        result.comment_similarity = 0.0

    # 5. Composite Score
    result.composite_score = (
        W_F1 * result.f1_score
        + W_SEVERITY * result.severity_accuracy
        + W_COMMENT * result.comment_similarity
    )

    # Clamp to [0.0, 1.0]
    result.composite_score = max(0.0, min(1.0, result.composite_score))

    result.details = {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "matches": [(ci, ai) for ci, ai, _ in matches],
    }

    return result


def compute_partial_reward(
    agent_comments: list[dict],
    gold_annotations: list[dict],
) -> float:
    """
    Compute partial reward signal after each add_comment action.
    Used during the episode (not final grading).

    Returns a value in [0.0, 1.0] representing progress toward full score.
    """
    if not gold_annotations:
        return 0.0

    matches = _match_comments_to_annotations(agent_comments, gold_annotations)
    # Partial reward = fraction of issues found (recall-like)
    recall = len(matches) / len(gold_annotations)
    return recall
