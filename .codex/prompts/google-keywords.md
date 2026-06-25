---
description: DEMAND scan — relative Google Trends search interest across keywords (SerpApi)
argument-hint: keyword one, keyword two, ... [--timeframe "today 3-m"] [--geo US] [--gprop youtube|web] [--type TIMESERIES|GEO_MAP|RELATED_QUERIES]
---
DEMAND signal: relative YouTube search interest (0–100, worldwide by default, ~90 days) with
per-term trajectory. Google Trends is the ONLY search-traffic source here. Run the COMPETITION
side afterward with /prompts:yt-competition.

Treat the comma-separated phrases in "$ARGUMENTS" as the --terms value; pass any "--flag value"
tokens through unchanged. Up to 10 terms (>5 is anchor-stitched and APPROXIMATE; ≤5 is exact).
Defaults if no flags given: --timeframe "today 3-m" --gprop youtube.

Run from the repo root (use python3 if that's the interpreter name on this machine):

```
python scripts/trends_serpapi.py --terms "<phrases from $ARGUMENTS>" [<flags from $ARGUMENTS>]
```

Then summarize for the user: terms ranked by average interest, each trajectory, any lead-change
crossovers, and the 2–3 strongest finalists to take into /prompts:yt-competition.

SerpApi free tier is 250 searches/month (shared, no rollover) — run once with all terms; don't
repeat identical queries. If it errors that SERPAPI_API_KEY is missing, the user needs a free key
from https://serpapi.com/ in the repo's .env (copy .env.example) or as an environment variable.
Never print the key.
