---
name: youtube-topic-research
description: Find a winnable YouTube long-form topic by weighing search demand (Google Trends via SerpApi) against existing competition (YouTube Data API). Use when choosing or validating a video topic, comparing candidate keywords or title phrasings, or checking whether a niche is already saturated.
---

# YouTube topic research — demand vs competition

Pick YouTube long-form topics by the **demand-vs-competition gap**: strong, rising search
interest that isn't already saturated. Two free data sources, each doing one job. Always run
them in this order — **demand is the gate; competition only matters for topics that clear it.**

The scripts live in this repo. Run them from the repo root with `python` — or `python3` on
machines where that's the command name (Python 3.7+, standard library only, no install step):

- Demand: `scripts/trends_serpapi.py`
- Competition: `scripts/youtube_competition.py`

## Workflow

**1. DEMAND — broad scan (do this first).** Take the user's candidate keywords/phrases (up to
10) and rank them by relative search interest with trajectory:

```
python scripts/trends_serpapi.py --terms "a,b,c,d,e" --timeframe "today 3-m" --gprop youtube
```

Read the SUMMARY: average interest per term, which leads, crossover points, and each term's
rising/flat/declining trajectory. Narrow to **2–3 finalists** — the strongest, ideally rising.

To deepen a finalist (only when useful — each is one more API call): `--type GEO_MAP` for the
regional split, or `--type RELATED_QUERIES` (one term at a time) for sub-topics and angles.

**2. COMPETITION — finalists only.** For the 2–3 finalists, measure how crowded the topic is:

```
python scripts/youtube_competition.py --terms "a,b" --max 25
```

Read the **Room to Rank** table (higher = fast view-velocity with few dominant 1M+ channels),
plus median views, freshness (old top results = neglected; days-old = a crowded flood), and the
large-channel share.

**3. DECIDE.** Apply the gate:

|  | **Low competition** | **High competition** |
|---|---|---|
| **High demand** | ✅ Make it now | ⚔️ Needs a sharp angle / speed |
| **Low demand** | 🪤 Trap — skip | ❌ Avoid |

A high Room-to-Rank score with **no** Google Trends demand is a **trap**, not an opening — low
competition *because* nobody's searching. Never recommend a topic on competition alone.

## Rules that keep the data honest

- **Google Trends is the only search-traffic source.** The YouTube Data API has no
  keyword search-volume data — never use it to judge "how much a term is searched."
- **Ignore YouTube `totalResults`** (an estimate capped at 1,000,000). The competition script
  already does; every stat comes from the sampled videos.
- Trends scores are a **relative 0–100 index**, not absolute volume — use them to compare terms
  and spot direction, not to read "X searches/month."
- **>5 terms is approximate.** Trends normalizes within one call; the demand script
  anchor-stitches 6–10 terms and flags the result APPROXIMATE. Keep scans to ≤5 terms for exact
  numbers.

## Free-tier discipline (the scarce resource)

- **SerpApi: 250 searches/month, shared, no rollover (~8/day).** Run one scan with all the
  user's terms; don't re-run identical queries. Reuse the broad-scan output when narrowing.
- YouTube Data API: ~10k units/day plus a separate ~100 search calls/day — roomy; one
  competition pull per finalist set is plenty.

## API keys (first run)

Both keys are free. If a script errors that a key is missing, guide the user to get it and store
it — never print, log, or commit a key.

- **SERPAPI_API_KEY** — sign up at https://serpapi.com/ and copy the key.
- **YOUTUBE_API_KEY** — Google Cloud Console → new project → enable **YouTube Data API v3** →
  Credentials → create an API key (an API key is enough; no OAuth).

For a cloned repo the simplest spot is a **`.env` at the repo root** (copy `.env.example` to
`.env`) — the scripts auto-load it. Real environment variables, if set, take precedence.

```
SERPAPI_API_KEY=your-serpapi-key
YOUTUBE_API_KEY=your-youtube-key
```
