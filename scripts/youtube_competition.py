#!/usr/bin/env python3
"""YouTube Data API v3 helper -- the COMPETITION signal for YouTube topic research.

For 2-3 finalist topics (already shortlisted by demand via trends_serpapi.py), this
measures the *supply* side: how much strong, fresh content already exists, so you can
tell which high-demand topic is actually winnable.

IMPORTANT: the YouTube Data API exposes NO keyword search-volume data -- use Google
Trends (trends_serpapi.py) for demand. Here we only read existing-video signals, and we
deliberately IGNORE search.list `pageInfo.totalResults` (it is an approximation capped at
1,000,000 and is not a real video count). All stats are computed from the SAMPLED videos.

Reads YOUTUBE_API_KEY from the environment and never prints it. Quota: ~10k units/day,
plus a separate ~100 search-calls/day bucket -- one run per finalist set is plenty.

Examples:
  python scripts/youtube_competition.py --terms "AI agents,AI workflows" --max 25
  python scripts/youtube_competition.py --terms "vibe coding" --max 40 --published-after-days 90
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from statistics import median

try:
    from _env import load_env
except ImportError:  # pragma: no cover - fall back to real env vars only
    def load_env(path=None):
        return

API_BASE = "https://www.googleapis.com/youtube/v3/"
TIMEOUT = 30
MAX_SAMPLE_CAP = 50           # search.list maxResults hard limit
LARGE_CHANNEL_SUBS = 1_000_000  # threshold for "big established competitor"


def eprint(*args):
    print(*args, file=sys.stderr)


class YouTubeError(RuntimeError):
    """Any failure talking to the YouTube Data API or parsing its response."""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _to_int(x, default=None):
    if isinstance(x, bool):
        return default
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        try:
            return int(s)
        except ValueError:
            return default
    return default


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def yt_get(endpoint, params):
    url = API_BASE + endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "trends-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            err = json.loads(e.read().decode("utf-8", "replace")).get("error", {})
            detail = err.get("message", "")
        except Exception:
            detail = str(e)
        hint = ""
        if e.code == 403:
            hint = ("  (403 usually means: API key invalid, 'YouTube Data API v3' not "
                    "enabled for the project, or quota exhausted.)")
        raise YouTubeError(f"HTTP {e.code} from YouTube API: {detail}{hint}") from None
    except urllib.error.URLError as e:
        raise YouTubeError(f"Network error reaching YouTube API: {e.reason}") from None
    except TimeoutError:
        raise YouTubeError(f"YouTube API request timed out after {TIMEOUT}s") from None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise YouTubeError(f"Could not parse YouTube API JSON response: {e}") from None


# --------------------------------------------------------------------------- #
# per-term analysis
# --------------------------------------------------------------------------- #
def _channel_subs(api_key, channel_ids):
    """channel_id -> subscriberCount (None if hidden/unknown). 1 unit per 50 ids."""
    subs = {}
    ids = [c for c in channel_ids if c]
    for batch in _chunks(ids, 50):
        data = yt_get("channels", {"part": "statistics", "id": ",".join(batch),
                                   "key": api_key})
        for item in data.get("items", []):
            stats = item.get("statistics", {})
            if stats.get("hiddenSubscriberCount"):
                subs[item.get("id")] = None
            else:
                subs[item.get("id")] = _to_int(stats.get("subscriberCount"))
    return subs


def analyze_term(api_key, term, max_results, published_after, region, now):
    search_params = {
        "part": "snippet", "q": term, "type": "video", "order": "relevance",
        "maxResults": max_results, "key": api_key,
    }
    if published_after:
        search_params["publishedAfter"] = published_after
    if region:
        search_params["regionCode"] = region

    search = yt_get("search", search_params)
    video_ids = [it["id"]["videoId"] for it in search.get("items", [])
                 if it.get("id", {}).get("videoId")]
    if not video_ids:
        return {"term": term, "sample_size": 0, "note": "no videos returned"}

    vids = []
    for batch in _chunks(video_ids, 50):
        data = yt_get("videos", {"part": "statistics,snippet", "id": ",".join(batch),
                                 "key": api_key})
        for v in data.get("items", []):
            st, sn = v.get("statistics", {}), v.get("snippet", {})
            published = _parse_dt(sn.get("publishedAt"))
            age_days = max((now - published).total_seconds() / 86400.0, 0.01) if published else None
            vids.append({
                "views": _to_int(st.get("viewCount"), 0),
                "age_days": age_days,
                "channel_id": sn.get("channelId"),
                "channel_title": sn.get("channelTitle"),
            })

    subs = _channel_subs(api_key, {v["channel_id"] for v in vids})

    views = [v["views"] for v in vids]
    ages = [v["age_days"] for v in vids if v["age_days"] is not None]
    velocities = [v["views"] / v["age_days"] for v in vids if v["age_days"]]
    distinct_channels = {v["channel_id"] for v in vids if v["channel_id"]}
    large = sum(1 for v in vids
                if subs.get(v["channel_id"]) is not None
                and subs[v["channel_id"]] >= LARGE_CHANNEL_SUBS)
    subs_known = sum(1 for v in vids if subs.get(v["channel_id"]) is not None)

    top = max(vids, key=lambda v: v["views"])
    return {
        "term": term,
        "sample_size": len(vids),
        "median_views": int(median(views)) if views else 0,
        "max_views": max(views) if views else 0,
        "mean_views": int(sum(views) / len(views)) if views else 0,
        "median_view_velocity_per_day": round(median(velocities), 1) if velocities else 0.0,
        "median_age_days": round(median(ages), 1) if ages else None,
        "distinct_channels": len(distinct_channels),
        "large_channel_share": round(large / len(vids), 2) if vids else 0.0,
        "large_channel_subs_coverage": round(subs_known / len(vids), 2) if vids else 0.0,
        "top_video": {"title": top.get("channel_title"), "views": top["views"]},
        "top_channel": top.get("channel_title"),
    }


# --------------------------------------------------------------------------- #
# room to rank (relative, across the terms in this run) -- COMPETITION ONLY
# --------------------------------------------------------------------------- #
def room_to_rank_table(results):
    """Competition-side heuristic. Uses view VELOCITY (views/day) rather than total
    views, so a fresh-but-surging topic isn't penalised for not having accumulated
    views yet. It deliberately ignores search demand -- read it next to trends data."""
    scored = [r for r in results if r.get("sample_size")]
    if not scored:
        return []
    max_traction = max(r["median_view_velocity_per_day"] for r in scored) or 1
    out = []
    for r in scored:
        traction_norm = r["median_view_velocity_per_day"] / max_traction  # 0..1 watch rate
        gap = 1.0 - r["large_channel_share"]                              # 0..1 room vs giants
        out.append({
            "term": r["term"],
            "traction_views_per_day": r["median_view_velocity_per_day"],
            "large_channel_share": r["large_channel_share"],
            "room_to_rank": round(100 * traction_norm * gap, 1),  # competition-only heuristic
        })
    out.sort(key=lambda x: x["room_to_rank"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_terms(raw):
    return [t.strip() for t in raw.split(",") if t.strip()]


def main(argv=None):
    try:  # channel titles / text may contain non-ASCII; avoid cp1252 crashes
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        description="YouTube Data API -- competition signal for finalist topics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--terms", required=True,
                        help="Comma-separated finalist topics (2-3 recommended).")
    parser.add_argument("--max", type=int, default=25,
                        help=f"Videos sampled per term (default 25, max {MAX_SAMPLE_CAP}).")
    parser.add_argument("--published-after-days", type=int, default=None,
                        help="Only consider videos published within the last N days.")
    parser.add_argument("--region", default=None,
                        help='Optional regionCode, e.g. "US". Default: global.')
    args = parser.parse_args(argv)

    load_env()  # pull keys from the project's .env (gitignored) if present
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        eprint("ERROR: YOUTUBE_API_KEY is not set.")
        eprint("Add it to the project's .env file (recommended):  YOUTUBE_API_KEY=your-key")
        eprint("Create a free key: Google Cloud Console -> new project -> enable")
        eprint("'YouTube Data API v3' -> Credentials -> API key. Or set an env var (PowerShell):")
        eprint('  $env:YOUTUBE_API_KEY = "your-key"')
        return 1

    terms = parse_terms(args.terms)
    if not terms:
        eprint("ERROR: --terms produced no usable topics.")
        return 2

    max_results = args.max
    if max_results < 1 or max_results > MAX_SAMPLE_CAP:
        eprint(f"ERROR: --max must be between 1 and {MAX_SAMPLE_CAP} (got {max_results}).")
        return 2

    now = datetime.now(timezone.utc)
    published_after = None
    if args.published_after_days is not None:
        if args.published_after_days < 1:
            eprint("ERROR: --published-after-days must be >= 1.")
            return 2
        cutoff = now.timestamp() - args.published_after_days * 86400
        published_after = datetime.fromtimestamp(cutoff, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")

    results = []
    try:
        for term in terms:
            results.append(analyze_term(api_key, term, max_results, published_after,
                                        args.region, now))
    except YouTubeError as e:
        eprint(f"ERROR: {e}")
        return 3

    print(json.dumps({
        "region": args.region or "GLOBAL",
        "published_after": published_after or "any",
        "sample_per_term": max_results,
        "results": results,
    }, indent=2, ensure_ascii=False))

    table = room_to_rank_table(results)
    print("\n=== ROOM TO RANK (competition only; ignores search demand; totalResults ignored) ===")
    if not table:
        print("  No sampled videos for any term.")
    else:
        for row in table:
            print(f"  {row['term']:<32} room-to-rank {row['room_to_rank']:>5}   "
                  f"(traction {row['traction_views_per_day']:,.0f} views/day, "
                  f"big-channel share {row['large_channel_share']:.0%})")
        best = table[0]
        print(f"\n  Most room to rank: {best['term']} (score {best['room_to_rank']})")
        print("  Higher = fast view-velocity with fewer dominant 1M+ channels. This is the")
        print("  COMPETITION side ONLY -- always read it next to demand (trends_serpapi.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
