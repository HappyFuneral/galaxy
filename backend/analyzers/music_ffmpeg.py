
from __future__ import annotations
from typing import Any, Dict
import subprocess
import numpy as np
from backend.engine.models import Segment

def _ffmpeg_pcm_segment(video_path: str, start: float, duration: float, sr: int = 22050) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error",
        "-ss", f"{start:.3f}",
        "-i", video_path,
        "-t", f"{duration:.3f}",
        "-ac", "1",
        "-ar", str(sr),
        "-f", "f32le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore").strip())
    return np.frombuffer(proc.stdout, dtype=np.float32)

def _rms_curve(audio: np.ndarray, frame: int = 2048, hop: int = 1024) -> np.ndarray:
    if len(audio) == 0:
        return np.array([0.0], dtype=np.float32)
    if len(audio) < frame:
        return np.array([float(np.sqrt(np.mean(audio * audio)))], dtype=np.float32)
    rms = []
    for i in range(0, len(audio) - frame, hop):
        x = audio[i:i+frame]
        rms.append(float(np.sqrt(np.mean(x * x))))
    return np.array(rms, dtype=np.float32) if rms else np.array([0.0], dtype=np.float32)

class FFMpegMusicAnalyzer:
    def __init__(self, video_path: str, sr: int = 22050):
        self.video_path = video_path
        self.sr = sr

    def extract(self, segment: Segment) -> Dict[str, Any]:
        audio = _ffmpeg_pcm_segment(self.video_path, segment.start, segment.duration, sr=self.sr)
        rms = _rms_curve(audio)

        mx = float(np.max(rms)) + 1e-8
        energy_curve = (rms / mx).clip(0, 1).tolist()

        energy_peak = float(np.percentile(rms, 95)) if len(rms) else 0.0

        k = max(1, len(rms)//5)
        energy_change = float(abs(float(np.mean(rms[:k])) - float(np.mean(rms[-k:])))) if len(rms) else 0.0

        dr = np.diff(rms) if len(rms) >= 2 else np.array([0.0], dtype=np.float32)
        thr = float(np.mean(np.abs(dr)) + 1.5*np.std(dr)) if len(dr) else 0.0
        onsets = int(np.sum(dr > thr)) if thr > 0 else 0
        onset_density = float(onsets / max(segment.duration, 1e-6))

        return {
            "energy_curve": energy_curve,
            "energy_peak": energy_peak,
            "energy_change": energy_change,
            "onset_density": onset_density,
            "harmonic_change": 0.2,
            "tempo": 120.0,
        }
