from __future__ import annotations

import os
import time
import uuid
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException,Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config.loader import load_all_configs
from backend.pipeline.pipeline import run_pipeline
from backend.api.deps import set_cfg, get_cfg
from backend.api.routes.exports import router as exports_router


# ---------------------------
# Paths / Config
# ---------------------------
APP_DIR = Path(os.getenv("APP_DIR", ".")).resolve()
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", str(APP_DIR / "backend/config"))).resolve()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(APP_DIR / "uploads"))).resolve()
EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", str(APP_DIR / "exports"))).resolve()
BGM_DIR = Path(os.getenv("BGM_DIR", str(APP_DIR / "bgm_uploads"))).resolve()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
BGM_DIR.mkdir(parents=True, exist_ok=True)

cfg = load_all_configs(CONFIG_DIR)


# Job model (in-memory)
# ---------------------------
@dataclass
class Job:
    job_id: str
    video_id: str
    platform: str
    export: bool
    status: str  # queued | running | done | failed
    stage: str
    progress: float
    error: Optional[str]
    created_at: float
    updated_at: float
    result: Optional[Dict[str, Any]]
    burn_in: bool = True
    speaker_focus: bool = True
    # options
    bgm_path: Optional[str] = None
    captions: bool = True




JOBS: Dict[str, Job] = {}
VIDEO_INDEX: Dict[str, str] = {}  # video_id -> filepath


def _now() -> float:
    return time.time()


def _set_job(job: Job, *, status: Optional[str] = None, stage: Optional[str] = None, progress: Optional[float] = None,
             error: Optional[str] = None):
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    job.updated_at = _now()


def _run_job(job_id: str):
    job = JOBS[job_id]
    try:
        _set_job(job, status="running", stage="analyze", progress=0.05)

        video_path = Path(VIDEO_INDEX[job.video_id])

        export_dir = EXPORTS_DIR / job.job_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # export_size: TikTok/Reels/Shorts 1080x1920 default
        export_size = (1080, 1920) if job.platform in {"tiktok", "reels", "shorts"} else None

        _set_job(job, stage="pipeline", progress=0.15)

        result = run_pipeline(
            video_path=video_path,
            platform=job.platform,
            export=job.export,
            export_dir=export_dir,
            export_size=export_size,
            cfg=cfg,
            job_bgm_path_str=job.bgm_path,
            captions=job.captions,
            burn_in=job.burn_in,
            speaker_focus=job.speaker_focus
        )

        # add download urls to exports (API relative)
        exports = result.get("exports", []) or []
        for ex in exports:
            fn = ex.get("filename")
            if fn:
                ex["url"] = f"/jobs/{job.job_id}/downloads/{fn}"
            srt = ex.get("srt")
            if srt:
                # store only filename in url for client convenience
                srt_name = Path(srt).name
                ex["srt_url"] = f"/jobs/{job.job_id}/downloads/{srt_name}"

        _set_job(job, stage="done", progress=1.0)
        job.result = result
        _set_job(job, status="done")

    except Exception as e:
        _set_job(job, status="failed", stage="failed", progress=1.0, error=str(e))


# ---------------------------
# FastAPI
# ---------------------------
app = FastAPI(title="AI Video Editor Backend", version="0.1.0")

set_cfg(cfg)  # after you load your YAMLs
app.include_router(exports_router, dependencies=[Depends(get_cfg)])
# ---------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    video_id = str(uuid.uuid4())
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    out = UPLOAD_DIR / f"{video_id}_{uuid.uuid4().hex}{suffix}"
    content = await file.read()
    out.write_bytes(content)
    VIDEO_INDEX[video_id] = str(out)
    return {"video_id": video_id, "filename": out.name, "path": str(out)}


@app.post("/upload-bgm")
async def upload_bgm(file: UploadFile = File(...)):
    bgm_id = str(uuid.uuid4())
    suffix = Path(file.filename or "bgm.mp3").suffix or ".mp3"
    out = BGM_DIR / f"{bgm_id}{suffix}"
    content = await file.read()
    out.write_bytes(content)
    return {"bgm_id": bgm_id, "filename": out.name, "path": str(out)}


def _resolve_bgm_path(bgm_id: Optional[str]) -> Optional[str]:
    if not bgm_id:
        return None
    matches = list(BGM_DIR.glob(f"{bgm_id}.*"))
    if not matches:
        return None
    return str(matches[0])


@app.post("/jobs")
def create_job(
        video_id: str,
        platform: str = "tiktok",
        export: bool = True,
        bgm_id: Optional[str] = None,
        captions: bool = True,
        burn_in: bool = True,
        speaker_focus: bool = True,
):
    if video_id not in VIDEO_INDEX:
        raise HTTPException(status_code=404, detail="Unknown video_id")

    job_id = str(uuid.uuid4())
    bgm_path = _resolve_bgm_path(bgm_id)

    job = Job(
        job_id=job_id,
        video_id=video_id,
        platform=platform,
        export=export,
        status="queued",
        stage="queued",
        progress=0.0,
        error=None,
        created_at=_now(),
        updated_at=_now(),
        result=None,
        bgm_path=bgm_path,
        captions=captions,
        burn_in=burn_in,
        speaker_focus=speaker_focus
    )
    JOBS[job_id] = job

    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    t.start()

    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")

    d = asdict(job)
    # don't expose internal full result here
    d["result"] = None
    return d


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"Job not done (status={job.status})")
    return job.result or {}


@app.get("/jobs/{job_id}/downloads/{filename}")
def download(job_id: str, filename: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    p = (EXPORTS_DIR / job_id / filename).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p))
