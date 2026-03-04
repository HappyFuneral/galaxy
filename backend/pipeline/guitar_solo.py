from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SoloOverlayResult:
    windows: List[Dict[str, Any]]
    confidence: float
    reasons: Dict[str, Any]


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _coalesce(windows: List[Dict[str, Any]], gap: float = 0.15, min_len: float = 0.35) -> List[Dict[str, Any]]:
    if not windows:
        return []
    ws = sorted(
        [{"start": float(w["start"]), "end": float(w["end"]), "intensity": float(w.get("intensity", 1.0))} for w in windows],
        key=lambda x: x["start"],
    )
    out: List[Dict[str, Any]] = []
    cur = ws[0].copy()
    for w in ws[1:]:
        if w["start"] <= cur["end"] + gap:
            cur["end"] = max(cur["end"], w["end"])
            cur["intensity"] = max(cur["intensity"], w.get("intensity", 1.0))
        else:
            if cur["end"] - cur["start"] >= min_len:
                out.append(cur)
            cur = w.copy()
    if cur["end"] - cur["start"] >= min_len:
        out.append(cur)
    return out


def solo_windows_from_note_events(
    note_events: List[Dict[str, Any]],
    *,
    bin_s: float = 1.5,
    min_density_notes_per_s: float = 1.6,
    min_coverage_ratio: float = 0.55,   # NEW: bin idő hány %-ában van pitch
    min_window_s: float = 0.40,
) -> List[Dict[str, Any]]:
    if not note_events:
        return []

    # Bin-enként számoljuk:
    # - note count (density)
    # - total covered duration (coverage)
    bins_count: Dict[int, int] = {}
    bins_cov: Dict[int, float] = {}

    for e in note_events:
        try:
            t0 = float(e.get("t_start", 0.0))
            t1 = float(e.get("t_end", 0.0))
        except Exception:
            continue
        if t1 <= t0:
            continue

        # event átfedése több binre is eshet
        b0 = int(t0 // bin_s)
        b1 = int((t1) // bin_s)

        # count: csak a kezdő binre számoljuk (ne duplázzunk túl durván)
        bins_count[b0] = bins_count.get(b0, 0) + 1

        for b in range(b0, b1 + 1):
            bs = b * bin_s
            be = bs + bin_s
            overlap = max(0.0, min(t1, be) - max(t0, bs))
            if overlap > 0:
                bins_cov[b] = bins_cov.get(b, 0.0) + overlap

    windows: List[Dict[str, Any]] = []

    for b in sorted(set(list(bins_count.keys()) + list(bins_cov.keys()))):
        cnt = bins_count.get(b, 0)
        cov = bins_cov.get(b, 0.0)

        density = cnt / max(1e-6, bin_s)
        coverage_ratio = cov / max(1e-6, bin_s)

        # SOLO, ha EITHER sűrű a note váltás, OR nagy részében van pitch
        if (density >= min_density_notes_per_s) or (coverage_ratio >= min_coverage_ratio):
            intensity = 0.5
            intensity += min(0.4, max(0.0, (coverage_ratio - min_coverage_ratio) * 1.2))
            intensity += min(0.3, max(0.0, (density - min_density_notes_per_s) / 3.0))
            windows.append(
                {"start": b * bin_s, "end": b * bin_s + bin_s, "intensity": float(_clip(intensity, 0.4, 1.0))}
            )

    return _coalesce(windows, gap=0.12, min_len=min_window_s)


def solo_overlay_from_tab_json(tab_json_path: Path, *, cfg: Optional[Dict[str, Any]] = None) -> SoloOverlayResult:
    cfg = cfg or {}
    bin_s = float(cfg.get("bin_s",2.0))
    min_density = float(cfg.get("min_density_notes_per_s", 0.6))
    min_window_s = float(cfg.get("min_window_s", 0.40))
    min_cov = float(cfg.get("min_coverage_ratio", 0.55))

    try:
        payload = json.loads(tab_json_path.read_text(encoding="utf-8"))
        note_events = payload.get("note_events") or []
    except Exception as e:
        return SoloOverlayResult(windows=[], confidence=0.0, reasons={"error": str(e), "source": str(tab_json_path)})

    windows = solo_windows_from_note_events(
        note_events, bin_s=bin_s, min_density_notes_per_s=min_density,min_coverage_ratio=min_cov, min_window_s=min_window_s
    )

    if windows:
        avg_int = sum(float(w.get("intensity", 1.0)) for w in windows) / len(windows)
        conf = _clip(0.55 + 0.25 * _clip(avg_int) + 0.20 * _clip(len(windows) / 4.0))
    else:
        conf = 0.0

    return SoloOverlayResult(
        windows=windows,
        confidence=float(conf),
        reasons={
            "tab_json": str(tab_json_path),
            "windows": len(windows),
            "bin_s": bin_s,
            "min_density_notes_per_s": min_density,
            "min_window_s": min_window_s,
        },
    )
