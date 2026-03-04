# V1.5-perf patch (konkrét fájlok)

## Lényege
- **Egyszer** dekódolunk (cache) videót: vizuál/audio/speech idősorok.
- Szegmens pontozás: **csak cache query** (O(1)).
- Whisper (faster-whisper) **csak a kiválasztott klippekre** fut (opcionális).

## Config példa
```yaml
performance:
  visual_sample_fps: 0.5
  visual_max_width: 256
  audio_hop_s: 0.25
  speech_vad_only: true
  whisper_on_selected_only: true
  max_whisper_clips: 2
```

## Whisper
- `speech_vad_only=true`: nincs whisper → nagyon gyors.
- Ha kell felirat:
  - `speech_vad_only=false`
  - `speech.whisper.compute_type=int8` CPU-hoz gyors

## Integráció
Ezek a fájlok felülírják / kiegészítik:
- `backend/engine/context.py`
- `backend/engine/runner.py`
- `backend/pipeline/pipeline.py`

És hozzáadnak újakat:
- `backend/analyzers/cache/*`
- `backend/analyzers/cached_analyzers.py`
- `backend/pipeline/speech_whisper.py`
