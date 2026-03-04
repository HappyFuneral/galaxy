from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

@dataclass(frozen=True)
class Decision:
    label: str
    final_score: float
    explanation: Dict[str, Any]
    recommendations: Dict[str, Any]

@dataclass(frozen=True)
class EvalResult:
    decision: str
    final_score: float
    scores: Dict[str, float]
    explanation: Dict[str, Any]
    recommendations: Dict[str, Any]

class DecisionEngine:
    """
    V1.6-compatible DecisionEngine that supports BOTH:
      - legacy init: DecisionEngine(thresholds_cfg)
        with thresholds_cfg['decision_thresholds'] = {top, good, borderline}
        and calling .decide(...)
      - new init: DecisionEngine(thresholds_cfg, scorers=..., platform_evaluator=..., final_weights=..., thresholds=...)
        and calling .evaluate(...)
    """

    def __init__(
        self,
        thresholds_cfg: Dict[str, Any],
        scorers: Optional[List[Any]] = None,
        platform_evaluator: Optional[Any] = None,
        final_weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ):
        self.cfg = thresholds_cfg or {}

        # --- thresholds ---
        th: Dict[str, Any] = {}
        if isinstance(thresholds, dict):
            th = thresholds
        elif isinstance(self.cfg.get("decision_thresholds"), dict):
            th = self.cfg["decision_thresholds"]
        elif isinstance(self.cfg.get("decision"), dict):
            th = self.cfg["decision"]
        elif isinstance(self.cfg, dict):
            th = self.cfg

        # Normalize to internal keys: top/good/borderline
        self.th = {
            "top": float(th.get("top", th.get("accept", 0.70))),
            "good": float(th.get("good", 0.66)),
            "borderline": float(th.get("borderline", 0.62)),
        }

        # --- scoring ---
        self.scorers = list(scorers or [])
        self.platform_evaluator = platform_evaluator
        self.final_weights = dict(final_weights or {"music": 0.25, "visual": 0.25, "emotion": 0.25, "platform": 0.25})

    def _label(self, final_score: float) -> str:
        if final_score >= float(self.th["top"]):
            return "top_clip"
        if final_score >= float(self.th["good"]):
            return "good_clip"
        if final_score >= float(self.th["borderline"]):
            return "borderline"
        return "reject"

    def _explain(self, scores: Dict[str, float]) -> Dict[str, Any]:
        strong = [k for k, v in scores.items() if k in {"music","visual","emotion","platform"} and float(v) >= 0.75]
        weak = [k for k, v in scores.items() if k in {"music","visual","emotion","platform"} and float(v) <= 0.50]
        return {"strong_points": strong, "weak_points": weak}

    # ---- LEGACY API (kept) ----
    def decide(self, final_score: float, scores: Dict[str, float], platform_recommendations: Dict[str, Any]) -> Decision:
        final_score = _clip(float(final_score))
        label = self._label(final_score)
        explanation = self._explain(scores)
        rec = dict(platform_recommendations or {})
        if label == "reject" and not rec.get("general"):
            rec["general"] = "Nincs elég erős rész a célplatformhoz (V1)."
        return Decision(label=label, final_score=final_score, explanation=explanation, recommendations=rec)

    # ---- V1.6 API ----
    def evaluate(
        self,
        *,
        segment: Any,
        platform: str,
        visual: Dict[str, Any],
        music: Dict[str, Any],
        speech: Dict[str, Any],
    ) -> EvalResult:
        scores: Dict[str, float] = {}
        for s in self.scorers:
            name = getattr(s, "name", None) or s.__class__.__name__.lower()
            v = float(s.score(segment=segment, platform=platform, visual=visual, music=music, speech=speech))
            scores[name] = _clip(v)

        if "platform" not in scores and self.platform_evaluator is not None:
            try:
                scores["platform"] = _clip(float(self.platform_evaluator.score(segment=segment, platform=platform)))
            except Exception:
                scores["platform"] = 0.0

        wsum = 0.0
        acc = 0.0
        for k, w in (self.final_weights or {}).items():
            if k in scores:
                ww = float(w)
                wsum += ww
                acc += ww * float(scores[k])
        final_score = _clip(acc / wsum) if wsum > 1e-9 else _clip(sum(scores.values()) / max(1, len(scores)))

        platform_rec: Dict[str, Any] = {}
        if self.platform_evaluator is not None and hasattr(self.platform_evaluator, "recommend"):
            try:
                platform_rec = dict(self.platform_evaluator.recommend(scores=scores, platform=platform) or {})
            except Exception:
                platform_rec = {}

        dec = self.decide(final_score, scores, platform_rec)
        return EvalResult(
            decision=dec.label,
            final_score=dec.final_score,
            scores=scores,
            explanation=dec.explanation,
            recommendations=dec.recommendations,
        )
