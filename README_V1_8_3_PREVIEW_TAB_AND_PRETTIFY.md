# V1.8.3 – Preview TAB overlay fix + better TAB overlay

## 1) Miért nem látszik preview-ben?
A preview render útvonal sokszor **kihagyja** a TAB overlay generálást (nem készül el a `.tab.ass`),
vagy nem adja át a `tab_ass_path` paramétert a `build_vf_filtergraph(...)`-nak.

## 2) Fix
Használd a helper-t a preview pipeline/endpoint kódjában:

```py
from backend.pipeline.preview_tab import maybe_build_tab_ass_for_preview

tab_ass = maybe_build_tab_ass_for_preview(
    tab_json=tab_json,
    out_dir=preview_dir,
    stem=stem,
    clip_duration_s=float(duration_s),
    cfg=cfg,
)

vf = build_vf_filtergraph(
    post_cfg,
    active_windows=active_windows,
    clip_duration_s=duration_s,
    tab_ass_path=str(tab_ass) if tab_ass else None,
    ...
)
```

## 3) TAB overlay finomítások
- több hang látszik: `min_conf` alapból 0.35
- `show_sustained=True`: a hang addig marad a tabon, amíg tart
- szebb: ASS `BorderStyle=3` (áttetsző doboz háttér a tab alatt)
