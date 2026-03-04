from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import time

from backend.pipeline.postprocess import build_vf_filtergraph
from backend.pipeline.audio_mix import export_clip_with_optional_bgm

@dataclass(frozen=True)
class PreviewRequest:
    export_id: str
    input_video: Path
    start: float
    end: float
    platform: str
    overrides: Dict[str, Any]
    bgm_path: Optional[Path] = None
    use_bgm: bool = False
    burn_in_srt_path: Optional[str] = None
    speaker_face_track: Optional[list] = None
    apply_speaker_crop: bool = False

@dataclass(frozen=True)
class PreviewResult:
    preview_path: Path
    duration_s: float
    created_at: float

def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a or {})
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def render_preview(
    *,
    req: PreviewRequest,
    cfg: Dict[str, Any],
    out_dir: Path,
    size: Tuple[int, int] = (540, 960),
    preview_seconds: float = 6.0,
) -> PreviewResult:
    t0 = time.time()

    seg_start = float(req.start)
    seg_end = float(req.end)
    if preview_seconds > 0:
        seg_end = min(seg_end, seg_start + float(preview_seconds))

    clip_dur = max(0.0, seg_end - seg_start)
    if clip_dur <= 0.05:
        raise ValueError("Preview segment duration too small")

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    out_path = out_dir / f"preview_{req.export_id}_{stamp}.mp4"

    post_cfg = dict(cfg.get("postprocess", {}) or {})
    mix_cfg = dict(cfg.get("audio_mix", {}) or {})
    ov = req.overrides or {}
    post_cfg = _deep_merge(post_cfg, ov.get("postprocess", {}) or {})
    mix_cfg = _deep_merge(mix_cfg, ov.get("audio_mix", {}) or {})

    # mark preview scale for postprocess (added in patched postprocess.py)
    post_cfg = dict(post_cfg)
    post_cfg["preview_scale"] = {"enabled": True, "w": int(size[0]), "h": int(size[1])}

    vf = build_vf_filtergraph(
        post_cfg,
        active_windows=ov.get("active_windows"),
        clip_duration_s=clip_dur,
        burn_in_srt_path=req.burn_in_srt_path,
        speaker_face_track=req.speaker_face_track,
        apply_speaker_crop=req.apply_speaker_crop,
    )

    debug_dir = out_dir / "_debug_ffmpeg"
    export_clip_with_optional_bgm(
        input_video=req.input_video,
        output_video=out_path,
        start=seg_start,
        end=seg_end,
        vf=vf,
        bgm_path=req.bgm_path,
        mix_cfg=mix_cfg,
        use_bgm=bool(req.use_bgm),
        debug_dir=debug_dir,
        debug_stem=out_path.stem,
    )

    return PreviewResult(preview_path=out_path, duration_s=clip_dur, created_at=t0)
