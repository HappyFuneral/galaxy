# V1.8.2 – TAB overlay (ASS) + highlight purple fix

## Why you see SOLO banner but no tabs
Right now your SOLO overlay is just a banner. To show **actual tab numbers** we render an ASS subtitle that updates every `step_s`.
Your tab json contains `tab_notes`, so we can build an overlay from that. Example file: clip_01_tiktok.tab.json fileciteturn1file0

## Add TAB overlay generation in pipeline (export loop)
After `tab_json` is known:

```py
from backend.pipeline.tab_ass import write_tab_ass

tab_ass = None
tab_overlay_cfg = (cfg.get("tab_overlay") or {}).get("tab_overlay") or (cfg.get("tab_overlay") or {})
# simplest: cfg['tab_overlay'] = {...}

if tab_json and (tab_overlay_cfg.get("enabled", True)):
    tab_ass_path = export_dir / f"{stem}.tab.ass"
    tab_ass = write_tab_ass(
        Path(tab_json),
        tab_ass_path,
        clip_duration_s=float(clip.segment.duration),
        cfg=tab_overlay_cfg,
    )
```

Then pass into postprocess:

```py
vf = build_vf_filtergraph(
    post_cfg,
    active_windows=clip.visual_active_windows,
    clip_duration_s=clip.segment.duration,
    burn_in_srt_path=burn_in_srt,
    tab_ass_path=str(tab_ass) if tab_ass else None,
    guitar_solo_windows=solo_windows,
)
```

## Purple tint fix (highlight)
In postprocess highlight path we add `hue=s=0` on the glow layer by default.
Config:

```yaml
highlight:
  glow:
    desaturate: true
```

## Missing notes
Your tab notes include many events with conf around ~0.45-0.55 fileciteturn1file0.
If you filter too hard, you'll drop notes. Try `min_conf: 0.35` in tab overlay cfg.
For better pitch detection: add band-pass and raise analysis FPS in the tab generator (next patch).
