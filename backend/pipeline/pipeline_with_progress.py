
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from backend.pipeline.pipeline import run_pipeline

ProgressCb = Callable[[str, float], None]

def run_demo_pipeline_with_progress(
    video_path: Path,
    platform: str,
    export: bool,
    export_dir: Path,
    export_size: Optional[Tuple[int, int]],
    cfg: Dict[str, Any],
    progress_cb: Optional[ProgressCb] = None,
) -> Dict[str, Any]:
    def tick(stage: str, p: float):
        if progress_cb:
            progress_cb(stage, max(0.0, min(1.0, float(p))))

    tick("probing_video", 0.03)
    tick("generating_segments", 0.10)
    tick("initializing_analyzers", 0.18)
    tick("scoring_segments", 0.35)

    payload = run_pipeline(
        video_path=video_path,
        platform=platform,
        export=export,
        export_dir=export_dir,
        export_size=export_size,
        cfg=cfg,
    )

    tick("selecting_top_clips", 0.82)
    tick("exporting_clips" if export else "skipping_export", 0.92)
    tick("done", 1.0)
    return payload
