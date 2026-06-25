---
description: DEMAND scan — relative Google Trends search interest across keywords (SerpApi)
argument-hint: keyword one, keyword two, ... [--timeframe "today 3-m"] [--geo US] [--gprop youtube|web] [--type TIMESERIES|GEO_MAP|RELATED_QUERIES]
allowed-tools: Bash(python:*)
---
DEMAND signal: relative YouTube search interest (0–100, worldwide by default, ~90 days) with
per-term trajectory. Google Trends is the ONLY search-traffic source here. Run the COMPETITION
side afterward with `/yt-competition`.

Treat the comma-separated phrases in `$ARGUMENTS` as the `--terms` value; pass any `--flag value`
tokens through unchanged. Up to 10 terms (>5 is anchor-stitched and APPROXIMATE; ≤5 is exact).
Defaults if no flags given: `--timeframe "today 3-m" --gprop youtube`.

Run:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/trends_serpapi.py" --terms "<phrases from $ARGUMENTS>" [<flags from $ARGUMENTS>]
```

(Use `python3` instead of `python` if that's the interpreter name on this machine.)

Then summarize for the user: terms ranked by average interest, each trajectory, any lead-change
crossovers, and the 2–3 strongest finalists to take into `/yt-competition`.

SerpApi free tier is 250 searches/month (shared, no rollover) — run once with all terms; don't
repeat identical queries. If it errors that `SERPAPI_API_KEY` is missing, the user needs a free
key from https://serpapi.com/ stored as an environment variable, or in a `.env` in their working
folder, or in `~/.trend-research-toolkit/.env` (never print the key).
