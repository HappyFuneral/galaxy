from __future__ import annotations
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .types import TimeSeries


@dataclass
class SpeechCache:
    """Cheap speech activity estimate (VAD-ish) once per video."""
    video_path: Path
    hop_s: float = 0.25
    speech_activity: Optional[TimeSeries] = None

    def build(self) -> "SpeechCache":
        hop = float(self.hop_s) if self.hop_s else 0.25
        hop = max(0.05, hop)

        af = "highpass=f=300,lowpass=f=3000,silencedetect=noise=-35dB:d=0.2"

        cmd = [
            "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "info",
            "-i", str(self.video_path),
            "-vn",
            "-af", af,
            "-f", "null", "-",
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.stderr is not None

        s_start = re.compile(r"silence_start:([0-9.]+)")
        s_end = re.compile(r"silence_end:([0-9.]+)")

        silences: List[Tuple[float, float]] = []
        cur_start: Optional[float] = None

        for line in proc.stderr:
            m1 = s_start.search(line)
            if m1:
                cur_start = float(m1.group(1))
                continue
            m2 = s_end.search(line)
            if m2 and cur_start is not None:
                silences.append((cur_start, float(m2.group(1))))
                cur_start = None

        proc.wait(timeout=180)

        dur = self._probe_duration()
        n = int(dur / hop) + 1
        act = [1.0] * n
        for a, b in silences:
            i0 = int(a / hop)
            i1 = int(b / hop) + 1
            for i in range(max(0, i0), min(n, i1)):
                act[i] = 0.0

        self.speech_activity = TimeSeries(t0=0.0, dt=hop, values=act)
        return self

    def _probe_duration(self) -> float:
        import json
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(self.video_path),
        ]
        out = subprocess.check_output(cmd, text=True)
        d = json.loads(out)
        return float(d["format"].get("duration") or 0.0)

    def query(self, start: float, end: float) -> Dict[str, Any]:
        if self.speech_activity is None:
            self.build()
        assert self.speech_activity is not None
        return {
            "speech_ratio": float(self.speech_activity.mean(start, end, default=0.0)),
            "segments": [],
        }
