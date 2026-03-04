
# AI Video Editor (Decision-first) – Complete V1 Skeleton

This repo is a **repo-ready** skeleton for an AI-assisted short-form clip generator.
Primary use case: **guitarist / musician content** (10–20 min -> 30–60s shorts).

## What works now
- Upload video
- Start a background job (status + progress)
- Sliding-window segment generation
- Feature extraction:
  - audio via ffmpeg PCM + RMS/onset proxy (V1 real-ish)
  - visual via MediaPipe hands+face + motion proxy
  - emotion from music+visual (V1)
- Normalization + scoring (config-driven)
- Platform evaluator (TikTok/Shorts/Reels profiles)
- Selection (threshold + **fallback**)
- Optional ffmpeg export of selected clips + download URLs
- Minimal React frontend (polling + results + downloads)
- Pytest tests for core modules

## Run
```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend Swagger: http://localhost:8000/docs
