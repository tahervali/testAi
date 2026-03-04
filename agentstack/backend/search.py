"""Fuzzy search scoring for solutions."""

import re
from models import Solution


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _match_score(query_tokens: list[str], text: str) -> float:
    """Score how well query tokens match against a text field.
    Uses partial/stem matching: term startswith word OR word startswith term.
    """
    words = _tokenize(text)
    if not words or not query_tokens:
        return 0.0
    score = 0.0
    for qt in query_tokens:
        for w in words:
            if qt.startswith(w) or w.startswith(qt):
                # Exact match scores higher
                if qt == w:
                    score += 2.0
                else:
                    score += 1.0
                break
    return score


def score_solution(solution: Solution, query: str) -> float:
    """Score a solution against a search query.

    Searches across: task_description, tags, solution code, language, agent_name.
    Weights: task_description (3x), tags (2x), code (1x), language (1.5x), agent (0.5x).
    Final score multiplied by success_rate.
    """
    tokens = _tokenize(query)
    if not tokens:
        return 0.0

    s = 0.0
    s += _match_score(tokens, solution.task_description or "") * 3.0
    s += _match_score(tokens, " ".join(solution.tags or [])) * 2.0
    s += _match_score(tokens, solution.solution or "") * 1.0
    s += _match_score(tokens, solution.language or "") * 1.5
    s += _match_score(tokens, solution.agent_name or "") * 0.5

    # Multiply by success_rate to surface high-quality solutions
    return s * max(solution.success_rate, 0.1)


def search_solutions(solutions: list[Solution], query: str, limit: int = 5) -> list[tuple[Solution, float]]:
    """Return top solutions sorted by relevance score."""
    scored = [(sol, score_solution(sol, query)) for sol in solutions]
    scored = [(sol, sc) for sol, sc in scored if sc > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
