from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# string_index in tab.json:
# 0=low E, 1=A, 2=D, 3=G, 4=B, 5=high e
_STR_ORDER = [5, 4, 3, 2, 1, 0]  # display e,B,G,D,A,E


def _ass_time(t: float) -> str:
    # ASS: H:MM:SS.cs (centiseconds)
    if t < 0:
        t = 0.0
    cs = int(round(t * 100.0))
    s, cs = divmod(cs, 100)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _tab_lines_from_columns(columns: List[Dict[int, str]], cols: int, cell_w: int) -> List[str]:
    names = {5: "e", 4: "B", 3: "G", 2: "D", 1: "A", 0: "E"}
    lines: Dict[int, List[str]] = {si: [names[si] + "|"] for si in _STR_ORDER}
    dash = "-" * cell_w

    for col in range(cols):
        mapping = columns[col] if col < len(columns) else {}
        for si in _STR_ORDER:
            cell = mapping.get(si, dash)
            if len(cell) < cell_w:
                cell = cell + ("-" * (cell_w - len(cell)))
            elif len(cell) > cell_w:
                cell = cell[:cell_w]
            lines[si].append(cell)

    for si in _STR_ORDER:
        lines[si].append("|")
    return ["".join(lines[si]) for si in _STR_ORDER]


@dataclass(frozen=True)
class TabOverlayCfg:
    step_s: float = 0.12
    columns: int = 22
    cell_w: int = 3
    min_conf: float = 0.35
    prefer_highest_midi: bool = True
    show_sustained: bool = True


def load_tab_notes(tab_json_path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(tab_json_path.read_text(encoding="utf-8"))
    return payload.get("tab_notes") or []


def build_tab_events(
    tab_notes: List[Dict[str, Any]],
    *,
    duration_s: float,
    cfg: TabOverlayCfg,
) -> List[Tuple[float, float, str]]:
    step = max(0.06, float(cfg.step_s))
    cols = int(cfg.columns)
    cell_w = int(cfg.cell_w)
    min_conf = float(cfg.min_conf)

    notes = []
    for n in tab_notes:
        try:
            t0 = float(n.get("t_start", 0.0))
            t1 = float(n.get("t_end", t0))
            si = int(n.get("string_index", -1))
            fret = int(n.get("fret", -1))
            conf = float(n.get("conf", 1.0))
            midi = int(n.get("midi", 0))
        except Exception:
            continue
        if si not in range(6) or fret < 0:
            continue
        if conf < min_conf:
            continue
        if t1 <= t0:
            t1 = t0 + 0.01
        notes.append((t0, t1, si, fret, conf, midi))
    notes.sort(key=lambda x: x[0])

    columns: List[Dict[int, str]] = [{} for _ in range(cols)]
    write_idx = 0
    events: List[Tuple[float, float, str]] = []

    t = 0.0
    j = 0
    n = len(notes)

    # Active sustain notes by string (fret, conf, midi, end_time)
    sustain: Dict[int, Tuple[int, float, int, float]] = {}

    while t < duration_s - 1e-6:
        t0 = t
        t1 = min(duration_s, t + step)

        bucket: Dict[int, Tuple[int, float, int]] = {}

        while j < n and notes[j][0] < t1:
            nt0, nt1, si, fret, conf, midi = notes[j]
            if nt0 >= t0:
                prev = bucket.get(si)
                if prev is None:
                    bucket[si] = (fret, conf, midi)
                else:
                    if cfg.prefer_highest_midi:
                        if midi > prev[2]:
                            bucket[si] = (fret, conf, midi)
                    else:
                        if conf > prev[1]:
                            bucket[si] = (fret, conf, midi)
                sustain[si] = (fret, conf, midi, nt1)
            j += 1

        if cfg.show_sustained:
            for si, (fret, conf, midi, tend) in list(sustain.items()):
                if tend <= t0:
                    sustain.pop(si, None)
                    continue
                if si not in bucket:
                    bucket[si] = (fret, conf, midi)

        col_map: Dict[int, str] = {}
        for si, (fret, conf, midi) in bucket.items():
            s = str(fret)
            if len(s) == 1:
                cell = f"-{s}-"
            elif len(s) == 2:
                cell = f"{s}-" if cell_w == 3 else s
            else:
                cell = s[:cell_w]
            col_map[si] = cell

        columns[write_idx] = col_map
        write_idx = (write_idx + 1) % cols

        ordered_cols = columns[write_idx:] + columns[:write_idx]
        lines = _tab_lines_from_columns(ordered_cols, cols=cols, cell_w=cell_w)
        text = r"\N".join(lines)
        events.append((t0, t1, text))

        t += step

    return events


def write_tab_ass(
    tab_json_path: Path,
    out_ass_path: Path,
    *,
    clip_duration_s: float,
    cfg: Optional[Dict[str, Any]] = None,
) -> Path:
    cfg = cfg or {}
    ocfg = TabOverlayCfg(
        step_s=float(cfg.get("step_s", 0.12)),
        columns=int(cfg.get("columns", 22)),
        cell_w=int(cfg.get("cell_w", 3)),
        min_conf=float(cfg.get("min_conf", 0.35)),
        prefer_highest_midi=bool(cfg.get("prefer_highest_midi", True)),
        show_sustained=bool(cfg.get("show_sustained", True)),
    )

    tab_notes = load_tab_notes(tab_json_path)
    events = build_tab_events(tab_notes, duration_s=float(clip_duration_s), cfg=ocfg)

    font = str(cfg.get("font", "Courier New"))
    font_size = int(cfg.get("font_size", 26))

    # ASS colour is &HAABBGGRR (alpha first)
    primary = str(cfg.get("primary_colour", "&H00FFFFFF"))
    outline_colour = str(cfg.get("outline_colour", "&H80000000"))
    back_colour = str(cfg.get("back_colour", "&H6A000000"))
    outline = int(cfg.get("outline", 2))
    shadow = int(cfg.get("shadow", 0))

    margin_v = int(cfg.get("margin_v", 52))
    margin_lr = int(cfg.get("margin_lr", 36))

    header_lines = [
        "[Script Info]\n",
        "ScriptType: v4.00+\n",
        "Collisions: Normal\n",
        "PlayResX: 1080\n",
        "PlayResY: 1920\n",
        "\n",
        "[V4+ Styles]\n",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n",
        f"Style: Tab,{font},{font_size},{primary},&H00000000,{outline_colour},{back_colour},0,0,0,0,100,100,0,0,3,{outline},{shadow},2,{margin_lr},{margin_lr},{margin_v},1\n",
        "\n",
        "[Events]\n",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
    ]
    out_lines = ["".join(header_lines)]
    for (t0, t1, text) in events:
        out_lines.append(f"Dialogue: 20,{_ass_time(t0)},{_ass_time(t1)},Tab,,0,0,0,,{text}\n")

    out_ass_path.parent.mkdir(parents=True, exist_ok=True)
    out_ass_path.write_text("".join(out_lines), encoding="utf-8")
    return out_ass_path
