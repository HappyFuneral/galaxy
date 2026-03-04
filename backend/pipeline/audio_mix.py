from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import subprocess
import shlex

@dataclass(frozen=True)
class MixDecision:
    use_bgm: bool
    reason: str

def decide_bgm_auto(speech_ratio: float, music_activity: float, cfg: dict) -> MixDecision:
    bgm_cfg = (cfg.get("bgm") or {})
    gate = (cfg.get("guitar_gate") or {})

    if not bool(bgm_cfg.get("enabled", True)):
        return MixDecision(False, "bgm disabled")

    mode = str(bgm_cfg.get("mode", "auto"))
    if mode == "never":
        return MixDecision(False, "bgm mode=never")
    if mode == "always":
        return MixDecision(True, "bgm mode=always")

    if speech_ratio < 0.20:
        return MixDecision(False, "low speech_ratio")

    if bool(gate.get("enabled", True)):
        thr = float(gate.get("threshold", 0.55))
        if music_activity >= thr:
            return MixDecision(False, f"music_activity high ({music_activity:.2f}>= {thr:.2f}) => bgm off")

    return MixDecision(True, "speech present and no strong music => bgm on")

def _dump_debug_files(debug_dir: Path, stem: str, cmd: List[str], vf: Optional[str], fc: Optional[str],
                     result: subprocess.CompletedProcess, meta: Optional[str] = None) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / f"{stem}.cmd.txt").write_text(" \\\n  ".join(shlex.quote(c) for c in cmd), encoding="utf-8")
    (debug_dir / f"{stem}.vf.txt").write_text(vf or "", encoding="utf-8")
    (debug_dir / f"{stem}.fc.txt").write_text(fc or "", encoding="utf-8")
    (debug_dir / f"{stem}.stderr.txt").write_text((result.stderr or ""), encoding="utf-8")
    if meta:
        (debug_dir / f"{stem}.meta.txt").write_text(meta, encoding="utf-8")

def _needs_filter_complex(vf: Optional[str]) -> bool:
    if not vf:
        return False
    return (";" in vf) or ("[vout]" in vf) or ("split=" in vf)

def export_clip_with_optional_bgm(
    input_video: Path,
    output_video: Path,
    start: float,
    end: float,
    vf: Optional[str],
    bgm_path: Optional[Path],
    mix_cfg: dict,
    use_bgm: bool,
    *,
    # --- COMPAT: older pipeline calls these ---
    burn_in: bool = False,
    srt_path: Optional[Path] = None,
    speaker_face_track: Optional[list] = None,
    apply_speaker_crop: bool = False,
    # ----------------------------------------
    debug_dir: Optional[Path] = None,
    debug_stem: Optional[str] = None,
) -> None:
    """
    V1.6 compat exporter.

    Notes:
    - burn_in/srt_path are kept for backward compatibility. Burn-in is already handled inside vf
      (postprocess.build_vf_filtergraph) when you pass burn_in_srt_path there.
    - speaker_face_track/apply_speaker_crop are also handled upstream in vf; accepted here to avoid
      breaking older call sites.
    """
    duration = max(0.0, end - start)
    if duration <= 0:
        raise ValueError("Invalid clip duration")

    bgm_cfg = (mix_cfg.get("bgm") or {})
    base_gain_db = float(bgm_cfg.get("base_gain_db", -18))
    duck = (bgm_cfg.get("ducking") or {})
    duck_enabled = bool(duck.get("enabled", True))

    needs_v_complex = _needs_filter_complex(vf)
    has_bgm = bool(use_bgm and bgm_path and bgm_path.exists())

    cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(input_video)]
    if has_bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm_path)]

    fc_parts: List[str] = []
    fc: Optional[str] = None

    v_map = "0:v:0"
    if needs_v_complex and vf:
        # vf is a subgraph that expects [0:v] prefix and outputs [vout]
        fc_parts.append(f"[0:v]{vf}")
        v_map = "[vout]"

    a_map = "0:a:0?"
    if has_bgm:
        if duck_enabled:
            a_fc = (
                f"[1:a]volume={base_gain_db}dB[bgm];"
                f"[bgm][0:a]sidechaincompress=threshold=0.02:ratio=10:attack=20:release=250:makeup=1[bgmduck];"
                f"[0:a][bgmduck]amix=inputs=2:normalize=0[mixa]"
            )
        else:
            a_fc = f"[1:a]volume={base_gain_db}dB[bgm];[0:a][bgm]amix=inputs=2:normalize=0[mixa]"
        fc_parts.append(a_fc)
        a_map = "[mixa]"

    if fc_parts:
        fc = ";".join(p.strip() for p in fc_parts if p.strip())
        cmd += ["-filter_complex", fc, "-map", v_map, "-map", a_map]
        if has_bgm:
            cmd += ["-shortest"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0?"]

    if (not needs_v_complex) and vf:
        cmd += ["-vf", vf]

    preset = str(bgm_cfg.get("ffmpeg_preset", "veryfast"))
    crf = str(bgm_cfg.get("ffmpeg_crf", "20"))

    cmd += [
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(output_video),
    ]

    def run_once(run_cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(run_cmd, capture_output=True, text=True)

    p = run_once(cmd)

    if debug_dir is not None:
        stem = debug_stem or output_video.stem
        meta = (
            f"needs_v_complex={needs_v_complex}\n"
            f"use_bgm={use_bgm}\n"
            f"has_bgm={has_bgm}\n"
            f"ducking_enabled={duck_enabled}\n"
            f"burn_in_kwarg={burn_in}\n"
            f"srt_path_kwarg={str(srt_path) if srt_path else None}\n"
        )
        _dump_debug_files(debug_dir, stem, cmd, vf, fc, p, meta=meta)

    if p.returncode == 0:
        return

    err = (p.stderr or "").strip()

    # fallback if sidechaincompress missing
    if has_bgm and duck_enabled and ("sidechaincompress" in err or "No such filter" in err):
        fc_parts2: List[str] = []
        v_map2 = "0:v:0"
        if needs_v_complex and vf:
            fc_parts2.append(f"[0:v]{vf}")
            v_map2 = "[vout]"
        a_fc2 = f"[1:a]volume={base_gain_db}dB[bgm];[0:a][bgm]amix=inputs=2:normalize=0[mixa]"
        fc_parts2.append(a_fc2)
        fc2 = ";".join(p.strip() for p in fc_parts2 if p.strip())

        cmd2 = ["ffmpeg", "-hide_banner", "-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
                "-i", str(input_video), "-stream_loop", "-1", "-i", str(bgm_path),
                "-filter_complex", fc2, "-map", v_map2, "-map", "[mixa]", "-shortest"]

        if (not needs_v_complex) and vf:
            cmd2 += ["-vf", vf]

        cmd2 += ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output_video)]

        p2 = run_once(cmd2)

        if debug_dir is not None:
            stem = (debug_stem or output_video.stem) + ".fallback"
            _dump_debug_files(debug_dir, stem, cmd2, vf, fc2, p2, meta="fallback_reason=sidechaincompress unsupported\n")

        if p2.returncode == 0:
            return
        raise RuntimeError((p2.stderr or "").strip() or "ffmpeg export failed (fallback)")

    raise RuntimeError(err or "ffmpeg export failed")
