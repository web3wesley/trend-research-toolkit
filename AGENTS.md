# Trend Research Toolkit — agent guide

This repo helps choose **YouTube long-form video topics** by comparing **demand** (who's
searching) against **competition** (what already exists). The goal is the best
*demand-vs-competition gap* — strong/rising search interest with thin/weak competition.

Two free data sources, two jobs. Run them in this order.

> This file is the tool-agnostic guide (Codex and other agents read `AGENTS.md`). Claude Code
> users get the same routing from `CLAUDE.md` and the bundled skill; the content is identical.

## 1. DEMAND — broad scan (do this first)

`scripts/trends_serpapi.py` (SerpApi → Google Trends). Relative **GLOBAL** search interest
across up to 10 phrases over the last 30–90 days, plus per-term trajectory
(rising/flat/declining). Use it to narrow to **2–3 finalists**.

```
python scripts/trends_serpapi.py --terms "a,b,c,d,e" --timeframe "today 3-m" --gprop youtube
```

Deepen the finalists: same-baseline `TIMESERIES`, `--type GEO_MAP` (regional split), or
`--type RELATED_QUERIES` (content angles; one term at a time).

## 2. COMPETITION — finalists only

`scripts/youtube_competition.py` (YouTube Data API v3). For the 2–3 finalists, read
existing-video views, recency, channel strength, and the **Room to Rank** table to judge
whether the topic is winnable.

```
python scripts/youtube_competition.py --terms "a,b" --max 25
```

## 3. DECIDE

Strong/rising demand (step 1) + thin/weak competition (step 2) = best topic. **Demand is the
gate:** a low-competition topic with no search demand is a trap, not an opening.

## Rules

- **Google Trends is the ONLY search-traffic source.** The YouTube Data API has no keyword
  search-volume data — never use it to gauge "how much a term is searched."
- **Never trust YouTube `pageInfo.totalResults`** (an estimate capped at 1,000,000). The
  competition script ignores it and computes everything from sampled videos.
- Reuse the broad-scan output when narrowing; **don't re-run identical SerpApi queries** — the
  free tier is the scarce resource.
- **>5 terms is anchor-stitched and APPROXIMATE;** ≤5 terms is one exact call.

## Free-tier limits (keep runs minimal)

- SerpApi: **250 searches/month**, shared, no rollover.
- YouTube Data API: **~10k units/day** plus a separate **~100 search-calls/day** bucket.

## Keys (never print, log, or commit)

Put them in the project's **`.env`** (gitignored) — the scripts auto-load it. Real environment
variables, if set, take precedence. Copy `.env.example` to `.env` to start.

- `SERPAPI_API_KEY` — https://serpapi.com/
- `YOUTUBE_API_KEY` — Google Cloud project with **YouTube Data API v3** enabled (API key, no OAuth)

Requires **Python 3.7+** (standard library only — no install step). Use `python3` where that is
the interpreter name.
