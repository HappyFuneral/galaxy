# V1.8 – Guitar-focused TAB generation (V1: audio-only)

## Files added
- `backend/pipeline/guitar_focus.py`
- `backend/pipeline/tab_generator.py`
- `config/tab.yaml` (example config to merge into your config system)

## Integration (drop-in)
In `backend/pipeline/pipeline.py`, inside the export loop for each selected clip:

```py
speech_feat = vctx.speech.extract(clip.segment)
music_feat  = vctx.music.extract(clip.segment)
visual_feat = vctx.visual.extract(clip.segment)

from backend.pipeline.guitar_focus import detect_guitar_focus
gf = detect_guitar_focus(music_feat=music_feat, visual_feat=visual_feat, speech_feat=speech_feat, cfg=cfg)

tab_out = None
if (cfg.get("tab") or {}).get("enabled", False) and gf.is_guitar_focused:
    from backend.pipeline.tab_generator import generate_tab_audio_only_for_segment
    tab_cfg = ((cfg.get("tab") or {}).get("audio_only") or {})
    stem = f"clip_{i:02d}_{platform}"
    tab_out = generate_tab_audio_only_for_segment(
        input_video=video_path,
        start=clip.segment.start,
        end=clip.segment.end,
        out_dir=export_dir,
        stem=stem,
        cfg=tab_cfg,
    )

exports.append({
    ...
    "guitar_focus": {"is": gf.is_guitar_focused, "confidence": gf.confidence, "reasons": gf.reasons},
    "tab": tab_out,
})
```

## Output
- `<stem>.tab.txt` – quick readable tab summary with timestamps
- `<stem>.tab.json` – structured note events + mapped tab notes

## Notes
- Works best for lead/monophonic guitar lines.
- Chords/polyphony will often produce lower confidence or fewer notes (expected).
