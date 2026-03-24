from __future__ import annotations

import json
import platform
from pathlib import Path

import psutil


def log_hardware(path: str | Path) -> None:
    payload = {
        "cpu": platform.processor() or platform.machine(),
        "cores": psutil.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / 1e9, 2),
        "os": platform.system(),
        "os_release": platform.release(),
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
