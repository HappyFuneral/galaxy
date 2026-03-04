from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import subprocess
import tempfile


def _extract_wav_16k_mono(video_path: Path, start: float, end: float, out_wav: Path) -> None:
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", str(start),
        "-to", str(end),
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-f", "wav",
        str(out_wav),
    ]
    subprocess.check_call(cmd)


def transcribe_clip_whisper(video_path: Path, start: float, end: float, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    whisper_cfg = (cfg.get("speech", {}) or {}).get("whisper", {}) or {}
    model = whisper_cfg.get("model", "base")
    device = whisper_cfg.get("device", "cpu")
    compute_type = whisper_cfg.get("compute_type", "int8")
    beam_size = int(whisper_cfg.get("beam_size", 1))
    vad_filter = bool(whisper_cfg.get("vad_filter", True))

    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "clip.wav"
        _extract_wav_16k_mono(video_path, start, end, wav)

        wm = WhisperModel(model, device=device, compute_type=compute_type)
        segments, _info = wm.transcribe(str(wav), beam_size=beam_size, vad_filter=vad_filter)

        out = []
        for s in segments:
            text = (s.text or "").strip()
            if text:
                out.append({"start": float(s.start), "end": float(s.end), "text": text})
        return out
