from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

from backend.engine.models import Segment
from backend.analyzers.cache.visual_cache import VisualCache
from backend.analyzers.cache.audio_cache import AudioCache
from backend.analyzers.cache.speech_cache import SpeechCache


@dataclass
class CachedVisualAnalyzer:
    cache: VisualCache
    motion_thr: float = 0.08

    def extract(self, seg: Segment) -> Dict[str, Any]:
        return self.cache.query(seg.start, seg.end, motion_thr=self.motion_thr)


@dataclass
class CachedMusicAnalyzer:
    cache: AudioCache

    def extract(self, seg: Segment) -> Dict[str, Any]:
        return self.cache.query(seg.start, seg.end)


@dataclass
class CachedSpeechAnalyzer:
    cache: SpeechCache

    def extract(self, seg: Segment) -> Dict[str, Any]:
        return self.cache.query(seg.start, seg.end)
