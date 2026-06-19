# Trend Research Toolkit

A two-tier workflow for choosing **YouTube long-form video topics** by comparing
**demand** (who's searching) against **competition** (what already exists). The goal is to
find the best *demand-vs-competition gap* — topics with strong, rising interest that aren't
already saturated.

Two free-tier data sources, each doing one job:

| Tool | Job | Source | Free tier |
|---|---|---|---|
| [`scripts/trends_serpapi.py`](scripts/trends_serpapi.py) | **Demand** — relative search interest over time, regional split, related queries | SerpApi → Google Trends | 250 searches/mo |
| [`scripts/youtube_competition.py`](scripts/youtube_competition.py) | **Competition** — existing-video views, freshness, channel strength | YouTube Data API v3 | ~10k units/day + ~100 search calls/day |

> **Why two tools?** Google Trends is the *only* source of search-traffic data — the YouTube
> Data API has no keyword search-volume endpoint. YouTube fills the other half: how crowded a
> topic already is. Always check demand **first**, then competition on the survivors.

---

## Project layout

```
.
├─ scripts/
│  ├─ trends_serpapi.py        # demand signal (Google Trends via SerpApi)
│  ├─ youtube_competition.py   # competition signal (YouTube Data API)
│  └─ _env.py                  # tiny .env loader (no dependencies)
├─ .env                        # your API keys (gitignored — never commit)
├─ .env.example                # template
├─ CLAUDE.md                   # routing rule for AI assistant sessions
└─ README.md                   # this file
```

No third-party packages — the scripts use only the Python standard library. Requires **Python 3.7+**.

---

## Setup

1. **Get the two API keys (both free):**
   - **SerpApi:** sign up at <https://serpapi.com/> and copy your API key.
   - **YouTube Data API v3:** in [Google Cloud Console](https://console.cloud.google.com/), create
     a project → **Enable APIs** → enable *YouTube Data API v3* → **Credentials → Create credentials
     → API key**. (An API key is enough; no OAuth. Optionally restrict it to YouTube Data API v3.)

2. **Add them to `.env`** (copy `.env.example` to `.env` if needed):
   ```
   SERPAPI_API_KEY=your-serpapi-key
   YOUTUBE_API_KEY=your-youtube-key
   ```
   The scripts auto-load `.env`. Real environment variables, if set, take precedence.

3. **Run anything below.** From the project folder:
   ```powershell
   python scripts/trends_serpapi.py --terms "AI agents,AI workflows"
   ```

---

## Quick start — the core loop

```powershell
# 1) BROAD SCAN — rank candidates by demand (global, last 90 days)
python scripts/trends_serpapi.py --terms "AI agents,AI automation,vibe coding,prompt engineering,RAG" --timeframe "today 3-m"

# 2) DEEP DIVE — head-to-head on your 2-3 finalists (same-baseline, 12 months)
python scripts/trends_serpapi.py --terms "AI agents,AI automation" --timeframe "today 12-m" --geo US

# 3) COMPETITION — is the topic winnable?
python scripts/youtube_competition.py --terms "AI agents,AI automation" --max 25

# 4) DECIDE — strong/rising demand + thin/weak competition = best topic
```

> **PowerShell tip:** for a worldwide scan, **omit `--geo`** (it defaults to global). Passing
> `--geo ""` fails because PowerShell drops empty-string arguments.

---

## Tool 1 — `trends_serpapi.py` (demand)

Relative search interest from Google Trends. Scores are a **0–100 index, not absolute volume.**

| Flag | Default | Notes |
|---|---|---|
| `--terms` | *(required)* | Comma-separated. Up to **10** for TIMESERIES, **5** for GEO_MAP, **1** for RELATED_QUERIES. |
| `--timeframe` | `today 3-m` | See date values below. Free-form — custom ranges allowed. |
| `--geo` | `""` (worldwide) | Country (`US`), sub-region (`US-CA`), or omit for global. |
| `--gprop` | `youtube` | `youtube` = YouTube search interest; `web` = general Google search. |
| `--type` | `TIMESERIES` | `TIMESERIES`, `GEO_MAP`, or `RELATED_QUERIES`. |

**`--timeframe` values:** `now 7-d`, `today 1-m` (~30d), `today 3-m` (~90d), `today 12-m`,
`today 5-y`, `all`, or a custom range `"2024-01-01 2026-06-19"`.

**What each `--type` returns:**
- **TIMESERIES** — interest over time + a SUMMARY: each term's average, which term leads,
  crossover points (where the lead flips), and trajectory (rising/flat/declining).
- **GEO_MAP** — interest broken down by region (US states with `--geo US`; countries worldwide).
- **RELATED_QUERIES** — `top` (consistently searched) and `rising` (spiking; "Breakout" = explosive)
  related searches for one term. Great for finding sub-topics and angles.

**Examples:**
```powershell
# Compare title phrasings to pick the highest-demand keyword
python scripts/trends_serpapi.py --terms "AI agents,how to build AI agents,AI agent tutorial,n8n AI agents"

# Catch fast risers in the last month
python scripts/trends_serpapi.py --terms "AI agents" --timeframe "today 1-m"

# Seasonality over 5 years
python scripts/trends_serpapi.py --terms "tax software" --timeframe "today 5-y"

# Where is the audience? (US state-level)
python scripts/trends_serpapi.py --terms "AI agents,AI automation" --type GEO_MAP --geo US

# Find rising sub-topics / angles
python scripts/trends_serpapi.py --terms "AI agents" --type RELATED_QUERIES

# Web vs YouTube demand (run both, compare) — gaps = underserved on video
python scripts/trends_serpapi.py --terms "AI agents,RAG,fine tuning" --gprop web
python scripts/trends_serpapi.py --terms "AI agents,RAG,fine tuning" --gprop youtube
```

> **Comparing more than 5 terms:** Google Trends only normalizes *within one call*. The script
> auto-stitches 6–10 terms through a shared anchor term and renormalizes to 0–100, but flags the
> result as **APPROXIMATE**. For exact numbers, keep scans to ≤5 terms.

---

## Tool 2 — `youtube_competition.py` (competition)

Samples real YouTube videos for each term and reports the supply side. It deliberately
**ignores `pageInfo.totalResults`** (an unreliable estimate capped at 1M) — every stat comes
from the sampled videos.

| Flag | Default | Notes |
|---|---|---|
| `--terms` | *(required)* | Comma-separated finalist topics (2–3 recommended). |
| `--max` | `25` | Videos sampled per term (max 50). |
| `--published-after-days` | *(none)* | Only consider videos newer than N days. |
| `--region` | *(global)* | Optional `regionCode`, e.g. `US`. |

**Output fields (per term):**

| Field | Meaning |
|---|---|
| `median_views` / `max_views` / `mean_views` | Revealed demand — are people actually watching this? |
| `median_view_velocity_per_day` | Views ÷ video age — how fast videos gain views. **This is what Room to Rank is built on.** |
| `median_age_days` | Freshness of the top results. **Old (6mo+) = neglected; days = crowded flood.** |
| `distinct_channels` | How many different channels own the top results. |
| `large_channel_share` | Fraction of sampled videos from 1M+ subscriber channels (competition strength). |
| `room_to_rank` | Competition-only heuristic: `100 × (view-velocity ÷ best-velocity in run) × (1 − big-channel share)`. Higher = more room. **Ignores demand by design.** |

**Examples:**
```powershell
# Standard competition read on finalists
python scripts/youtube_competition.py --terms "AI agents,AI automation" --max 25

# Only recent competition — is anyone serving this RIGHT NOW?
python scripts/youtube_competition.py --terms "AI agents" --published-after-days 30 --max 40

# US-only competition
python scripts/youtube_competition.py --terms "AI agents" --region US
```

> **Room to Rank is demand-blind** (the YouTube API can't see search volume). A high score with
> no Google Trends demand is a **trap** — low competition *because* nobody's searching. It uses
> view *velocity* (not total views), so fresh, surging topics aren't penalised. Always pair it with Tool 1.

---

## How to decide

|  | **Low competition** | **High competition** |
|---|---|---|
| **High demand** | ✅ Make it now | ⚔️ Need a sharp angle / speed |
| **Low demand** | 🪤 Trap — skip | ❌ Avoid |

Demand (Trends) is the gate; competition only matters for topics that clear it.

---

## Worked example: the demand gate

A real run showing why you check demand *before* competition. Researching a video about YouTube
tools, **"free VidIQ alternative" scored the highest Room to Rank (85.7)** — the lowest big-channel
share on the board — so by competition alone it looked like the best opening. But Google Trends put
its search demand at **~0**: nobody searches that phrase on YouTube. Low competition with no demand
is an empty room, not an opportunity.

**Room to Rank is competition-only; the demand gate is what catches this.** Demand first, every time.

---

## Key concepts & caveats

- **Relative, not absolute.** Trends scores are a 0–100 index. Use them to compare and spot
  direction, not to read "X searches/month."
- **Anchor terms for tracking over time.** Because Trends normalizes per call, keep one stable
  anchor term in every recurring scan so you can track movement across weeks.
- **Competition is a sample.** Stats reflect the top `--max` videos, not all of YouTube.
- **Latest data bucket is partial.** The current week/day is still accumulating.

---

## Free-tier limits

| Service | Limit | Practical note |
|---|---|---|
| SerpApi (Trends) | 250 searches/month, no rollover | The scarce resource (~8/day). Reuse broad-scan output; don't re-query. A >5-term scan costs multiple calls. |
| YouTube Data API | ~10k units/day + ~100 search calls/day | Roomy. One competition pull per finalist set is plenty. |

Keep test runs minimal. Don't create extra accounts to multiply credits.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `SERPAPI_API_KEY is not set` / `YOUTUBE_API_KEY is not set` | Add the key to `.env` (no quotes, no spaces). |
| `argument --geo: expected one argument` (PowerShell) | Omit `--geo` for global; PowerShell drops `--geo ""`. |
| `HTTP 403` from YouTube | Enable *YouTube Data API v3* on the project, check key restrictions, or you've hit quota. |
| `RELATED_QUERIES accepts exactly ONE term` | Run it once per term — that data type is single-term only. |
| Empty / no data | Term may have too little search volume, or the timeframe/geo is too narrow. |

---

## Security

- Keys live in `.env` only — **never printed, logged, or committed.** `.env` is gitignored;
  `.env.example` holds blank placeholders.
- Restrict the YouTube key to *YouTube Data API v3* in the console as defense-in-depth.
