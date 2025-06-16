from __future__ import annotations

import re
from typing import Iterable, List


def _sentence_split(text: str) -> List[str]:
    return re.split(r"(?<=[.!?]) +", text)


def chunk_text(
    text: str,
    max_tokens: int = 200,
    overlap: int = 40,
) -> list[str]:
    sentences = _sentence_split(text)
    window: list[str] = []
    tokens = 0
    results = []
    for sent in sentences:
        sent_tokens = len(sent.split())
        if tokens + sent_tokens > max_tokens:
            results.append(" ".join(window))
            while tokens > overlap and window:
                tokens -= len(window[0].split())
                window.pop(0)
        window.append(sent)
        tokens += sent_tokens
    if window:
        results.append(" ".join(window))

    return results
