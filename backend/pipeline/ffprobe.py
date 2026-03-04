
import json
import subprocess
from pathlib import Path

def get_video_duration_seconds(path: Path) -> float:
    cmd = ["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    data = json.loads(proc.stdout)
    return float(data["format"]["duration"])
