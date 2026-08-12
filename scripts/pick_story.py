#!/usr/bin/env python3
"""Pick today's HN candidates: current front-page stories with >=100 points
that we haven't covered yet (keyed by hn_id in data/posts/). Prints a JSON
array of up to 10 candidates (the daily prompt picks the most explainable
one), or exits 3 if there are none."""
import glob
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_POINTS = 100
ALGOLIA_URL = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30"


def covered_ids():
    seen = set()
    for path in glob.glob(os.path.join(ROOT, "data", "posts", "*.json")):
        try:
            with open(path) as f:
                seen.add(int(json.load(f)["hn_id"]))
        except (KeyError, ValueError, TypeError):
            pass
    return seen


def eligible(hits, seen_ids, min_points=MIN_POINTS):
    out = []
    for h in hits:
        try:
            hn_id = int(h["objectID"])
        except (KeyError, ValueError, TypeError):
            continue
        points = h.get("points") or 0
        if points < min_points or hn_id in seen_ids or not h.get("title"):
            continue
        out.append({
            "hn_id": hn_id,
            "title": h["title"],
            "url": h.get("url") or None,
            "points": points,
            "num_comments": h.get("num_comments") or 0,
            "hn_url": f"https://news.ycombinator.com/item?id={hn_id}",
        })
    out.sort(key=lambda c: c["points"], reverse=True)
    return out[:10]


def fetch_front_page():
    req = urllib.request.Request(ALGOLIA_URL,
                                 headers={"User-Agent": "hn-explained"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["hits"]


def main():
    candidates = eligible(fetch_front_page(), covered_ids())
    if not candidates:
        sys.exit(3)  # nothing eligible today
    print(json.dumps(candidates, indent=2))


if __name__ == "__main__":
    main()
