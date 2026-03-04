from __future__ import annotations

from typing import Any, Dict, List, Optional
from backend.pipeline.speaker_focus import build_speaker_crop_x_expr


def _fmt(x: float) -> str:
    return f"{x:.3f}"


def _escape_subtitles_path(p: str) -> str:
    return p.replace("\\", "\\\\").replace("'", "\\'")


def _coalesce_windows(windows: List[Dict[str, Any]], min_len: float) -> List[Dict[str, Any]]:
    if not windows:
        return []
    ws = sorted(
        [{"start": float(w["start"]), "end": float(w["end"]), "intensity": float(w.get("intensity", 1.0))} for w in windows],
        key=lambda w: w["start"],
    )
    merged: List[Dict[str, Any]] = []
    cur = ws[0].copy()
    for w in ws[1:]:
        if w["start"] <= cur["end"] + 0.10:
            cur["end"] = max(cur["end"], w["end"])
            cur["intensity"] = max(cur["intensity"], w["intensity"])
        else:
            if (cur["end"] - cur["start"]) >= min_len:
                merged.append(cur)
            cur = w.copy()
    if (cur["end"] - cur["start"]) >= min_len:
        merged.append(cur)
    return merged


def _build_enable_expr(windows: List[Dict[str, Any]]) -> Optional[str]:
    if not windows:
        return None
    parts = [f"between(t,{_fmt(w['start'])},{_fmt(w['end'])})" for w in windows]
    return "+".join(parts)


