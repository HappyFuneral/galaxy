from __future__ import annotations

import json
import math
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Standard tuning (Hz) for strings:
# 0=low E2, 1=A2, 2=D3, 3=G3, 4=B3, 5=high E4
_STD_TUNING_HZ = [82.4069, 110.0, 146.8324, 195.9977, 246.9417, 329.6276]


def _hz_to_midi(f: float) -> int:
    if f <= 0:
        return 0
    return int(round(69 + 12 * math.log2(f / 440.0)))


def _midi_to_hz(m: int) -> float:
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


@dataclass(frozen=True)
class TabGenCfg:
    # audio extraction
    sr: int = 22050
    # analysis
    hop_s: float = 0.02     # 50 fps
    win_s: float = 0.04     # 40 ms
    fmin: float = 80.0
    fmax: float = 1400.0
    hps_harmonics: int = 4
    # confidence / voicing
    min_rms: float = 0.010
    min_conf: float = 0.30
    # note segmentation
    max_semitone_jump: float = 1.5
    min_note_s: float = 0.06
    # mapping
    max_fret: int = 24
    prefer_high_strings: bool = True


def _run(cmd: List[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "").strip() or "ffmpeg failed")


def _extract_audio_wav(
    input_video: Path,
    start: float,
    end: float,
    wav_out: Path,
    *,
    sr: int,
    highpass_hz: float = 80.0,
    lowpass_hz: float = 1800.0,
    comp: bool = True,
) -> None:
    """Extract mono WAV with mild filtering & compression to improve pitch detection."""
    dur = max(0.0, float(end - start))
    if dur <= 0:
        raise ValueError("Invalid duration for audio extract")

    af = [f"highpass=f={highpass_hz}", f"lowpass=f={lowpass_hz}"]
    if comp:
        af.append("acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=2")
    af.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    af_str = ",".join(af)

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", str(input_video),
        "-t", f"{dur:.3f}",
        "-vn",
        "-ac", "1",
        "-ar", str(int(sr)),
        "-af", af_str,
        str(wav_out),
    ]
    _run(cmd)


def _read_wav_mono(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        ch = wf.getnchannels()
        sr = wf.getframerate()
        n = wf.getnframes()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(n)

    if sampwidth == 2:
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        a = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def _hann(n: int) -> np.ndarray:
    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / max(1, n - 1))


def _hps_pitch(frame: np.ndarray, sr: int, fmin: float, fmax: float, harmonics: int) -> Tuple[float, float]:
    """Harmonic Product Spectrum pitch estimate. Returns (freq_hz, conf)."""
    n = len(frame)
    if n < 16:
        return 0.0, 0.0

    win = _hann(n)
    x = frame * win
    spec = np.fft.rfft(x)
    mag = np.abs(spec).astype(np.float32) + 1e-8

    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    lo = int(np.searchsorted(freqs, fmin))
    hi = int(np.searchsorted(freqs, fmax))
    lo = max(1, lo)
    hi = max(lo + 2, min(len(mag) - 1, hi))

    band = mag[lo:hi].copy()
    if band.size < 8:
        return 0.0, 0.0

    hps = band.copy()
    for h in range(2, max(2, harmonics + 1)):
        dec = band[::h]
        hps[: dec.size] *= dec

    k = int(np.argmax(hps))
    peak = float(hps[k])
    med = float(np.median(hps)) + 1e-9
    conf = max(0.0, min(1.0, (peak / med - 1.0) / 8.0))
    freq = float(freqs[lo + k])
    return freq, conf


def _segment_notes(
    times: np.ndarray,
    freqs: np.ndarray,
    confs: np.ndarray,
    *,
    min_conf: float,
    max_semitone_jump: float,
    min_note_s: float,
) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    cur: Dict[str, Any] | None = None

    def close(t_end: float):
        nonlocal cur
        if not cur:
            return
        dur = float(t_end - cur["t_start"])
        if dur >= min_note_s:
            cur["t_end"] = float(t_end)
            notes.append(cur)
        cur = None

    for t, f, c in zip(times, freqs, confs):
        if c < min_conf or f <= 0:
            if cur:
                close(float(t))
            continue

        m = _hz_to_midi(float(f))
        if cur is None:
            cur = {"t_start": float(t), "t_end": float(t), "midi": int(m), "freq_hz": float(f), "conf": float(c)}
            continue

        dm = abs(int(m) - int(cur["midi"]))
        if dm > max_semitone_jump:
            close(float(t))
            cur = {"t_start": float(t), "t_end": float(t), "midi": int(m), "freq_hz": float(f), "conf": float(c)}
        else:
            cur["t_end"] = float(t)
            cur["conf"] = float(max(cur["conf"], c))
            cur["freq_hz"] = float((cur["freq_hz"] * 0.7) + (f * 0.3))
            cur["midi"] = int(round((cur["midi"] * 0.7) + (m * 0.3)))

    if cur is not None and len(times) > 0:
        step = float(times[1] - times[0]) if len(times) > 1 else 0.02
        close(float(times[-1] + step))

    return notes


