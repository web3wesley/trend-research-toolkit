---
description: COMPETITION check — existing-video supply for finalist topics (YouTube Data API v3)
argument-hint: finalist one, finalist two [--max 25] [--published-after-days 90] [--region US]
---
COMPETITION signal: for 2–3 finalist topics already shortlisted by demand
(/prompts:google-keywords), measure how much strong, fresh content already exists. The YouTube
API has no search-volume data, so this never gauges demand; it also ignores totalResults (every
stat comes from the sampled videos).

Treat the comma-separated phrases in "$ARGUMENTS" as the --terms value (2–3 recommended); pass
any "--flag value" tokens through unchanged. Default sample is --max 25 (max 50) per term.

Run from the repo root (use python3 if that's the interpreter name on this machine):

```
python scripts/youtube_competition.py --terms "<phrases from $ARGUMENTS>" [<flags from $ARGUMENTS>]
```

Then summarize for the user: the Room to Rank table (higher = fast view-velocity with few
dominant 1M+ channels), median views / view-velocity, freshness, distinct-channel count, and
large-channel share — and call out the most winnable finalist. Competition side ONLY; pair it
with demand from /prompts:google-keywords. A high score with no demand is a trap.

If it errors that YOUTUBE_API_KEY is missing, the user needs a free key (Google Cloud Console →
enable YouTube Data API v3 → create an API key) in the repo's .env or as an environment variable.
Never print the key.
