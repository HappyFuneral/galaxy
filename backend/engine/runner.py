from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from backend.engine.models import Segment
from backend.engine.decision_engine import DecisionEngine
from backend.engine.context import VideoContext


@dataclass
class SegmentEvalResult:
    decision: str
    final_score: float
    scores: Dict[str, float]
    explanation: Dict[str, Any]
    recommendations: Dict[str, Any]
    active_windows: Optional[List[Dict[str, Any]]] = None


class EngineRunner:
    def __init__(self, engine: DecisionEngine):
        self.engine = engine

    def evaluate_segment(self, seg: Segment, platform: str, vctx: VideoContext) -> SegmentEvalResult:
        visual = vctx.visual.extract(seg)
        music = vctx.music.extract(seg)
        speech = vctx.speech.extract(seg)

        res = self.engine.evaluate(
            segment=seg,
            platform=platform,
            visual=visual,
            music=music,
            speech=speech,
        )

        return SegmentEvalResult(
            decision=res.decision,
            final_score=float(res.final_score),
            scores=res.scores,
            explanation=res.explanation,
            recommendations=res.recommendations,
            active_windows=list(visual.get("active_windows", []) or []),
        )


def build_engine_runner(cfg: Dict[str, Any]) -> EngineRunner:
    from backend.engine.factory import build_decision_engine
    engine = build_decision_engine(cfg=cfg)
    return EngineRunner(engine=engine)
