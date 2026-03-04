from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class GuitarFocusResult:
    is_guitar_focused: bool
    confidence: float
    reasons: Dict[str, Any]
    fretboard_roi: Optional[Tuple[float, float, float, float]] = None


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def detect_guitar_focus(
    *,
    music_feat: Dict[str, Any],
    visual_feat: Dict[str, Any],
    speech_feat: Dict[str, Any],
    cfg: Dict[str, Any],
) -> GuitarFocusResult:
    """Conservative V1 guitar-focus detector (audio-first + optional visual hints)."""

    tab_cfg = (cfg.get("tab") or {})
    det = (tab_cfg.get("guitar_focus") or {})

    thr_conf = float(det.get("min_confidence", 0.25))
    min_music = float(det.get("min_music_activity", 0.55))
    max_speech = float(det.get("max_speech_ratio", 1.0))

    music_activity = float(music_feat.get("music_activity", 0.0) or 0.0)
    speech_ratio = float(speech_feat.get("speech_ratio", 0.0) or 0.0)

    fret_vis = float(visual_feat.get("fretboard_visible_ratio", 0.0) or 0.0)
    hand_near_neck = float(visual_feat.get("hand_near_fretboard_ratio", 0.0) or 0.0)
    motion_mean = float(visual_feat.get("motion_mean", 0.0) or 0.0)

    audio_score = _clip((music_activity - 0.35) / 0.65)
    speech_gate = _clip(1.0 - (speech_ratio / max(1e-6, max_speech)))

    visual_bonus = 0.0
    if fret_vis > 0.0:
        visual_bonus += 0.35 * _clip(fret_vis / 0.6)
    if hand_near_neck > 0.0:
        visual_bonus += 0.25 * _clip(hand_near_neck / 0.6)
    visual_bonus += 0.10 * _clip(motion_mean / 0.25)

    confidence = _clip(0.70 * audio_score + 0.30 * speech_gate + visual_bonus)

    if music_activity < min_music:
        confidence *= 0.6
    if speech_ratio > max_speech:
        confidence *= 0.6

    roi = None
    if isinstance(visual_feat.get("fretboard_roi"), (list, tuple)) and len(visual_feat["fretboard_roi"]) == 4:
        try:
            roi = tuple(float(x) for x in visual_feat["fretboard_roi"])  # type: ignore
        except Exception:
            roi = None

    is_focus = bool(confidence >= thr_conf and music_activity >= min_music and speech_ratio <= max_speech)

    reasons = {
        "music_activity": music_activity,
        "speech_ratio": speech_ratio,
        "fretboard_visible_ratio": fret_vis,
        "hand_near_fretboard_ratio": hand_near_neck,
        "motion_mean": motion_mean,
        "thresholds": {
            "min_confidence": thr_conf,
            "min_music_activity": min_music,
            "max_speech_ratio": max_speech,
        },
    }

    return GuitarFocusResult(
        is_guitar_focused=is_focus,
        confidence=float(confidence),
        reasons=reasons,
        fretboard_roi=roi,
    )
