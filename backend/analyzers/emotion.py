
from __future__ import annotations
from typing import Any, Dict, List
from backend.engine.models import Segment

def _mean(xs: List[float]) -> float:
    return sum(xs)/len(xs) if xs else 0.0

def _variance(xs: List[float]) -> float:
    m = _mean(xs)
    return _mean([(x-m)**2 for x in xs]) if xs else 0.0

def _slope(xs: List[float]) -> float:
    return (xs[-1] - xs[0]) if len(xs) >= 2 else 0.0

class EmotionEstimatorV1:
    def __init__(self, cfg: Dict[str, Any] | None = None):
        self.cfg = cfg or {}

    def extract_from_ctx(self, segment: Segment, music_feats: Dict[str, Any], visual_feats: Dict[str, Any]) -> Dict[str, Any]:
        energy_curve = list(music_feats.get("energy_curve", []))
        build_up = max(_slope(energy_curve), 0.0)
        climax_strength = (max(energy_curve) - _mean(energy_curve)) if energy_curve else 0.0
        expressive_motion = float(visual_feats.get("motion_intensity", 0.0)) * float(music_feats.get("energy_change", 0.0))
        temporal_contrast = _variance(energy_curve)
        return {"build_up":float(build_up),"climax_strength":float(climax_strength),"expressive_motion":float(expressive_motion),"temporal_contrast":float(temporal_contrast)}
