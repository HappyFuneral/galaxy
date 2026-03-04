# V1.7 Backend: exports + preview endpoints

New router: backend/api/routes/exports.py

Endpoints:
- GET   /exports?job_id=...
- GET   /exports/{job_id}/{export_id}/recipe
- PATCH /exports/{job_id}/{export_id}/recipe     body: { overrides: {...} }
- POST  /exports/{job_id}/{export_id}/preview    body: { seconds, size_w, size_h, overrides }

Integration (FastAPI main):
1) Ensure cfg is injectable as a dependency named `cfg`:
   - If you already do this, ignore deps.py.
2) Include router:

```py
from fastapi import Depends
from backend.api.deps import set_cfg, get_cfg
from backend.api.routes.exports import router as exports_router

set_cfg(cfg)  # after you load your YAMLs
app.include_router(exports_router, dependencies=[Depends(get_cfg)])
```

Recipe file expected:
- exports/<job_id>/<export_id>.recipe.json

Recipe minimal schema:
{
  "input_video": "uploads/....mp4",
  "platform": "tiktok",
  "segment": {"start": 15.0, "end": 60.0},
  "overrides": {"postprocess": {...}, "audio_mix": {...}, "active_windows": [...]},
  "bgm_path": "uploads/bgm.mp3",
  "use_bgm": true,
  "burn_in_srt_path": "exports/<job_id>/clip_01.srt",
  "speaker_face_track": [...],
  "apply_speaker_crop": true
}

Preview output:
- exports/<job_id>/previews/preview_<export_id>_<ts>.mp4
Debug dump:
- exports/<job_id>/previews/_debug_ffmpeg/*.cmd.txt, *.fc.txt, *.stderr.txt
