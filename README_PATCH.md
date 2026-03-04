# Patch: highlight needs -filter_complex

Your error:
  Simple filtergraph ... expected 1 input/1 output ... had 3/3 ... use -filter_complex

Cause:
- Highlight uses split+blend which is a complex graph.
- It cannot be passed via -vf (simple graph).

Fix:
- backend/pipeline/postprocess.py returns a complex subgraph (when highlight active) that outputs [vout]
- backend/pipeline/audio_mix.py detects this and uses ONE -filter_complex combining:
  - video graph: [0:v]{vf} -> [vout]
  - audio mix graph (optional): -> [mixa]
  Then maps [vout] and audio.

Apply:
- unzip into repo root, overwrite these files, restart backend.
