
# Normalization (V1)

We normalize features in two stages:

## 1) Video-level normalization
Make segments comparable within the same video.

Typical strategies:
- Robust scaling: (x - median) / IQR
- Percentile scaling: x / p90

## 2) Global normalization
Make comparisons stable across videos.
- z-score relative to global mean/std, then sigmoid to (0..1)
- percentile-based scaling

Global stats are stored in `backend/normalization/stats_store.py` (V1: JSON file).
Later can be updated from accepted clips (EMA).

All normalized features are clipped to [0,1].
