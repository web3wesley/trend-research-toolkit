"""Tiny zero-dependency .env loader shared by the helper scripts.

Reads KEY=VALUE lines into os.environ WITHOUT overriding variables already present in the
real environment, so SERPAPI_API_KEY / YOUTUBE_API_KEY can live in a local .env file while
real environment variables (if set) still take precedence.

Search order when no explicit path is given (first file to define a key wins; real
environment variables beat all of them):
  1. ./.env                            -- the folder you're running in
  2. ~/.trend-research-toolkit/.env    -- a stable per-user location
  3. <repo>/.env                       -- alongside the scripts (cloned-repo layout)

The cwd and per-user locations matter when the toolkit is installed as a Claude Code plugin:
the plugin directory is a versioned cache that is replaced on update, so keys kept next to the
scripts would not survive. Put them in ~/.trend-research-toolkit/.env (or your working folder,
or real environment variables) instead.
"""
import os
from pathlib import Path

# Kept for backwards compatibility: the .env that sits next to a cloned repo.
DEFAULT_ENV = Path(__file__).resolve().parent.parent / ".env"


def _candidate_paths():
    return [
        Path.cwd() / ".env",
        Path.home() / ".trend-research-toolkit" / ".env",
        DEFAULT_ENV,
    ]


def load_env(path=None):
    paths = [Path(path)] if path else _candidate_paths()
    seen = set()
    for p in paths:
        try:
            p = p.resolve()
        except OSError:
            continue
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        for raw in p.read_text(encoding="utf-8-sig").splitlines():
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
