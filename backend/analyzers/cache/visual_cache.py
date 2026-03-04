from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .types import TimeSeries


@dataclass
class VisualCache:
    """Compute cheap visual activity (motion proxy) once per video."""
    video_path: Path
    sample_fps: float = 0.5
    max_width: int = 256
    dt: float = 2.0
    motion: Optional[TimeSeries] = None
    brightness: Optional[TimeSeries] = None

    def build(self) -> "VisualCache":
        fps = float(self.sample_fps) if self.sample_fps else 0.5
        fps = max(0.1, fps)
        self.dt = 1.0 / fps

        vf = f"fps={fps},scale={self.max_width}:-2"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(self.video_path),
            "-an", "-vf", vf,
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None

        w, h = self._probe_scaled_size()
        frame_bytes = w * h * 3

        prev = None
        motions: List[float] = []
        brs: List[float] = []

        while True:
            buf = proc.stdout.read(frame_bytes)
            if not buf or len(buf) < frame_bytes:
                break
            frame = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 3))
            brs.append(float(frame.mean() / 255.0))

            if prev is None:
                motions.append(0.0)
            else:
                diff = np.abs(frame.astype(np.int16) - prev.astype(np.int16))
                motions.append(float(diff.mean() / 255.0))
            prev = frame

        try:
            proc.stdout.close()
        except Exception:
            pass
        proc.wait(timeout=120)

        self.motion = TimeSeries(t0=0.0, dt=self.dt, values=motions)
        self.brightness = TimeSeries(t0=0.0, dt=self.dt, values=brs)
        return self

    def _probe_scaled_size(self) -> Tuple[int, int]:
        import json
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            str(self.video_path),
        ]
        out = subprocess.check_output(cmd, text=True)
        data = json.loads(out)
        s = data["streams"][0]
        ow, oh = int(s["width"]), int(s["height"])
        w = min(self.max_width, ow)
        h = int(round(oh * (w / ow)))
        if w % 2 == 1: w -= 1
        if h % 2 == 1: h -= 1
        return max(2, w), max(2, h)

    def query(self, start: float, end: float, motion_thr: float = 0.08) -> Dict[str, Any]:
        if self.motion is None or self.brightness is None:
            self.build()
        assert self.motion and self.brightness

        motion_mean = self.motion.mean(start, end, default=0.0)
        motion_max = self.motion.max(start, end, default=0.0)
        bright_mean = self.brightness.mean(start, end, default=0.0)

        active_frac = self.motion.fraction_above(start, end, thr=motion_thr, default=0.0)
        active_windows = self._active_windows(start, end, thr=motion_thr, min_len_s=0.8)

        return {
            "motion_mean": float(motion_mean),
            "motion_max": float(motion_max),
            "brightness_mean": float(bright_mean),
            "active_fraction": float(active_frac),
            "active_windows": active_windows,
        }

    def _active_windows(self, start: float, end: float, thr: float, min_len_s: float) -> List[Dict[str, float]]:
        assert self.motion is not None
        xs = self.motion.slice(start, end)
        if not xs:
            return []
        windows: List[Tuple[float, float]] = []
        in_run = False
        run_start = 0.0
        for i, v in enumerate(xs):
            t = start + i * self.motion.dt
            if v >= thr and not in_run:
                in_run = True
                run_start = t
            if v < thr and in_run:
                w0, w1 = run_start, t
                if (w1 - w0) >= min_len_s:
                    windows.append((w0, w1))
                in_run = False
        if in_run:
            w0, w1 = run_start, end
            if (w1 - w0) >= min_len_s:
                windows.append((w0, w1))

        rel = []
        for w0, w1 in windows:
            rel.append({"start": float(max(0.0, w0 - start)), "end": float(max(0.0, min(end, w1) - start))})
        return rel
