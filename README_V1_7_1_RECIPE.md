# V1.7.1 – Recipe autosave + preview file serving

## What changed
1) On HQ export, every clip writes a recipe file next to the mp4:
   exports/<job_id>/clip_01_tiktok.recipe.json

2) Exports API now serves preview mp4 files:
   GET /exports/{job_id}/previews/{name}

3) Preview endpoint now returns:
   - preview_url: "/exports/{job_id}/previews/<file>.mp4"

## Why
Mobile needs a stable "render recipe" to tweak sliders and request preview/re-export.
