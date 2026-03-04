from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

@dataclass
class PlatformScorer:
    """Wraps PlatformEvaluator into a scorer."""
    platform_evaluator: Any
    cfg: Dict[str, Any]
    name: str = "platform"

    def score(self, *, segment, platform: str, visual: Dict[str, Any], music: Dict[str, Any], speech: Dict[str, Any]) -> float:
        s = float(self.platform_evaluator.score(segment=segment, platform=platform))
        # optional shaping
        gamma = float(self.cfg.get("gamma", 1.0))
        if gamma != 1.0 and s > 0:
            s = s ** gamma
        return _clamp01(s)
