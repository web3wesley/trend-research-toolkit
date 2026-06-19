# Trend research routing (YouTube long-form: demand vs competition)

Goal: given a list of candidate keywords/phrases, find the topics with the best
**demand-vs-competition gap** — high/rising search interest with thin/weak existing competition.

Two free data sources, two different jobs. Run them in this order:

1. **DEMAND — broad scan.** `scripts/trends_serpapi.py` (SerpApi Google Trends).
   Give 5–10 phrases and see relative **GLOBAL** search interest over the last 30–90 days,
   plus per-term trajectory (rising/flat/declining). Use it to narrow to 2–3 finalists.
   ```
   python scripts/trends_serpapi.py --terms "a,b,c,d,e" --timeframe "today 3-m" --geo "" --gprop youtube
   ```
   Then deepen the finalists: same-baseline `TIMESERIES`, `--type GEO_MAP` (regional split),
   `--type RELATED_QUERIES` (content angles; one term at a time).

2. **COMPETITION — finalists only.** `scripts/youtube_competition.py` (YouTube Data API v3).
   For the 2–3 finalists, read existing-video views, recency, and channel strength to judge
   whether the topic is winnable.
   ```
   python scripts/youtube_competition.py --terms "a,b" --max 25
   ```

3. **Decide.** Strong/rising demand (step 1) + thin/weak competition (step 2) = best topic.

## Rules
- **Google Trends is the ONLY search-traffic source.** The YouTube Data API has no
  keyword search-volume data — never use it to gauge "how much a term is searched."
- **Never trust YouTube `pageInfo.totalResults`** (it's an estimate capped at 1,000,000).
  The competition script already ignores it and computes everything from sampled videos.
- The two tools measure different things (search interest vs competition), so they don't
  overlap — but **reuse the broad-scan output when narrowing; don't re-run identical
  SerpApi queries**, the SerpApi free tier is the scarce resource.

## Free-tier limits (keep runs minimal)
- SerpApi: **250 searches/month**, shared, no rollover. A >5-term scan costs multiple calls
  (anchor-stitched and flagged APPROXIMATE); ≤5 terms is one call and exact.
- YouTube Data API: **~10k units/day** plus a separate **~100 search-calls/day** bucket.

## Keys (never print, log, or commit)
- Put them in the project's **`.env`** (gitignored) — the scripts auto-load it. Real environment
  variables, if set, take precedence over `.env`.
- `SERPAPI_API_KEY` — https://serpapi.com/
- `YOUTUBE_API_KEY` — Google Cloud project with **YouTube Data API v3** enabled (API key, no OAuth)
- Copy `.env.example` to `.env` to start.
