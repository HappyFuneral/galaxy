# AI Video Editor – V1.6

Focus: **performance + stability**, plus **speaker focus** and **ffmpeg debug dumps**.

## Included
- Backend (FastAPI) + Web frontend + Mobile (Expo) in `/mobile`
- Cache-based analyzers (visual/audio/speech) for speed
- `backend/engine/factory.py` to build DecisionEngine from config (with safe fallbacks)
- Speaker focus: face-center crop for speech clips
- Burn-in subtitles supported via `build_vf_filtergraph(... burn_in_srt_path=...)`
- Debug dumps in `exports/<job>/_debug_ffmpeg/`:
  - `*.cmd.txt` (full ffmpeg command)
  - `*.vf.txt` (video filtergraph)
  - `*.fc.txt` (audio filter_complex)
  - `*.stderr.txt` stderr output

## Recommended config
```yaml
performance:
  visual_sample_fps: 0.5
  visual_max_width: 256
  audio_hop_s: 0.25
  speech_vad_only: true
  whisper_on_selected_only: true
  max_whisper_clips: 2
postprocess:
  speaker_focus:
    track:
      sample_fps: 2.0
      max_width: 320
      min_conf: 0.5
```
