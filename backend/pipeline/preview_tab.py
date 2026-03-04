from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from backend.pipeline.tab_ass import write_tab_ass

def maybe_build_tab_ass_for_preview(
    *,
    tab_json: Optional[str],
    out_dir: Path,
    stem: str,
    clip_duration_s: float,
    cfg: Dict[str, Any],
) -> Optional[Path]:
    """
    Preview path often skips heavy work.
    This helper ensures TAB overlay still appears in preview when tab_json exists.
    """
    if not tab_json:
        return None
    tab_overlay_cfg = (cfg.get("tab_overlay") or {})
    if not bool(tab_overlay_cfg.get("enabled", True)):
        return None
    out_path = out_dir / f"{stem}.tab.ass"
    return write_tab_ass(Path(tab_json), out_path, clip_duration_s=float(clip_duration_s), cfg=tab_overlay_cfg)
