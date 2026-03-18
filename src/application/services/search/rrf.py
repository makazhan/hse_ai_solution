"""Reciprocal Rank Fusion — объединение нескольких ранжированных списков."""
from collections import defaultdict
from typing import Callable


def apply_rrf(
    *result_lists: list[dict],
    key_fn: Callable = lambda item: item['id'],
    k: int = 60,
    limit: int = 10,
) -> list[dict]:
    """Reciprocal Rank Fusion across N ranked lists."""
    scores: dict[str, float] = defaultdict(float)
    results_map: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, item in enumerate(result_list):
            doc_key = key_fn(item)
            scores[doc_key] += 1.0 / (k + rank + 1)
            if doc_key not in results_map:
                results_map[doc_key] = item

    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    final = []
    for doc_key in sorted_keys[:limit]:
        item = {**results_map[doc_key], 'score': scores[doc_key]}
        final.append(item)
    return final
