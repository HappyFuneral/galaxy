
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json
import math

def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)

@dataclass
class GlobalStats:
    stats: Dict[str, Dict[str, float]]

    @staticmethod
    def load(path: Path) -> "GlobalStats":
        if not path.exists():
            return GlobalStats(stats={})
        return GlobalStats(stats=json.loads(path.read_text(encoding="utf-8")))

    def mean_std(self, key: str) -> tuple[float, float]:
        d = self.stats.get(key, {})
        mean = float(d.get("mean", 0.0))
        std = float(d.get("std", 1.0)) or 1.0
        return mean, std

    def p90(self, key: str) -> float:
        d = self.stats.get(key, {})
        return float(d.get("p90", 1.0)) or 1.0

class GlobalStatsNormalizer:
    def __init__(self, normalization_cfg: Dict[str, Any], global_stats_path: Optional[str] = "./data/global_stats.json"):
        self.methods: Dict[str, str] = dict(normalization_cfg.get("methods", {}))
        self.global_stats = GlobalStats.load(Path(global_stats_path)) if global_stats_path else GlobalStats(stats={})

    def _apply(self, key: str, value: float, video_percentiles: Optional[Dict[str, float]] = None) -> float:
        method = self.methods.get(key, "passthrough")

        if method == "passthrough":
            return float(value)

        if method == "zscore_sigmoid":
            mean, std = self.global_stats.mean_std(key)
            z = (float(value) - mean) / std
            return _clip(_sigmoid(z))

        if method == "log_percentile":
            p90 = self.global_stats.p90(key)
            x = float(value) / p90
            return _clip(math.log1p(max(0.0, x)) / math.log1p(2.0))

        if method == "video_percentile":
            p = 1.0
            if video_percentiles and key in video_percentiles:
                p = float(video_percentiles[key]) or 1.0
            return _clip(float(value) / p)

        return float(value)

    def normalize(self, raw_features: Dict[str, Dict[str, Any]], video_percentiles: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for domain, feats in raw_features.items():
            dom_out: Dict[str, Any] = {}
            for k, v in feats.items():
                if isinstance(v, list):
                    dom_out[k] = v
                elif isinstance(v, (int, float)):
                    dom_out[k] = self._apply(k, float(v), video_percentiles=video_percentiles)
                else:
                    dom_out[k] = v
            out[domain] = dom_out
        return out
