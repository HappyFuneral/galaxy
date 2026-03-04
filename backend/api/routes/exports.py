from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import time
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.pipeline.preview import PreviewRequest, render_preview
from backend.pipeline.reexport import ReexportRequest, render_hq_reexport
from fastapi import Depends
from backend.api.deps import get_cfg

router = APIRouter(prefix="/exports", tags=["exports"])

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def _exports_root(cfg: Dict[str, Any]) -> Path:
    return Path(cfg.get("paths", {}).get("exports_dir", "exports"))

def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def _write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

class RecipePatch(BaseModel):
    overrides: Dict[str, Any] = Field(default_factory=dict)

class PreviewBody(BaseModel):
    seconds: float = 6.0
    size_w: int = 540
    size_h: int = 960
    overrides: Dict[str, Any] = Field(default_factory=dict)

class ReexportBody(BaseModel):
    overrides: Dict[str, Any] = Field(default_factory=dict)

@router.get("")
def list_exports(job_id: str, cfg: Dict[str, Any] = Depends(get_cfg)) -> Dict[str, Any]:
    root = _exports_root(cfg) / job_id
    if not root.exists():
        raise HTTPException(404, f"job exports not found: {job_id}")
    items = []
    for p in sorted(root.glob("*.mp4")):
        export_id = p.stem
        recipe_p = root / f"{export_id}.recipe.json"
        items.append({
            "export_id": export_id,
            "video": str(p),
            "recipe": str(recipe_p) if recipe_p.exists() else None,
        })
    return {"job_id": job_id, "exports": items}

@router.get("/{job_id}/files/{name}")
def get_export_file(job_id: str, name: str, cfg: Dict[str, Any] = Depends(get_cfg)):
    if not _SAFE_NAME.match(name):
        raise HTTPException(400, "invalid name")
    root = _exports_root(cfg) / job_id
    p = root / name
    if not p.exists():
        raise HTTPException(404, "file not found")
    mt = "video/mp4" if name.endswith(".mp4") else "application/octet-stream"
    return FileResponse(str(p), media_type=mt, filename=name)

@router.get("/{job_id}/{export_id}/recipe")
def get_recipe(job_id: str, export_id: str, cfg: Dict[str, Any] = Depends(get_cfg)) -> Dict[str, Any]:
    root = _exports_root(cfg) / job_id
    p = root / f"{export_id}.recipe.json"
    if not p.exists():
        raise HTTPException(404, "recipe not found")
    return _read_json(p)

@router.patch("/{job_id}/{export_id}/recipe")
def patch_recipe(job_id: str, export_id: str, body: RecipePatch, cfg: Dict[str, Any] = Depends(get_cfg)) -> Dict[str, Any]:
    root = _exports_root(cfg) / job_id
    p = root / f"{export_id}.recipe.json"
    if not p.exists():
        raise HTTPException(404, "recipe not found")
    cur = _read_json(p)
    cur_over = cur.get("overrides") or {}
    cur_over.update(body.overrides or {})
    cur["overrides"] = cur_over
    cur["updated_at"] = time.time()
    _write_json(p, cur)
    return cur

@router.get("/{job_id}/previews/{name}")
def get_preview_file(job_id: str, name: str, cfg: Dict[str, Any] = Depends(get_cfg)):
    if not _SAFE_NAME.match(name):
        raise HTTPException(400, "invalid name")
    root = _exports_root(cfg) / job_id / "previews"
    p = root / name
    if not p.exists():
        raise HTTPException(404, "preview not found")
    return FileResponse(str(p), media_type="video/mp4", filename=name)

@router.post("/{job_id}/{export_id}/preview")
def preview_export(
    job_id: str,
    export_id: str,
    body: PreviewBody,
    cfg: Dict[str, Any] = Depends(get_cfg),
):
    root = _exports_root(cfg) / job_id
    recipe_p = root / f"{export_id}.recipe.json"
    if not recipe_p.exists():
        raise HTTPException(404, "recipe not found")

    recipe = _read_json(recipe_p)
    video_path = Path(recipe["input_video"])
    if not video_path.exists():
        raise HTTPException(404, f"input video missing: {video_path}")

    seg = recipe.get("segment") or {}
    start = float(seg.get("start", 0.0))
    end = float(seg.get("end", 0.0))
    if end <= start:
        raise HTTPException(400, "invalid segment in recipe")

    merged_overrides = dict(recipe.get("overrides") or {})
    merged_overrides.update(body.overrides or {})

    previews_dir = _ensure_dir(root / "previews")

    req = PreviewRequest(
        export_id=export_id,
        input_video=video_path,
        start=start,
        end=end,
        platform=str(recipe.get("platform", "tiktok")),
        overrides=merged_overrides,
        bgm_path=Path(recipe["bgm_path"]) if recipe.get("bgm_path") else None,
        use_bgm=bool(recipe.get("use_bgm", False)),
        burn_in_srt_path=str(recipe.get("burn_in_srt_path")) if recipe.get("burn_in_srt_path") else None,
        speaker_face_track=recipe.get("speaker_face_track"),
        apply_speaker_crop=bool(recipe.get("apply_speaker_crop", False)),
    )

    res = render_preview(
        req=req,
        cfg=cfg,
        out_dir=previews_dir,
        size=(int(body.size_w), int(body.size_h)),
        preview_seconds=float(body.seconds),
    )

    name = res.preview_path.name
    preview_url = f"/exports/{job_id}/previews/{name}"

    return {
        "job_id": job_id,
        "export_id": export_id,
        "preview_url": preview_url,
        "duration_s": res.duration_s,
        "created_at": res.created_at,
    }

@router.post("/{job_id}/{export_id}/reexport")
def reexport_hq(
    job_id: str,
    export_id: str,
    body: ReexportBody,
    cfg: Dict[str, Any] = Depends(get_cfg),
):
    root = _exports_root(cfg) / job_id
    recipe_p = root / f"{export_id}.recipe.json"
    if not recipe_p.exists():
        raise HTTPException(404, "recipe not found")
    recipe = _read_json(recipe_p)

    req = ReexportRequest(
        job_id=job_id,
        export_id=export_id,
        recipe=recipe,
        overrides=body.overrides or {},
        cfg=cfg,
        out_dir=root,
        export_size=None,
    )
    try:
        res = render_hq_reexport(req)
    except Exception as e:
        raise HTTPException(500, str(e))

    file_name = res.output_path.name
    file_url = f"/exports/{job_id}/files/{file_name}"

    return {
        "job_id": job_id,
        "base_export_id": export_id,
        "new_export_id": res.new_export_id,
        "file_url": file_url,
        "recipe_url": f"/exports/{job_id}/{res.new_export_id}/recipe",
        "created_at": res.created_at,
    }
