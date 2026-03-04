from __future__ import annotations
from typing import Any, Dict

_CFG: Dict[str, Any] = {}

def set_cfg(cfg: Dict[str, Any]) -> None:
    global _CFG
    _CFG = cfg

def get_cfg() -> Dict[str, Any]:
    return _CFG
