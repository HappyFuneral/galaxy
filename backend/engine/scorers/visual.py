from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

@dataclass
class VisualScorer:
    """Scores visual quality & engagement.

    Input features expected from vctx.visual.extract(seg):
      - motion_mean: 0..1
      - motion_max: 0..1
      - brightness_mean: 0..1
      - active_fraction: 0..1
    """
    cfg: Dict[str, Any]
    name: str = "visual"

    def score(self, *, segment, platform: str, visual: Dict[str, Any], music: Dict[str, Any], speech: Dict[str, Any]) -> float:
        motion = float(visual.get("motion_mean", 0.0))
        motion_max = float(visual.get("motion_max", motion))
        active_frac = float(visual.get("active_fraction", 0.0))
        bright = float(visual.get("brightness_mean", 0.5))

        w = self.cfg.get("weights") or {}
        w_motion = float(w.get("motion", 0.45))
        w_active = float(w.get("active_fraction", 0.25))
        w_peak = float(w.get("motion_peak", 0.15))
        w_bright = float(w.get("brightness", 0.15))

        # Brightness: prefer mid-range
        b_center = float(self.cfg.get("brightness_center", 0.55))
        b_tol = float(self.cfg.get("brightness_tolerance", 0.40))
        b_score = 1.0 - (abs(bright - b_center) / max(1e-6, b_tol))
        b_score = _clamp01(b_score)

        raw = w_motion * motion + w_active * active_frac + w_peak * motion_max + w_bright * b_score

        return _clamp01(raw)
