
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class Segment:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

@dataclass(frozen=True)
class EvaluationResult:
    decision: str
    final_score: float
    scores: Dict[str, float]
    explanation: Dict[str, Any]
    recommendations: Dict[str, Any]
