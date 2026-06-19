"""Tiny zero-dependency .env loader shared by the helper scripts.

Reads KEY=VALUE lines from the project's .env (gitignored) into os.environ WITHOUT
overriding variables already present in the real environment. This lets you keep
SERPAPI_API_KEY / YOUTUBE_API_KEY in a local .env file instead of exporting them,
while real environment variables (if set) still take precedence.
"""
import os
from pathlib import Path

DEFAULT_ENV = Path(__file__).resolve().parent.parent / ".env"


def load_env(path=None):
    path = Path(path) if path else DEFAULT_ENV
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val
