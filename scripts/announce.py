#!/usr/bin/env python3
"""Announce not-yet-announced posts on Bluesky.

Credentials live in data/announce-config.json (gitignored):
  {"bluesky": {"handle": "you.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}}
Announced slugs are tracked in data/announced.json (gitignored).
Exits 0 quietly when no config exists, so the pipeline works without it.
"""
import glob
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://ibrhmvk.github.io/hn-explained"
CONFIG = os.path.join(ROOT, "data", "announce-config.json")
STATE = os.path.join(ROOT, "data", "announced.json")


def xrpc(path, payload, token=None):
    req = urllib.request.Request(
        "https://bsky.social/xrpc/" + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": "Bearer " + token} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def post_bluesky(cfg, text, url):
    session = xrpc("com.atproto.server.createSession",
                   {"identifier": cfg["handle"], "password": cfg["app_password"]})
    start = len(text.encode()) - len(url.encode())
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "facets": [{"index": {"byteStart": start, "byteEnd": len(text.encode())},
                    "features": [{"$type": "app.bsky.richtext.facet#link",
                                  "uri": url}]}],
    }
    xrpc("com.atproto.repo.createRecord", {
        "repo": session["did"], "collection": "app.bsky.feed.post",
        "record": record}, token=session["accessJwt"])


def main():
    if not os.path.exists(CONFIG):
        print("announce: no config, skipping")
        return
    with open(CONFIG) as f:
        cfg = json.load(f)
    announced = set()
    if os.path.exists(STATE):
        with open(STATE) as f:
            announced = set(json.load(f))

    posts = []
    for path in glob.glob(os.path.join(ROOT, "data", "posts", "*.json")):
        with open(path) as f:
            posts.append(json.load(f))
    posts.sort(key=lambda p: p["date"])

    for p in posts:
        if p["slug"] in announced:
            continue
        url = f"{SITE_URL}/p/{p['slug']}.html"
        text = f"{p['title']}\n\n{p.get('domain') or 'news.ycombinator.com'} · {p['summary']}"
        # bluesky caps posts at 300 chars; keep the url intact at the end
        budget = 300 - len(url) - 2
        if len(text) > budget:
            text = text[:budget - 1].rstrip() + "…"
        text = f"{text}\n\n{url}"
        try:
            if "bluesky" in cfg:
                post_bluesky(cfg["bluesky"], text, url)
                print(f"announced on bluesky: {p['slug']}")
        except Exception as e:  # a failed announce must not fail the pipeline
            print(f"announce failed for {p['slug']}: {e}", file=sys.stderr)
            continue
        announced.add(p["slug"])

    with open(STATE, "w") as f:
        json.dump(sorted(announced), f, indent=2)


if __name__ == "__main__":
    main()
