"""Tagger protocol (EA-7.5): every proposed action gets `{task_type, confidence}`. Rules first, model second."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .models import ProposedAction


@dataclass
class TagResult:
    task_type: str | None
    confidence: float


class Tagger(Protocol):
    def tag(self, action: ProposedAction) -> TagResult: ...


class RuleTagger:
    """Ordered rules `(predicate, task_type)`; the first match wins with confidence 1.0. An optional fallback
    (e.g. a model classifier) handles the rest. No match and no fallback → unknown type, confidence 0."""

    def __init__(self, rules: list[tuple[Callable[[ProposedAction], bool], str]] | None = None,
                 fallback: Tagger | None = None):
        self.rules = rules or []
        self.fallback = fallback

    def tag(self, action: ProposedAction) -> TagResult:
        for predicate, task_type in self.rules:
            if predicate(action):
                return TagResult(task_type, 1.0)
        if self.fallback is not None:
            return self.fallback.tag(action)
        return TagResult(None, 0.0)
