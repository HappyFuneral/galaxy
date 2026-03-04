
from __future__ import annotations
from typing import Any, Dict, List
from backend.engine.models import Segment

def _clip(x: float, lo: float=0.0, hi: float=1.0) -> float:
    return max(lo, min(hi, x))

def _mean(xs: List[float]) -> float:
    return sum(xs)/len(xs) if xs else 0.0

class PlatformEvaluator:
    def __init__(self, profiles: Dict[str, Any]):
        self.profiles = profiles

    def evaluate(self, segment: Segment, raw: Dict[str, Any], scores_wo_platform: Dict[str, float], platform: str) -> Dict[str, Any]:
        profile = self.profiles[platform]
        energy_curve = list(raw["music"].get("energy_curve", []))

        hook_window_s = int(profile["hook_window_s"])
        hook_len = min(len(energy_curve), max(1, hook_window_s))
        hook_score = _clip((_mean(energy_curve[:hook_len]) / (_mean(energy_curve) + 1e-6)), 0.0, 2.0) / 2.0

        start_e = energy_curve[0] if energy_curve else 0.0
        end_e = energy_curve[-1] if energy_curve else 0.0
        loop_score = _clip(1.0 - abs(start_e - end_e), 0.0, 1.0)

        silent_view = _clip(0.6 * float(scores_wo_platform.get("visual", 0.0)) + 0.4 * float(raw["visual"].get("motion_intensity", 0.0)), 0.0, 1.0)

        target = float(profile["duration_target"])
        duration_fit = _clip(1.0 - abs(segment.duration - target) / target, 0.0, 1.0)

        w = profile["weights"]
        platform_score = (
            float(w["hook"]) * hook_score +
            float(w["silent_view"]) * silent_view +
            float(w["loop"]) * loop_score +
            float(w["duration_fit"]) * duration_fit
        )
        platform_score = _clip(platform_score, 0.0, 1.0)

        rec: Dict[str, Any] = {}
        if hook_score < 0.4:
            rec["hook"] = "Kezdd ütősebben (belépés/riff az első pár másodpercben)."
        if float(raw["visual"].get("hands_visible_ratio", 0.0)) < 0.6:
            rec["framing"] = "A kéz/hangszer legyen jobban látható (közelebbi kamera / jobb szög)."
        if platform_score < 0.6:
            rec["general"] = "Ez a szakasz valószínűleg gyengébb short-form teljesítményt hoz."

        return {"platform_score": float(platform_score), "recommendations": rec}
