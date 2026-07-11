"""
pss10.py
--------
Implementation of the Perceived Stress Scale - 10 item (PSS-10), developed by
Cohen, Kamarck, & Mermelstein (1983/1988). This is a self-report instrument
widely used to measure perceived stress over the last month.

SCORING (important):
- 10 items, each answered on a 0-4 scale:
        0 = Never
        1 = Almost Never
        2 = Sometimes
        3 = Often
        4 = Very Often

- Four items are positive-framed and must be reverse-scored before summing:
    items 4, 5, 7, 8 (0-based indexes 3, 4, 6, 7). Reverse formula: new = 4 - old

- Total score range: 0 - 40. Common categories:
        0–13   = Low
        14–26  = Moderate
        27–40  = High

Source: Cohen, S., Kamarck, T., & Mermelstein, R. (1983).
"A global measure of perceived stress." Journal of Health and Social Behavior.
"""

from typing import List, Dict

# 0-based indexes of items that must be reverse-scored
REVERSE_SCORED_INDEXES = [3, 4, 6, 7]  # = items 4, 5, 7, 8

PSS10_QUESTIONS = [
    "In the last month, how often have you been upset because of something that happened unexpectedly?",
    "In the last month, how often have you felt unable to control important things in your life?",
    "In the last month, how often have you felt nervous and stressed?",
    "In the last month, how often have you felt confident about your ability to handle personal problems?",
    "In the last month, how often have you felt that things were going your way?",
    "In the last month, how often have you felt that you could not cope with all the things you had to do?",
    "In the last month, how often have you been able to control irritations in your life?",
    "In the last month, how often have you felt that you were on top of things?",
    "In the last month, how often have you been angered because of things that were outside of your control?",
    "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?",
]

LIKERT_LABELS = [
    "Never",
    "Almost Never",
    "Sometimes",
    "Often",
    "Very Often",
]


def calculate_pss10(answers: List[int]) -> Dict:
    """
    Calculate a PSS-10 score from 10 answers (each 0-4).

    Args:
        answers: list of 10 integers, each between 0-4, matching the order of PSS10_QUESTIONS.

    Returns:
        dict with total_score, category, and per-item detail for transparency/debugging.
    """
    if len(answers) != 10:
        raise ValueError(f"PSS-10 requires exactly 10 answers, received: {len(answers)}")

    for i, ans in enumerate(answers):
        if not (0 <= ans <= 4):
            raise ValueError(f"Answer at index {i} must be between 0-4, received: {ans}")

    adjusted_scores = []
    for i, ans in enumerate(answers):
        if i in REVERSE_SCORED_INDEXES:
            adjusted_scores.append(4 - ans)
        else:
            adjusted_scores.append(ans)

    total_score = sum(adjusted_scores)
    category = categorize_pss_score(total_score)

    return {
        "total_score": total_score,
        "max_score": 40,
        "category": category,
        "raw_answers": answers,
        "adjusted_scores": adjusted_scores,
    }


def categorize_pss_score(score: int) -> str:
    """Categorize total PSS-10 score (0-40) into three levels."""
    if score <= 13:
        return "Low"
    elif score <= 26:
        return "Moderate"
    else:
        return "High"
