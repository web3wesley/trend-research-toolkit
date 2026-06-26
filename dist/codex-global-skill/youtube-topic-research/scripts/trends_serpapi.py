#!/usr/bin/env python3
"""SerpApi Google Trends helper -- the DEMAND signal for YouTube topic research.

Two jobs (see CLAUDE.md for routing):
  * Broad scan : relative search interest across up to 10 phrases, global, 30-90 days.
  * Deep dive  : same-baseline TIMESERIES, regional GEO_MAP, RELATED_QUERIES on finalists.

Google Trends is the ONLY search-traffic source in this project (the YouTube Data API
exposes no keyword search-volume data). Scores are RELATIVE interest (0-100), not absolute
search counts.

Reads SERPAPI_API_KEY from the environment and never prints it. Free tier: 250 searches
per month, shared and with no rollover -- keep runs minimal.

Examples:
  python scripts/trends_serpapi.py --terms "AI agents,AI workflows" --timeframe "today 3-m" --geo "" --gprop youtube
  python scripts/trends_serpapi.py --terms "AI agents,AI workflows" --type GEO_MAP --geo US
  python scripts/trends_serpapi.py --terms "AI agents" --type RELATED_QUERIES
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    from _env import load_env
except ImportError:  # pragma: no cover - fall back to real env vars only
    def load_env(path=None):
        return

SEARCH_URL = "https://serpapi.com/search.json"
MAX_TERMS = 10          # hard cap we accept from the user
BATCH = 5               # SerpApi's per-call comparison limit for TIMESERIES/GEO_MAP
TIMEOUT = 30            # seconds
META_KEYS = ("date", "timestamp")


def eprint(*args):
    print(*args, file=sys.stderr)


class SerpApiError(RuntimeError):
    """Any failure talking to SerpApi or making sense of its response."""


# --------------------------------------------------------------------------- #
# small helpers
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
            try:
                return int(float(s))
            except ValueError:
                return default
    return default


def _mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return sum(values) / len(values) if values else 0.0


def _clean(s):
    """Normalise Unicode spaces/dashes Google uses in date labels to ASCII."""
    if not isinstance(s, str):
        return s
    return (s.replace(" ", " ").replace(" ", " ")
            .replace("–", "-").replace("—", "-"))


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def serpapi_get(api_key, terms, data_type, date, geo, gprop):
    """Call the google_trends engine and return the parsed JSON dict (or raise)."""
    params = {
        "engine": "google_trends",
        "q": ",".join(terms),
        "data_type": data_type,
        "api_key": api_key,
    }
    if date:
        params["date"] = date
    if geo:
        params["geo"] = geo
    if gprop:  # empty string == web search; only send for youtube/news/etc.
        params["gprop"] = gprop

    url = SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "trends-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            body = e.read().decode("utf-8", "replace")
            detail = json.loads(body).get("error", body)
        except Exception:
            detail = str(e)
        raise SerpApiError(f"HTTP {e.code} from SerpApi: {detail}") from None
    except urllib.error.URLError as e:
        raise SerpApiError(f"Network error reaching SerpApi: {e.reason}") from None
    except TimeoutError:
        raise SerpApiError(f"SerpApi request timed out after {TIMEOUT}s") from None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SerpApiError(f"Could not parse SerpApi JSON response: {e}") from None

    if isinstance(data, dict) and data.get("error"):
        raise SerpApiError(f"SerpApi returned an error: {data['error']}")
    status = (data.get("search_metadata") or {}).get("status")
    if status and status not in ("Success", "Cached"):
        raise SerpApiError(f"SerpApi status={status!r} (no successful result)")
    return data


# --------------------------------------------------------------------------- #
# TIMESERIES
# --------------------------------------------------------------------------- #
def parse_timeseries(data):
    """interest_over_time.timeline_data -> [{date, timestamp, <term>: value, ...}]."""
    iot = data.get("interest_over_time")
    if not iot or not iot.get("timeline_data"):
        raise SerpApiError(
            "No interest_over_time/timeline_data in response "
            "(no Google Trends data for these terms / timeframe?)."
        )
    points = []
    for entry in iot["timeline_data"]:
        row = {"date": _clean(entry.get("date")), "timestamp": _to_int(entry.get("timestamp"))}
        for v in entry.get("values", []):
            q = v.get("query")
            if q is not None:
                row[q] = _to_int(v.get("extracted_value"), _to_int(v.get("value"), 0))
        points.append(row)
    return points


def _averages(points, terms):
    return {t: _mean([p.get(t) for p in points]) for t in terms}


def _call_points(api_key, batch_terms, date, geo, gprop):
    return parse_timeseries(serpapi_get(api_key, batch_terms, "TIMESERIES", date, geo, gprop))


def stitch_timeseries(api_key, terms, date, geo, gprop):
    """Compare >5 terms by stitching batches through a shared anchor term.

    Google Trends normalises 0-100 *within a single call*, so two separate calls are
    not directly comparable. We keep one anchor term in every batch and rescale each
    batch onto the anchor's baseline, then renormalise the merged result to 0-100.
    The result is APPROXIMATE (sensitive to anchor noise); <=5 terms is exact.
    """
    calls = 0
    first = terms[:BATCH]
    p1 = _call_points(api_key, first, date, geo, gprop)
    calls += 1
    avg1 = _averages(p1, first)
    anchor = max(first, key=lambda t: avg1.get(t, 0.0))
    anchor_base = avg1.get(anchor, 0.0)
    if anchor_base <= 0:
        raise SerpApiError(
            "The strongest of the first 5 terms still has zero interest, so cross-batch "
            "stitching would be meaningless. Re-run with <=5 terms or different terms."
        )

    merged = {}

    def add_rows(rows, scale_by):  # scale_by: {term: scale}
        for row in rows:
            ts = row["timestamp"]
            slot = merged.setdefault(ts, {"date": row["date"], "timestamp": ts})
            for term, scale in scale_by.items():
                val = row.get(term)
                if isinstance(val, (int, float)):
                    slot[term] = val * scale

    add_rows(p1, {t: 1.0 for t in first})

    rest = terms[BATCH:]
    step = BATCH - 1  # one slot reserved for the anchor
    for i in range(0, len(rest), step):
        chunk = rest[i:i + step]
        pk = _call_points(api_key, [anchor] + chunk, date, geo, gprop)
        calls += 1
        ak = _averages(pk, [anchor]).get(anchor, 0.0)
        scale = (anchor_base / ak) if ak > 0 else 1.0
        add_rows(pk, {t: scale for t in chunk})  # add only the new terms, rescaled

    points = [merged[ts] for ts in sorted(merged)]
    all_vals = [v for row in points for k, v in row.items()
                if k not in META_KEYS and isinstance(v, (int, float))]
    mx = max(all_vals) if all_vals else 0
    if mx > 0:
        for row in points:
            for k in list(row):
                if k not in META_KEYS and isinstance(row[k], (int, float)):
                    row[k] = round(row[k] * 100.0 / mx, 1)
    return points, calls


def _trajectory(points, term):
    vals = [p.get(term) for p in points if isinstance(p.get(term), (int, float))]
    if len(vals) < 4:
        return "n/a"
    k = max(1, len(vals) // 3)
    early, late = _mean(vals[:k]), _mean(vals[-k:])
    if early == 0:
        return "rising" if late > 0 else "flat"
    change = (late - early) / early * 100.0
    if change >= 15:
        return f"rising (+{change:.0f}%)"
    if change <= -15:
        return f"declining ({change:.0f}%)"
    return f"flat ({change:+.0f}%)"


def summarize_timeseries(points, terms):
    averages = {t: round(_mean([p.get(t) for p in points]), 1) for t in terms}
    ranked = sorted(averages.items(), key=lambda kv: kv[1], reverse=True)
    crossovers, prev = [], None
    for p in points:
        present = {t: p[t] for t in terms if isinstance(p.get(t), (int, float))}
        if not present:
            continue
        leader = max(present, key=present.get)
        if prev is not None and leader != prev:
            crossovers.append({"date": p["date"], "from": prev, "to": leader})
        prev = leader
    trajectories = {t: _trajectory(points, t) for t in terms}
    return averages, ranked, crossovers, trajectories


def run_timeseries(api_key, terms, date, geo, gprop):
    approx = len(terms) > BATCH
    if approx:
        points, calls = stitch_timeseries(api_key, terms, date, geo, gprop)
    else:
        points = _call_points(api_key, terms, date, geo, gprop)
        calls = 1

    print(json.dumps({"timeframe": date, "geo": geo or "WORLDWIDE",
                      "gprop": gprop or "web", "timeline": points},
                     indent=2, ensure_ascii=False))

    averages, ranked, crossovers, trajectories = summarize_timeseries(points, terms)
    eprint(f"\n[serpapi] data_type=TIMESERIES, calls used={calls}"
           + ("  (>5 terms: APPROXIMATE anchor-stitched scale)" if approx else ""))
    print("\n=== SUMMARY (relative interest 0-100) ===")
    for term, avg in ranked:
        print(f"  {term:<32} avg {avg:>5}   trajectory: {trajectories[term]}")
    winner = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    if runner and winner[1] == runner[1]:
        print(f"\n  Higher average interest: TIE ({winner[0]} = {runner[0]})")
    else:
        print(f"\n  Higher average interest: {winner[0]} ({winner[1]})")
    if crossovers:
        print("  Lead changes (crossover points):")
        for c in crossovers:
            print(f"    {c['date']}: {c['from']} -> {c['to']}")
    else:
        print("  Lead changes: none (one term led the entire window)")


# --------------------------------------------------------------------------- #
# GEO_MAP
# --------------------------------------------------------------------------- #
def run_geo_map(api_key, terms, date, geo, gprop):
    data = serpapi_get(api_key, terms, "GEO_MAP", date, geo, gprop)
    regions = data.get("compared_breakdown_by_region")
    if not regions:
        raise SerpApiError("No compared_breakdown_by_region in response (try fewer terms / wider geo).")
    cleaned = []
    for r in regions:
        row = {"location": r.get("location"), "geo": r.get("geo")}
        for v in r.get("values", []):
            q = v.get("query")
            if q is not None:
                row[q] = _to_int(v.get("extracted_value"), _to_int(v.get("value"), 0))
        cleaned.append(row)
    print(json.dumps({"timeframe": date, "geo": geo or "WORLDWIDE",
                      "regions": cleaned}, indent=2, ensure_ascii=False))
    eprint(f"\n[serpapi] data_type=GEO_MAP, calls used=1, regions={len(cleaned)}")


# --------------------------------------------------------------------------- #
# RELATED_QUERIES
# --------------------------------------------------------------------------- #
def run_related(api_key, term, date, geo, gprop):
    data = serpapi_get(api_key, [term], "RELATED_QUERIES", date, geo, gprop)
    rq = data.get("related_queries") or {}
    out = {
        "term": term,
        "top": [{"query": x.get("query"),
                 "value": _to_int(x.get("extracted_value"), _to_int(x.get("value")))}
                for x in rq.get("top", []) or []],
        "rising": [{"query": x.get("query"),
                    "value": x.get("value"),                 # may be "Breakout" / "+2,300%"
                    "extracted_value": x.get("extracted_value")}
                   for x in rq.get("rising", []) or []],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    eprint(f"\n[serpapi] data_type=RELATED_QUERIES, calls used=1, "
           f"top={len(out['top'])}, rising={len(out['rising'])}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_terms(raw):
    return [t.strip() for t in raw.split(",") if t.strip()]


def main(argv=None):
    try:  # ensure non-ASCII (Google's date labels) print on a cp1252 console
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        description="SerpApi Google Trends -- demand signal (relative search interest).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--terms", required=True,
                        help="Comma-separated keywords/phrases (up to 10 for TIMESERIES).")
    parser.add_argument("--timeframe", default="today 3-m",
                        help='Google Trends date range (default "today 3-m" = ~90 days; '
                             'also "today 1-m", "today 12-m", or "yyyy-mm-dd yyyy-mm-dd").')
    parser.add_argument("--geo", default="",
                        help='Region code, e.g. "US". Empty (default) = WORLDWIDE.')
    parser.add_argument("--gprop", default="youtube", choices=["youtube", "web"],
                        help='Search property: "youtube" (default) or "web".')
    parser.add_argument("--type", dest="data_type", default="TIMESERIES",
                        choices=["TIMESERIES", "GEO_MAP", "RELATED_QUERIES"],
                        help="Which Google Trends panel to pull (default TIMESERIES).")
    args = parser.parse_args(argv)

    load_env()  # pull keys from the project's .env (gitignored) if present
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        eprint("ERROR: SERPAPI_API_KEY is not set.")
        eprint("Add it to the project's .env file (recommended):  SERPAPI_API_KEY=your-key")
        eprint("Get a free key at https://serpapi.com/ . Or set an env var (PowerShell):")
        eprint('  $env:SERPAPI_API_KEY = "your-key"')
        return 1

    terms = parse_terms(args.terms)
    if not terms:
        eprint("ERROR: --terms produced no usable keywords.")
        return 2
    if len(terms) > MAX_TERMS:
        eprint(f"ERROR: {len(terms)} terms given; max is {MAX_TERMS}.")
        return 2

    gprop = "" if args.gprop == "web" else "youtube"

    if args.data_type == "RELATED_QUERIES" and len(terms) != 1:
        eprint("ERROR: --type RELATED_QUERIES accepts exactly ONE term "
               f"(got {len(terms)}). Run it once per term.")
        return 2
    if args.data_type == "GEO_MAP" and len(terms) > BATCH:
        eprint(f"ERROR: --type GEO_MAP accepts up to {BATCH} terms (got {len(terms)}).")
        return 2

    try:
        if args.data_type == "TIMESERIES":
            run_timeseries(api_key, terms, args.timeframe, args.geo, gprop)
        elif args.data_type == "GEO_MAP":
            run_geo_map(api_key, terms, args.timeframe, args.geo, gprop)
        else:
            run_related(api_key, terms[0], args.timeframe, args.geo, gprop)
    except SerpApiError as e:
        eprint(f"ERROR: {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
