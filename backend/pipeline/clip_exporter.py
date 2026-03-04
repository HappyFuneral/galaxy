from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional


def export_clip_ffmpeg(input_path: Path, output_path: Path, start: float, end: float, target_w: Optional[int] = None,
                       target_h: Optional[int] = None) -> None:
    duration = max(0.0, end - start)
    if duration <= 0:
        raise ValueError("Invalid clip duration")

    vf = []
    if target_w and target_h:
        vf.append(f"scale={target_w}:{target_h}")

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", str(input_path),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
    ]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += [str(output_path)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
