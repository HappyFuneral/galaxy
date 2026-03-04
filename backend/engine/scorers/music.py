from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

@dataclass
class MusicScorer:
    """Scores musical interest for a segment.

    Input features expected from vctx.music.extract(seg):
      - music_activity: 0..1 (mean)
      - music_peak: 0..1 (max)
    """
    cfg: Dict[str, Any]

    name: str = "music"

    def score(self, *, segment, platform: str, visual: Dict[str, Any], music: Dict[str, Any], speech: Dict[str, Any]) -> float:
        act = float(music.get("music_activity", 0.0))
        peak = float(music.get("music_peak", act))

        w_peak = float((self.cfg.get("weights") or {}).get("peak", 0.55))
        w_act = float((self.cfg.get("weights") or {}).get("activity", 0.45))

        raw = w_act * act + w_peak * peak

        # Soft gate: very low activity => downweight
        floor_thr = float(self.cfg.get("floor_activity", 0.08))
        if act < floor_thr:
            raw *= float(self.cfg.get("low_activity_penalty", 0.6))

        return _clamp01(raw)
