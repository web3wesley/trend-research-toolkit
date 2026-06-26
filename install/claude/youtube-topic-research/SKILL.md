---
name: youtube-topic-research
description: Find a winnable YouTube long-form topic by weighing search demand (Google Trends via SerpApi) against existing competition (YouTube Data API). Use when choosing or validating a video topic, comparing candidate keywords or title phrasings, or checking whether a niche is already saturated.
---

# YouTube topic research — demand vs competition

Pick YouTube long-form topics by the **demand-vs-competition gap**: strong, rising search
interest that isn't already saturated. Two free data sources, each doing one job. Always run
them in this order — **demand is the gate; competition only matters for topics that clear it.**

## Where the scripts are (self-contained personal skill)

The Python scripts are bundled **inside this skill's own folder**. Run them with `python` (or
`python3`; Python 3.7+, standard library only, no install step). Reference them with the
skill-directory variable, which resolves to this folder at runtime:

- Demand:      `${CLAUDE_SKILL_DIR}/scripts/trends_serpapi.py`
- Competition: `${CLAUDE_SKILL_DIR}/scripts/youtube_competition.py`

If `${CLAUDE_SKILL_DIR}` is not set, the scripts are physically at
`~/.claude/skills/youtube-topic-research/scripts/` — use that path instead.

## Workflow

**1. DEMAND — broad scan (do this first).** Rank the user's candidate keywords/phrases (up to
10) by relative search interest with trajectory:

```
python "${CLAUDE_SKILL_DIR}/scripts/trends_serpapi.py" --terms "a,b,c,d,e" --timeframe "today 3-m" --gprop youtube
```

Read the SUMMARY: average interest per term, which leads, crossover points, and each term's
rising/flat/declining trajectory. Narrow to **2–3 finalists** — the strongest, ideally rising.

Deepen a finalist (only when useful — each is one more API call): `--type GEO_MAP` for the
regional split, or `--type RELATED_QUERIES` (one term at a time) for sub-topics and angles.

**2. COMPETITION — finalists only.** Measure how crowded the 2–3 finalists are:

```
python "${CLAUDE_SKILL_DIR}/scripts/youtube_competition.py" --terms "a,b" --max 25
```

Read the **Room to Rank** table (higher = fast view-velocity with few dominant 1M+ channels),
plus median views, freshness (old top results = neglected; days-old = a crowded flood), and the
large-channel share.

**3. DECIDE.**

|  | **Low competition** | **High competition** |
|---|---|---|
| **High demand** | ✅ Make it now | ⚔️ Needs a sharp angle / speed |
| **Low demand** | 🪤 Trap — skip | ❌ Avoid |

A high Room-to-Rank score with **no** Google Trends demand is a **trap** — low competition
*because* nobody's searching. Never recommend a topic on competition alone.

## Rules that keep the data honest

- **Google Trends is the only search-traffic source.** The YouTube Data API has no keyword
  search-volume data — never use it to judge "how much a term is searched."
- **Ignore YouTube `totalResults`** (an estimate capped at 1,000,000). The competition script
  already does; every stat comes from the sampled videos.
- Trends scores are a **relative 0–100 index**, not absolute volume.
- **>5 terms is approximate** (anchor-stitched); ≤5 terms is one exact call.

## Free-tier discipline

- **SerpApi: 250 searches/month, shared, no rollover (~8/day).** Run one scan with all terms;
  don't re-run identical queries.
- YouTube Data API: ~10k units/day + ~100 search calls/day — roomy.

## API keys

The scripts read keys in this order (first match wins; real environment variables beat all): a
real environment variable, `~/.trend-research-toolkit/.env`, a `.env` in the folder you're
working in, or a `.env` placed next to this skill. Recommended stable spot:
`~/.trend-research-toolkit/.env`, containing:

```
SERPAPI_API_KEY=your-serpapi-key
YOUTUBE_API_KEY=your-youtube-key
```

Never print, log, or commit a key.
