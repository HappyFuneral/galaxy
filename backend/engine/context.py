from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from backend.analyzers.cache.visual_cache import VisualCache
from backend.analyzers.cache.audio_cache import AudioCache
from backend.analyzers.cache.speech_cache import SpeechCache
from backend.analyzers.cached_analyzers import CachedVisualAnalyzer, CachedMusicAnalyzer, CachedSpeechAnalyzer


@dataclass
class VideoContext:
    visual: CachedVisualAnalyzer
    music: CachedMusicAnalyzer
    speech: CachedSpeechAnalyzer


def build_ctx_for_video(video_path: str, cfg: Dict[str, Any]) -> VideoContext:
    p = Path(video_path)
    perf = (cfg.get("performance", {}) or {})
    visual_fps = float(perf.get("visual_sample_fps", 0.5))
    visual_w = int(perf.get("visual_max_width", 256))
    audio_hop = float(perf.get("audio_hop_s", 0.25))

    # Build caches ONCE (major speed-up)
    visual_cache = VisualCache(video_path=p, sample_fps=visual_fps, max_width=visual_w).build()
    audio_cache = AudioCache(video_path=p, hop_s=audio_hop).build()
    speech_cache = SpeechCache(video_path=p, hop_s=audio_hop).build()

    motion_thr = float((cfg.get("postprocess", {}) or {}).get("highlight", {}).get("motion_thr", 0.08))

    return VideoContext(
        visual=CachedVisualAnalyzer(cache=visual_cache, motion_thr=motion_thr),
        music=CachedMusicAnalyzer(cache=audio_cache),
        speech=CachedSpeechAnalyzer(cache=speech_cache),
    )
