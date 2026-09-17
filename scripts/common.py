"""Shared helpers used by every fetch script."""
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return default
        return json.loads(content)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def load_watchlist():
    return load_json(CONFIG_DIR / "watchlist.json", [])


def get_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent})
    return s


def polite_sleep(seconds: float = 1.1):
    """MusicBrainz and courteous scraping etiquette both want >=1s between calls."""
    time.sleep(seconds)


def log(msg: str):
    print(f"[producer-watch] {msg}", flush=True)
