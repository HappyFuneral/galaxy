
from __future__ import annotations
from typing import Any, Dict

def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def _weighted_avg(values: Dict[str, float], weights: Dict[str, float]) -> float:
    total = 0.0
    wsum = 0.0
    for k, w in weights.items():
        if k not in values:
            continue
        total += float(w) * float(values[k])
        wsum += float(w)
    return _clip(total / wsum if wsum else 0.0)

class WeightedScoreCalculator:
    def __init__(self, scoring_cfg: Dict[str, Any]):
        self.final_weights = scoring_cfg["weights"]
        self.music_weights = scoring_cfg.get("music_weights", {})
        self.visual_weights = scoring_cfg.get("visual_weights", {})
        self.emotion_weights = scoring_cfg.get("emotion_weights", {})

    def _score_domain(self, norm_feats: Dict[str, Any], weights: Dict[str, float]) -> float:
        scalars = {k: float(v) for k, v in norm_feats.items() if isinstance(v, (int, float))}
        return _weighted_avg(scalars, weights)

    def score(self, normalized: Dict[str, Dict[str, Any]], platform: str) -> Dict[str, float]:
        music_s = self._score_domain(normalized.get("music", {}), self.music_weights)
        visual_s = self._score_domain(normalized.get("visual", {}), self.visual_weights)
        emotion_s = self._score_domain(normalized.get("emotion", {}), self.emotion_weights)

        platform_score = float(normalized.get("platform", {}).get("platform_score", 0.0))
        platform_score = _clip(platform_score)

        scores = {
            "music": _clip(music_s),
            "visual": _clip(visual_s),
            "emotion": _clip(emotion_s),
            "platform": _clip(platform_score),
        }

        final = 0.0
        for k, w in self.final_weights.items():
            final += float(w) * float(scores.get(k, 0.0))
        scores["final"] = _clip(final)
        return scores
