from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math

@dataclass(frozen=True)
class TimeSeries:
    """Uniformly-sampled time series."""
    t0: float
    dt: float
    values: List[float]

    def _idx_range(self, start: float, end: float) -> Tuple[int, int]:
        if end <= start:
            return (0, 0)
        i0 = int(max(0, (start - self.t0) / self.dt))
        i1 = int(min(len(self.values), math.ceil((end - self.t0) / self.dt)))
        return i0, i1

    def slice(self, start: float, end: float) -> List[float]:
        i0, i1 = self._idx_range(start, end)
        return self.values[i0:i1]

    def mean(self, start: float, end: float, default: float = 0.0) -> float:
        xs = self.slice(start, end)
        if not xs:
            return default
        return float(sum(xs) / len(xs))

    def max(self, start: float, end: float, default: float = 0.0) -> float:
        xs = self.slice(start, end)
        if not xs:
            return default
        return float(max(xs))

    def fraction_above(self, start: float, end: float, thr: float, default: float = 0.0) -> float:
        xs = self.slice(start, end)
        if not xs:
            return default
        c = sum(1 for v in xs if v >= thr)
        return float(c / len(xs))