def _map_midi_to_string_fret(midi: int, *, max_fret: int, prefer_high_strings: bool) -> Tuple[int, int]:
    best = None
    for si, open_hz in enumerate(_STD_TUNING_HZ):
        open_m = _hz_to_midi(open_hz)
        fret = midi - open_m
        if 0 <= fret <= max_fret:
            pref = (5 - si) * 0.15 if prefer_high_strings else 0.0
            cost = float(fret) + float(pref)
            cand = (cost, si, fret)
            if best is None or cand[0] < best[0]:
                best = cand
    if best is None:
        diffs = [(abs(midi - _hz_to_midi(h)), i) for i, h in enumerate(_STD_TUNING_HZ)]
        _, si = sorted(diffs)[0]
        open_m = _hz_to_midi(_STD_TUNING_HZ[si])
        fret = max(0, min(max_fret, midi - open_m))
        return int(si), int(fret)
    return int(best[1]), int(best[2])


def generate_tab_audio_only_for_segment(
    *,
    input_video: Path,
    start: float,
    end: float,
    out_dir: Path,
    stem: str,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """V2 pitch-based TAB json generator (audio-only)."""
    c = TabGenCfg(
        sr=int(cfg.get("sr", 22050)),
        hop_s=float(cfg.get("hop_s", 0.02)),
        win_s=float(cfg.get("win_s", 0.04)),
        fmin=float(cfg.get("fmin", 80.0)),
        fmax=float(cfg.get("fmax", 1400.0)),
        hps_harmonics=int(cfg.get("hps_harmonics", 4)),
        min_rms=float(cfg.get("min_rms", 0.010)),
        min_conf=float(cfg.get("min_conf", 0.30)),
        max_semitone_jump=float(cfg.get("max_semitone_jump", 1.5)),
        min_note_s=float(cfg.get("min_note_s", 0.06)),
        max_fret=int(cfg.get("max_fret", 24)),
        prefer_high_strings=bool(cfg.get("prefer_high_strings", True)),
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.tab.json"

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        wav_path = td / "seg.wav"
        _extract_audio_wav(
            input_video, start, end, wav_path,
            sr=c.sr,
            highpass_hz=float(cfg.get("highpass_hz", 80.0)),
            lowpass_hz=float(cfg.get("lowpass_hz", 1800.0)),
            comp=bool(cfg.get("compress", True)),
        )
        sig, sr = _read_wav_mono(wav_path)

    hop = max(1, int(round(c.hop_s * sr)))
    win = max(hop + 8, int(round(c.win_s * sr)))

    if len(sig) < win:
        sig = np.pad(sig, (0, win - len(sig)))

    n_frames = 1 + (len(sig) - win) // hop
    times = (np.arange(n_frames) * hop) / float(sr)

    freqs = np.zeros(n_frames, dtype=np.float32)
    confs = np.zeros(n_frames, dtype=np.float32)

    for i in range(n_frames):
        fr = sig[i * hop : i * hop + win]
        rms = float(np.sqrt(np.mean(fr * fr)) + 1e-12)
        if rms < c.min_rms:
            continue
        f, conf = _hps_pitch(fr, sr, c.fmin, c.fmax, c.hps_harmonics)
        freqs[i] = float(f)
        confs[i] = float(conf)

    # EMA smoothing in MIDI space for voiced frames
    voiced = confs >= c.min_conf
    midi = np.zeros_like(freqs, dtype=np.float32)
    if np.any(voiced):
        midi[voiced] = np.array([_hz_to_midi(float(f)) for f in freqs[voiced]], dtype=np.float32)

    alpha = float(cfg.get("ema_alpha", 0.25))
    last = None
    for i in range(n_frames):
        if not voiced[i]:
            continue
        if last is None:
            last = midi[i]
        else:
            last = (1 - alpha) * last + alpha * midi[i]
        midi[i] = last
        freqs[i] = float(_midi_to_hz(int(round(last))))

    notes = _segment_notes(
        times, freqs, confs,
        min_conf=c.min_conf,
        max_semitone_jump=c.max_semitone_jump,
        min_note_s=c.min_note_s,
    )

    tab_notes: List[Dict[str, Any]] = []
    for n in notes:
        si, fret = _map_midi_to_string_fret(int(n["midi"]), max_fret=c.max_fret, prefer_high_strings=c.prefer_high_strings)
        tab_notes.append({
            "t_start": float(n["t_start"]),
            "t_end": float(n["t_end"]),
            "freq_hz": float(n["freq_hz"]),
            "midi": int(n["midi"]),
            "conf": float(n["conf"]),
            "string_index": int(si),
            "fret": int(fret),
        })

    payload = {
        "version": "v2_hps_filtered",
        "segment": {"start": float(start), "end": float(end)},
        "config": {
            "sr": c.sr, "hop_s": c.hop_s, "win_s": c.win_s,
            "fmin": c.fmin, "fmax": c.fmax, "min_conf": c.min_conf,
            "min_rms": c.min_rms, "hps_harmonics": c.hps_harmonics,
        },
        "tab_notes": tab_notes,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "exports": {"files": {"json": str(json_path)}},
        "stats": {"frames": int(n_frames), "notes": int(len(tab_notes))},
    }
