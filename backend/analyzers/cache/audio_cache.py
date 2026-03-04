from __future__ import annotations
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import TimeSeries


@dataclass
class AudioCache:
    """Compute cheap audio 'music activity' envelope once per video."""
    video_path: Path
    hop_s: float = 0.25
    rms_db: Optional[TimeSeries] = None
    activity: Optional[TimeSeries] = None

    def build(self) -> "AudioCache":
        hop = float(self.hop_s) if self.hop_s else 0.25
        hop = max(0.05, hop)

        af = f"asetnsamples=n={int(48000*hop)}:p=1,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level"

        cmd = [
            "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "info",
            "-i", str(self.video_path),
            "-vn",
            "-af", af,
            "-f", "null", "-",
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert proc.stderr is not None

        t_re = re.compile(r"pts_time:([0-9.]+)")
        v_re = re.compile(r"lavfi\.astats\.Overall\.RMS_level=([-0-9.]+)")

        times: List[float] = []
        vals: List[float] = []
        last_t: Optional[float] = None

        for line in proc.stderr:
            m1 = t_re.search(line)
            if m1:
                last_t = float(m1.group(1))
                continue
            m2 = v_re.search(line)
            if m2 and last_t is not None:
                times.append(last_t)
                vals.append(float(m2.group(1)))

        proc.wait(timeout=180)

        if not times:
            self.rms_db = TimeSeries(t0=0.0, dt=hop, values=[-60.0])
            self.activity = TimeSeries(t0=0.0, dt=hop, values=[0.0])
            return self

        t0 = 0.0
        dt = hop
        n = int((max(times) - t0) / dt) + 1
        buckets = [[] for _ in range(n)]
        for t, v in zip(times, vals):
            i = int((t - t0) / dt)
            if 0 <= i < n:
                buckets[i].append(v)

        rms = []
        for b in buckets:
            rms.append(sum(b)/len(b) if b else -60.0)

        act = [self._db_to_activity(x) for x in rms]
        self.rms_db = TimeSeries(t0=t0, dt=dt, values=rms)
        self.activity = TimeSeries(t0=t0, dt=dt, values=act)
        return self

    @staticmethod
    def _db_to_activity(db: float) -> float:
        lo, hi = -60.0, -10.0
        x = (db - lo) / (hi - lo)
        return float(max(0.0, min(1.0, x)))

    def query(self, start: float, end: float) -> Dict[str, Any]:
        if self.activity is None:
            self.build()
        assert self.activity is not None
        return {
            "music_activity": float(self.activity.mean(start, end, default=0.0)),
            "music_peak": float(self.activity.max(start, end, default=0.0)),
        }
