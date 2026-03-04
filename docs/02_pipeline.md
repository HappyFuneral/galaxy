
# Pipeline

1) Upload -> video_id
2) Create job -> job_id
3) Pipeline:
   - ffprobe duration
   - generate segments (window/step)
   - build per-video ctx (audio/visual analyzers)
   - evaluate each segment:
       music + visual -> emotion
       normalize -> score -> platform -> final -> decision
   - select top clips
     - if none >= min_score -> fallback top N
   - export (optional) via ffmpeg
4) Result JSON:
   - candidates (all)
   - selected (top)
   - exports (download URLs added by API layer)
