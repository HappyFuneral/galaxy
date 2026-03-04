from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import time
import uuid

from backend.pipeline.postprocess import build_vf_filtergraph
from backend.pipeline.audio_mix import export_clip_with_optional_bgm
from backend.pipeline.recipe import write_export_recipe

@dataclass(frozen=True)
class ReexportRequest:
    job_id: str
    export_id: str
    recipe: Dict[str, Any]
    overrides: Dict[str, Any]
    cfg: Dict[str, Any]
    out_dir: Path
    export_size: Optional[Tuple[int, int]] = None

@dataclass(frozen=True)
class ReexportResult:
    new_export_id: str
    output_path: Path
    recipe_path: Path
    created_at: float

def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a or {})
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def render_hq_reexport(req: ReexportRequest) -> ReexportResult:
    t0 = time.time()

    recipe = req.recipe or {}
    input_video = Path(recipe["input_video"])
    if not input_video.exists():
        raise FileNotFoundError(f"input video missing: {input_video}")

    seg = recipe.get("segment") or {}
    start = float(seg.get("start", 0.0))
    end = float(seg.get("end", 0.0))
    if end <= start:
        raise ValueError("invalid segment in recipe")

    platform = str(recipe.get("platform", "tiktok"))

    merged = _deep_merge(recipe.get("overrides") or {}, req.overrides or {})
    post_cfg = _deep_merge(req.cfg.get("postprocess", {}) or {}, merged.get("postprocess", {}) or {})
    mix_cfg  = _deep_merge(req.cfg.get("audio_mix", {}) or {}, merged.get("audio_mix", {}) or {})

    active_windows = merged.get("active_windows") or (recipe.get("overrides") or {}).get("active_windows") or None

    burn_in_srt_path = recipe.get("burn_in_srt_path")
    speaker_face_track = recipe.get("speaker_face_track")
    apply_speaker_crop = bool(recipe.get("apply_speaker_crop", False))

    vf = build_vf_filtergraph(
        post_cfg,
        active_windows=active_windows,
        clip_duration_s=max(0.0, end - start),
        burn_in_srt_path=str(burn_in_srt_path) if burn_in_srt_path else None,
        speaker_face_track=speaker_face_track,
        apply_speaker_crop=apply_speaker_crop,
    )

    req.out_dir.mkdir(parents=True, exist_ok=True)
    new_export_id = f"{req.export_id}_re_{uuid.uuid4().hex[:8]}"
    out_path = req.out_dir / f"{new_export_id}.mp4"

    bgm_path = Path(recipe["bgm_path"]) if recipe.get("bgm_path") else None
    use_bgm = bool(recipe.get("use_bgm", False))

    debug_dir = req.out_dir / "_debug_ffmpeg"

    export_clip_with_optional_bgm(
        input_video=input_video,
        output_video=out_path,
        start=start,
        end=end,
        vf=vf,
        bgm_path=bgm_path,
        mix_cfg=mix_cfg,
        use_bgm=use_bgm,
        debug_dir=debug_dir,
        debug_stem=out_path.stem,
    )

    recipe_path = req.out_dir / f"{new_export_id}.recipe.json"
    write_export_recipe(
        recipe_path=recipe_path,
        input_video=input_video,
        platform=platform,
        segment={"start": start, "end": end},
        overrides=merged,
        bgm_path=bgm_path if bgm_path and bgm_path.exists() else None,
        use_bgm=use_bgm,
        burn_in_srt_path=Path(burn_in_srt_path) if burn_in_srt_path else None,
        speaker_face_track=speaker_face_track,
        apply_speaker_crop=apply_speaker_crop,
    )

    return ReexportResult(new_export_id=new_export_id, output_path=out_path, recipe_path=recipe_path, created_at=t0)
