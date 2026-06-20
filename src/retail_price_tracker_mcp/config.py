from __future__ import annotations

import os
from pathlib import Path


def default_db_path() -> Path:
    configured = os.getenv("PRICE_TRACKER_DB")
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / "tracker.db"
