
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import yaml

def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def load_all_configs(config_dir: Path) -> Dict[str, Any]:
    return {
        "postprocess": load_yaml(config_dir / "postprocess.yaml"),
        "performance": load_yaml(config_dir / "performance.yaml"),
        "platforms": load_yaml(config_dir / "platforms.yaml"),
        "speech": load_yaml(config_dir / "speech.yaml"),
        "audio_mix": load_yaml(config_dir / "audio_mix.yaml"),
        "scoring": load_yaml(config_dir / "scoring.yaml"),
        "thresholds": load_yaml(config_dir / "thresholds.yaml"),
        "platform_profiles": load_yaml(config_dir / "platform_profiles.yaml"),
        "normalization": load_yaml(config_dir / "normalization.yaml"),
        "learning": load_yaml(config_dir / "learning.yaml"),
        "tab": load_yaml(config_dir / "tab.yaml"),
        "guitar_solo_overlay": load_yaml(config_dir / "postprocess_guitar_solo_overlay_snippet.yaml"),
        "tab_overlay": load_yaml(config_dir / "tab_overlay.yaml")
    }
