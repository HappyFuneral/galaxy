from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
import json
import time

def write_export_recipe(
    *,
    recipe_path: Path,
    input_video: Path,
    platform: str,
    segment: Dict[str, float],
    overrides: Optional[Dict[str, Any]] = None,
    bgm_path: Optional[Path] = None,
    use_bgm: bool = False,
    burn_in_srt_path: Optional[Path] = None,
    speaker_face_track: Optional[list] = None,
    apply_speaker_crop: bool = False,
) -> None:
    """
    Persist a "render recipe" next to an export file, so we can:
      - preview (fast)
      - re-export with overrides from mobile
    """
    obj: Dict[str, Any] = {
        "input_video": str(input_video),
        "platform": platform,
        "segment": {"start": float(segment["start"]), "end": float(segment["end"])},
        "overrides": overrides or {},
        "bgm_path": str(bgm_path) if bgm_path else None,
        "use_bgm": bool(use_bgm),
        "burn_in_srt_path": str(burn_in_srt_path) if burn_in_srt_path else None,
        "speaker_face_track": speaker_face_track,
        "apply_speaker_crop": bool(apply_speaker_crop),
        "created_at": time.time(),
        "updated_at": time.time(),
        "version": "v1.7.1",
    }
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    recipe_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
