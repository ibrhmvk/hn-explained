#!/usr/bin/env python3
"""Pick today's repo: the highest-starred repo created in the last 3 weeks
that we haven't covered yet. Prints a JSON blob to stdout, or nothing if
no candidate is found."""
import json
import glob
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_STARS = 500


def covered_repos():
    seen = set()
    for path in glob.glob(os.path.join(ROOT, "data", "posts", "*.json")):
        try:
            with open(path) as f:
                seen.add(json.load(f)["repo"].lower())
        except (KeyError, ValueError):
            pass
    return seen


def search(query):
    url = (
        "https://api.github.com/search/repositories?q="
        + urllib.parse.quote(query)
        + "&sort=stars&order=desc&per_page=30"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "trending-explained"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["items"]


def main():
    since = (date.today() - timedelta(days=21)).isoformat()
    seen = covered_repos()
    for item in search(f"created:>{since} stars:>{MIN_STARS}"):
        if item["full_name"].lower() in seen:
            continue
        print(json.dumps({
            "repo": item["full_name"],
            "url": item["html_url"],
            "description": item["description"] or "",
            "stars": item["stargazers_count"],
            "language": item["language"] or "",
            "created_at": item["created_at"],
        }, indent=2))
        return
    print("", end="")
    sys.exit(3)  # nothing new to cover today


if __name__ == "__main__":
    main()
