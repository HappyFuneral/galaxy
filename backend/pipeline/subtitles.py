from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
from pathlib import Path

def _ts(t: float) -> str:
    # SRT time format: HH:MM:SS,mmm
    if t < 0:
        t = 0.0
    ms = int(round(t * 1000))
    h = ms // 3600000
    ms -= h * 3600000
    m = ms // 60000
    ms -= m * 60000
    s = ms // 1000
    ms -= s * 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

@dataclass(frozen=True)
class SrtItem:
    start: float
    end: float
    text: str

def build_srt_items(asr_segments: List[Dict[str, Any]]) -> List[SrtItem]:
    items: List[SrtItem] = []
    for seg in asr_segments:
        st = float(seg["start"])
        en = float(seg["end"])
        tx = str(seg["text"]).strip()
        if not tx or en <= st:
            continue
        items.append(SrtItem(start=st, end=en, text=tx))
    return items

def write_srt(items: List[SrtItem], out_path: Path) -> None:
    lines = []
    for idx, it in enumerate(items, start=1):
        lines.append(str(idx))
        lines.append(f"{_ts(it.start)} --> {_ts(it.end)}")
        lines.append(it.text)
        lines.append("")  # blank line
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
