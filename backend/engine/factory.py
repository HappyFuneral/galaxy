from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

def _get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

@dataclass
class _FallbackScorer:
    name: str
    feature_key: str
    def score(self, *, segment, platform: str, visual: Dict[str, Any], music: Dict[str, Any], speech: Dict[str, Any]) -> float:
        bag = {"visual": visual, "music": music, "speech": speech}.get(self.name, {})
        try:
            v = float(bag.get(self.feature_key, 0.0))
        except Exception:
            v = 0.0
        return max(0.0, min(1.0, v))

class _FallbackPlatformEvaluator:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or {}
    def score(self, *, segment, platform: str) -> float:
        target = float(_get(self.cfg, f"{platform}.target_seconds", 45.0))
        tol = float(_get(self.cfg, f"{platform}.tolerance_seconds", 10.0))
        dur = float(getattr(segment, "duration", max(0.0, segment.end - segment.start)))
        diff = abs(dur - target)
        s = 1.0 - (diff / max(1e-6, tol))
        return max(0.0, min(1.0, s))

def build_decision_engine(cfg: Dict[str, Any]):
    from backend.engine.decision_engine import DecisionEngine

    scoring_cfg = cfg.get("scoring", {}) or {}
    thresholds_cfg = cfg.get("thresholds", {}) or {}

    final_weights = scoring_cfg.get(
        "final_weights",
        {"music": 0.25, "visual": 0.25, "emotion": 0.25, "platform": 0.25},
    )

    platform_eval_cfg = (cfg.get("platforms") or cfg.get("platform") or {}) or {}
    try:
        from backend.engine.platform_evaluator import PlatformEvaluator
        platform_evaluator = PlatformEvaluator(platform_eval_cfg)
    except Exception:
        platform_evaluator = _FallbackPlatformEvaluator(platform_eval_cfg)

    scorers: List[Any] = []
    try:
        from backend.engine.scorers.music import MusicScorer
        scorers.append(MusicScorer(scoring_cfg.get("music", {}) or {}))
    except Exception:
        scorers.append(_FallbackScorer(name="music", feature_key="music_activity"))

    try:
        from backend.engine.scorers.visual import VisualScorer
        scorers.append(VisualScorer(scoring_cfg.get("visual", {}) or {}))
    except Exception:
        scorers.append(_FallbackScorer(name="visual", feature_key="motion_mean"))

    try:
        from backend.engine.scorers.emotion import EmotionScorer
        scorers.append(EmotionScorer(scoring_cfg.get("emotion", {}) or {}))
    except Exception:
        scorers.append(_FallbackScorer(name="speech", feature_key="speech_ratio"))

    try:
        from backend.engine.scorers.platform import PlatformScorer
        scorers.append(PlatformScorer(platform_evaluator, scoring_cfg.get("platform", {}) or {}))
    except Exception:
        class _PlatformScorer:
            name = "platform"
            def __init__(self, pe): self.pe = pe
            def score(self, *, segment, platform: str, visual, music, speech) -> float:
                return float(self.pe.score(segment=segment, platform=platform))
        scorers.append(_PlatformScorer(platform_evaluator))

    # NOTE: thresholds_cfg passed positionally to match your legacy __init__(thresholds_cfg)
    return DecisionEngine(
        thresholds_cfg,
        scorers=scorers,
        platform_evaluator=platform_evaluator,
        final_weights=final_weights,
        thresholds=(thresholds_cfg.get("decision_thresholds") or thresholds_cfg.get("decision") or thresholds_cfg),
    )