def build_vf_filtergraph(
    post_cfg: Dict[str, Any],
    active_windows: Optional[List[Dict[str, Any]]] = None,
    clip_duration_s: Optional[float] = None,
    *,
    burn_in_srt_path: Optional[str] = None,
    tab_ass_path: Optional[str] = None,
    speaker_face_track: Optional[List[Dict[str, Any]]] = None,
    apply_speaker_crop: bool = False,
    guitar_solo_windows: Optional[List[Dict[str, Any]]] = None,
    debug_dump: Optional[Dict[str, Any]] = None,
) -> Optional[str]:

    quality = post_cfg.get("quality", {}) or {}
    fade = post_cfg.get("fade", {}) or {}
    highlight = post_cfg.get("highlight", {}) or {}
    captions = post_cfg.get("captions", {}) or {}
    burn_cfg = (captions.get("burn_in") or {})
    border = post_cfg.get("border", {}) or {}
    solo_cfg = post_cfg.get("guitar_solo_overlay", {}) or {}

    chain: List[str] = []
    graph_parts: List[str] = []

    if apply_speaker_crop and speaker_face_track:
        sf_cfg = (post_cfg.get("speaker_focus") or {})
        track_cfg = (sf_cfg.get("track") or {})
        ema_alpha = float(track_cfg.get("ema_alpha", 0.25))
        max_points = int(track_cfg.get("max_points", 18))
        max_delta_per_s = float(track_cfg.get("max_delta_per_s", 0.35))

        xexpr = build_speaker_crop_x_expr(
            speaker_face_track,
            ema_alpha=ema_alpha,
            max_points=max_points,
            max_delta_per_s=max_delta_per_s,
        )
        if xexpr:
            out_w = "ih*9/16"
            chain.append(
                f"crop=w='if(gt(iw/ih,9/16),{out_w},iw)'"
                f":h='if(gt(iw/ih,9/16),ih,ih)'"
                f":x='if(gt(iw/ih,9/16),{xexpr},0)'"
                f":y=0"
            )

    if quality.get("enabled", True):
        den = quality.get("denoise", {}) or {}
        if den.get("enabled", True):
            chain.append(f"hqdn3d={str(den.get('params','1.5:1.2:6:6'))}")

        eq = quality.get("eq", {}) or {}
        if eq.get("enabled", False):
            contrast = float(eq.get("contrast", 1.0))
            brightness = float(eq.get("brightness", 0.0))
            saturation = float(eq.get("saturation", 1.0))
            gamma = float(eq.get("gamma", 1.0))
            chain.append(f"eq=contrast={contrast}:brightness={brightness}:saturation={saturation}:gamma={gamma}")

        sh = quality.get("sharpen", {}) or {}
        if sh.get("enabled", True):
            chain.append(f"unsharp={str(sh.get('params','5:5:0.60'))}")

    if fade.get("enabled", True) and clip_duration_s and clip_duration_s > 0.1:
        d = float(fade.get("duration_s", 0.35))
        d = max(0.05, min(d, float(clip_duration_s) / 3.0))
        chain.append(f"fade=t=in:st=0:d={_fmt(d)}:c=black")
        out_start = max(0.0, float(clip_duration_s) - d)
        chain.append(f"fade=t=out:st={_fmt(out_start)}:d={_fmt(d)}:c=black")

    solo_enable = None
    if bool(solo_cfg.get("enabled", True)):
        sw = _coalesce_windows(guitar_solo_windows or [], min_len=float(solo_cfg.get("min_window_s", 0.40)))
        solo_enable = _build_enable_expr(sw)

    def _append_solo(filters: List[str]) -> None:
        if not solo_enable:
            return
        text = str(solo_cfg.get("text", "GUITAR SOLO"))
        bar_h = float(solo_cfg.get("bar_height_ratio", 0.12))
        bar_color = str(solo_cfg.get("bar_color", "black@0.35"))
        fs = int(solo_cfg.get("font_size", 42))
        fc = str(solo_cfg.get("font_color", "white@0.95"))
        borderw = int(solo_cfg.get("text_borderw", 2))
        bcol = str(solo_cfg.get("text_bordercolor", "black@0.55"))

        filters.append(
            "drawbox="
            f"x=0:y=ih-(ih*{_fmt(bar_h)}):w=iw:h=ih*{_fmt(bar_h)}:"
            f"color={bar_color}:t=fill:enable='{solo_enable}'"
        )
        safe_txt = text.replace("'", "\\'")
        filters.append(
            "drawtext="
            f"text='{safe_txt}':"
            "x=(w-text_w)/2:"
            f"y=h-(h*{_fmt(bar_h)})+(h*{_fmt(bar_h)})*0.20:"
            f"fontsize={fs}:fontcolor={fc}:"
            f"borderw={borderw}:bordercolor={bcol}:"
            f"enable='{solo_enable}'"
        )

    def _append_subtitles(filters: List[str]) -> None:
        if burn_in_srt_path and burn_cfg.get("enabled", True):
            style = str(burn_cfg.get("force_style", ""))
            srt_esc = _escape_subtitles_path(burn_in_srt_path)
            filters.append(f"subtitles='{srt_esc}'" + (f":force_style='{style}'" if style else ""))
        if tab_ass_path:
            ass_esc = _escape_subtitles_path(tab_ass_path)
            filters.append(f"subtitles='{ass_esc}'")

    def _append_border(filters: List[str]) -> None:
        if border.get("enabled", True):
            edge_margin_ratio = float(border.get("edge_margin_ratio", 0.03))
            thickness = int(border.get("box_thickness", 12))
            color = str(border.get("box_color", "white@0.18"))
            margin_expr = f"min(iw\\,ih)*{edge_margin_ratio}"
            filters.append(
                f"drawbox=x={margin_expr}:y={margin_expr}:w=iw-2*({margin_expr}):h=ih-2*({margin_expr}):color={color}:t={thickness}"
            )

    highlight_used = False
    enable_expr = None
    if highlight.get("enabled", True):
        glow = (highlight.get("glow", {}) or {})
        if glow.get("enabled", True):
            windows = _coalesce_windows(active_windows or [], min_len=float(highlight.get("min_window_s", 0.35)))
            enable_expr = _build_enable_expr(windows)
            if enable_expr:
                highlight_used = True
                sigma = float(glow.get("sigma", 1.3))
                gamma = float(glow.get("gamma", 1.0))
                bright = float(glow.get("brightness", 0.02))
                opacity = float(glow.get("opacity", 0.18))
                opacity = max(0.0, min(0.5, opacity))

                desat = bool(glow.get("desaturate", True))
                desat_f = "hue=s=0," if desat else ""

                base_chain = ",".join(chain) if chain else "null"
                graph_parts.append(f"{base_chain}[vin]")
                graph_parts.append(
                    "[vin]split=2[base][gl];"
                    f"[gl]{desat_f}gblur=sigma={_fmt(sigma)}:steps=1,eq=gamma={_fmt(gamma)}:brightness={_fmt(bright)},"
                    f"format=rgba,colorchannelmixer=aa={_fmt(opacity)}[gl2];"
                    f"[base][gl2]blend=all_mode=screen:enable='{enable_expr}'[vhl]"
                )

    if not highlight_used:
        _append_subtitles(chain)
        _append_solo(chain)
        _append_border(chain)
        if debug_dump is not None:
            debug_dump.update({"mode": "simple", "vf": ",".join(chain) if chain else None, "solo_enable": solo_enable, "tab_ass_path": tab_ass_path})
        return ",".join(chain) if chain else None

    tail: List[str] = []
    _append_subtitles(tail)
    _append_solo(tail)
    _append_border(tail)

    graph_parts.append(f"[vhl]{','.join(tail) if tail else 'null'}[vout]")
    fc = ";".join(p.strip() for p in graph_parts if p.strip()) or None
    if debug_dump is not None:
        debug_dump.update({"mode": "complex", "filter_complex": fc, "solo_enable": solo_enable, "tab_ass_path": tab_ass_path})
    return fc
