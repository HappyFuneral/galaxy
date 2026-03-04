from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

@dataclass
class EmotionScorer:
    """Scores 'emotional / hook potential' using simple heuristics.

    This is a placeholder scorer designed to be swapped with ML later.

    Uses:
      - speech_ratio (0..1): how much speech is present (podcast/talk hooks)
      - music_activity (0..1): musical intensity proxy (guitar riffs/solos)
      - motion_peak (0..1): visual excitement proxy
    """
    cfg: Dict[str, Any]
    name: str = "emotion"

    def score(self, *, segment, platform: str, visual: Dict[str, Any], music: Dict[str, Any], speech: Dict[str, Any]) -> float:
        speech_ratio = float(speech.get("speech_ratio", 0.0))
        music_activity = float(music.get("music_activity", 0.0))
        motion_peak = float(visual.get("motion_max", visual.get("motion_mean", 0.0)))

        w = self.cfg.get("weights") or {}
        w_speech = float(w.get("speech_ratio", 0.45))
        w_music = float(w.get("music_activity", 0.40))
        w_motion = float(w.get("motion_peak", 0.15))

        raw = w_speech * speech_ratio + w_music * music_activity + w_motion * motion_peak

        # Optional penalty if both speech and music are very low
        if speech_ratio < float(self.cfg.get("min_speech_ratio", 0.05)) and music_activity < float(self.cfg.get("min_music_activity", 0.08)):
            raw *= float(self.cfg.get("low_energy_penalty", 0.75))

        return _clamp01(raw)
