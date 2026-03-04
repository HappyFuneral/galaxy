
from __future__ import annotations
from typing import List
from backend.engine.models import Segment

def generate_sliding_segments(duration_s: float, window_s: float = 45.0, step_s: float = 15.0, min_duration_s: float = 20.0) -> List[Segment]:
    if duration_s <= 0:
        return []
    if duration_s < window_s:
        return [Segment(0.0, duration_s)] if duration_s >= min_duration_s else []
    segs=[]
    t=0.0
    while t + window_s <= duration_s + 1e-6:
        segs.append(Segment(t, min(t+window_s, duration_s)))
        t += step_s
    if segs and segs[-1].end < duration_s:
        segs.append(Segment(max(0.0, duration_s-window_s), duration_s))
    uniq=[]
    seen=set()
    for s in segs:
        key=(round(s.start,2), round(s.end,2))
        if key not in seen and s.duration >= min_duration_s:
            seen.add(key); uniq.append(s)
    return uniq
