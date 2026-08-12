# HN, Explained Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A sibling site to Repo, Explained: one automated post per day explaining the day's top technical Hacker News story, with an embedded Scrimba explainer, published to GitHub Pages.

**Architecture:** Copy the proven trending-explained pipeline (`launchd → run_daily.sh → picker → headless claude -p → build_site.py → announce.py → git push`) into `~/hn-explained`, then swap the picker (HN Algolia API instead of GitHub search) and the daily prompt (explain an article/tool, not a repo). The static-site builder and stylesheet carry over with a rebrand (name, orange accent, HN-flavored metadata pills).

**Tech Stack:** Python 3 stdlib only (no pip deps), zsh, launchd, headless Claude Code with the Scrimba Explain MCP tools, GitHub Pages from `docs/`.

## Global Constraints

- Source of truth to copy from: `/Users/ibrahim/trending-explained` (do not modify that repo).
- Project root: `/Users/ibrahim/hn-explained`. Repo `ibrhmvk/hn-explained`, Pages from `docs/` on `main`. Site URL: `https://ibrhmvk.github.io/hn-explained`.
- Site name is exactly `HN, Explained` — never "Hacker News Explained" (YC trademark).
- Tagline: `The day's top Hacker News story, explained visually. Every day. Fully automated.`
- Python stdlib only; tests use `unittest` and run with `python3 -m unittest discover -s tests -v`.
- Claim tokens (`?claim=...`) must never appear in committed files. `data/claim-links.txt`, `data/announce-config.json`, `data/announced.json`, `logs/` stay gitignored.
- launchd job `io.hn-explained.daily` fires at **10:30** (one hour after the trending-explained job — the two headless Claude runs must not overlap).
- Post JSON schema (produced by the prompt, consumed by build_site.py):
  `{ slug, title, story_title, story_url, domain, hn_id, hn_url, date, summary, explainer_url, body_html, points, num_comments }`
  — `story_url` may be null (Ask HN); `explainer_url` may be null; `body_html` is trusted (our own pipeline).

---

### Task 1: Scaffold the repo from trending-explained

**Files:**
- Create: `~/hn-explained/` — copied `scripts/`, `prompts/`, `docs/style.css`, `.gitignore`; fresh `README.md`; empty `data/posts/`, `logs/` dirs.

**Interfaces:**
- Produces: a git repo (already initialized, contains the spec under `docs/superpowers/specs/`) with the untouched copied files that Tasks 2–4 adapt.

- [ ] **Step 1: Copy the pipeline files**

```bash
cd /Users/ibrahim/hn-explained
SRC=/Users/ibrahim/trending-explained
mkdir -p scripts prompts docs data/posts logs tests
cp $SRC/scripts/build_site.py $SRC/scripts/announce.py $SRC/scripts/run_daily.sh scripts/
cp $SRC/scripts/pick_repo.py scripts/pick_story.py
cp $SRC/prompts/daily.md prompts/daily.md
cp $SRC/docs/style.css docs/style.css
cp $SRC/.gitignore .gitignore
```

Note: `docs/index.html`, `docs/p/`, `feed.xml`, `sitemap.xml`, `robots.txt` are NOT copied — `build_site.py` regenerates them from (initially zero) posts.

- [ ] **Step 2: Write README.md**

```markdown
# HN, Explained

The day's top Hacker News story, explained visually. Every day. Fully automated.

Live: https://ibrhmvk.github.io/hn-explained

Sibling of [Repo, Explained](https://ibrhmvk.github.io/trending-explained/). Daily pipeline:
launchd (10:30) → `scripts/run_daily.sh` → `scripts/pick_story.py` (HN Algolia front page,
≥100 points, uncovered) → headless `claude -p prompts/daily.md` (post JSON + Scrimba
explainer) → `scripts/build_site.py` (site + sitemap/RSS/OG/JSON-LD) → `scripts/announce.py`
(Bluesky, optional) → git push. One manual step per post: claim the Scrimba explainer from
`data/claim-links.txt` (gitignored) and set it to link-only visibility.

Tests: `python3 -m unittest discover -s tests -v`
```

- [ ] **Step 3: Verify the tree and commit**

Run: `ls scripts prompts docs data tests && git add -A && git status --short`
Expected: `scripts/{pick_story.py,build_site.py,announce.py,run_daily.sh}`, `prompts/daily.md`, `docs/style.css`, `README.md`, `.gitignore` staged. (`data/posts`, `logs`, `tests` are empty and won't be tracked yet — fine.)

```bash
git commit -m "Scaffold from trending-explained pipeline"
```

---

### Task 2: pick_story.py — HN front-page picker

**Files:**
- Modify: `scripts/pick_story.py` (full rewrite of the copied `pick_repo.py`)
- Test: `tests/test_pick_story.py`

**Interfaces:**
- Produces: CLI that prints a JSON **array** of up to 10 candidate objects `{hn_id: int, title, url: str|null, points: int, num_comments: int, hn_url}` sorted by points desc, or exits with code 3 and no output when there are no eligible candidates. Pure function `eligible(hits, seen_ids, min_points=100)` used by tests. Coverage is keyed on `hn_id` in `data/posts/*.json`.
- Consumes: nothing from other tasks.

The picker does mechanical filtering only (points floor, dedup against covered `hn_id`s). Editorial judgment — technical vs politics/layoffs/paywall — lives in the prompt (Task 4), not here. No keyword filters.

- [ ] **Step 1: Write the failing test**

`tests/test_pick_story.py`:

```python
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pick_story import eligible

HIT = {"objectID": "101", "title": "A story", "url": "https://ex.com/a",
       "points": 250, "num_comments": 90}


def hit(**over):
    h = dict(HIT)
    h.update(over)
    return h


class TestEligible(unittest.TestCase):
    def test_maps_fields(self):
        [c] = eligible([HIT], set())
        self.assertEqual(c, {"hn_id": 101, "title": "A story",
                             "url": "https://ex.com/a", "points": 250,
                             "num_comments": 90,
                             "hn_url": "https://news.ycombinator.com/item?id=101"})

    def test_filters_low_points_and_covered(self):
        hits = [hit(objectID="1", points=99), hit(objectID="2"), hit(objectID="3")]
        got = eligible(hits, seen_ids={3})
        self.assertEqual([c["hn_id"] for c in got], [2])

    def test_sorts_by_points_and_caps_at_10(self):
        hits = [hit(objectID=str(i), points=100 + i) for i in range(15)]
        got = eligible(hits, set())
        self.assertEqual(len(got), 10)
        self.assertEqual(got[0]["points"], 114)

    def test_null_url_kept_and_missing_fields_safe(self):
        [c] = eligible([hit(url=None, points=150, num_comments=None)], set())
        self.assertIsNone(c["url"])
        self.assertEqual(c["num_comments"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL — `ImportError: cannot import name 'eligible'` (file still contains pick_repo code).

- [ ] **Step 3: Write the implementation**

Replace `scripts/pick_story.py` entirely:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Smoke-test against the live API**

Run: `python3 scripts/pick_story.py | python3 -c "import json,sys; c=json.load(sys.stdin); print(len(c), c[0]['title'])"`
Expected: prints a count 1–10 and a real current HN headline. (If it exits 3 because the front page is unusually quiet, rerun with `MIN_POINTS` sanity-checked — but with a 100-point floor on 30 front-page hits this should not happen.)

- [ ] **Step 6: Commit**

```bash
git add scripts/pick_story.py tests/test_pick_story.py
git commit -m "pick_story: HN Algolia front-page candidate picker"
```

---

### Task 3: Rebrand build_site.py + style.css for HN

**Files:**
- Modify: `scripts/build_site.py`, `docs/style.css`, `scripts/announce.py`
- Test: `tests/test_build_site.py`

**Interfaces:**
- Consumes: post JSON files matching the schema in Global Constraints.
- Produces: `docs/index.html`, `docs/p/<slug>.html`, `docs/sitemap.xml`, `docs/feed.xml`, `docs/robots.txt`. Functions `render_index(posts)`, `render_post(p)`, `pills(p)` keep their existing names/signatures.

- [ ] **Step 1: Write the failing test**

`tests/test_build_site.py`:

```python
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_site

POST = {
    "slug": "2026-08-13-example-story",
    "title": "How Example does X without Y",
    "story_title": "Example: X without Y",
    "story_url": "https://example.com/post",
    "domain": "example.com",
    "hn_id": 44001122,
    "hn_url": "https://news.ycombinator.com/item?id=44001122",
    "date": "2026-08-13",
    "summary": "A short summary.",
    "explainer_url": "https://scrimba.com/explain/abc123",
    "body_html": "<h2>Section</h2><p>Body.</p>",
    "points": 512,
    "num_comments": 341,
}


class TestBuildSite(unittest.TestCase):
    def test_branding(self):
        self.assertEqual(build_site.SITE_NAME, "HN, Explained")
        self.assertEqual(build_site.SITE_URL,
                         "https://ibrhmvk.github.io/hn-explained")

    def test_pills_show_hn_metadata(self):
        html = build_site.pills(POST)
        self.assertIn("▲ 512", html)
        self.assertIn('href="https://news.ycombinator.com/item?id=44001122"', html)
        self.assertIn("341 comments", html)
        self.assertIn('href="https://example.com/post"', html)
        self.assertIn("example.com", html)

    def test_pills_survive_null_url_and_bad_points(self):
        p = dict(POST, story_url=None, points=None)
        html = build_site.pills(p)
        self.assertIn("▲ ?", html)
        self.assertNotIn('href="None"', html)

    def test_post_page(self):
        html = build_site.render_post(POST)
        self.assertIn("scrimba.com/explain/abc123", html)
        self.assertIn("controls-cover", html)
        self.assertIn("HN, Explained", html)
        self.assertIn("<h2>Section</h2>", html)

    def test_index_lists_post(self):
        html = build_site.render_index([POST])
        self.assertIn("p/2026-08-13-example-story.html", html)
        self.assertIn("How Example does X without Y", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_build_site -v`
Expected: FAIL — `SITE_NAME` is `"Repo, Explained"`, `pills` KeyErrors on missing `repo`/`stars`.

- [ ] **Step 3: Adapt build_site.py**

Four edits to `scripts/build_site.py` (everything else stays verbatim):

1. Constants + module docstring schema line:

```python
SITE_NAME = "HN, Explained"
TAGLINE = "The day's top Hacker News story, explained visually. Every day. Fully automated."
SITE_URL = "https://ibrhmvk.github.io/hn-explained"
```

2. In `PAGE`, swap the 📦 favicon glyph and header emoji to 🗞️ (two occurrences: the `rel="icon"` data URI's `<text>` content, and `<a class="brand" ...>🗞️ {site}</a>`).

3. Replace `pills()`:

```python
def pills(p, link_out=True):
    points = p.get("points")
    points = f"{points:,}" if isinstance(points, int) else "?"
    src = ""
    if link_out and p.get("story_url"):
        label = esc(p.get("domain") or "source")
        src = (f'<a class="pill" href="{esc(p["story_url"])}" target="_blank" '
               f'rel="noopener">{label} ↗</a>')
    n = p.get("num_comments")
    n = f"{n:,}" if isinstance(n, int) else "?"
    comments = (f'<a class="pill" href="{esc(p["hn_url"])}" target="_blank" '
                f'rel="noopener">{n} comments ↗</a>')
    return (f'<div class="pills"><span class="pill">{esc(p["date"])}</span>'
            f'<span class="pill">▲ {points}</span>{src}{comments}</div>')
```

4. In `og_meta()`, JSON-LD `"about"` becomes `article.get("story_title") or article["title"]`; in `render_post()`, the iframe `title` attribute becomes `title="Interactive explainer: {esc(p['title'])}"` (the `repo` field no longer exists).

- [ ] **Step 4: Retheme style.css accent to HN orange**

In `docs/style.css`, change only the four accent values (light then dark block):

```css
/* light */  --accent: #ea580c; --accent-2: #f59e0b;
/* dark  */  --accent: #fb923c; --accent-2: #fbbf24;
```

- [ ] **Step 5: Update announce.py site URL**

In `scripts/announce.py` line 16: `SITE_URL = "https://ibrhmvk.github.io/hn-explained"`.

- [ ] **Step 6: Run tests, then build the empty site**

Run: `python3 -m unittest discover -s tests -v` — Expected: all 9 tests PASS.
Run: `python3 scripts/build_site.py` — Expected: `built site: 0 post(s)`; `docs/index.html` exists and contains "First post coming soon." and "HN, Explained".

- [ ] **Step 7: Commit**

```bash
git add scripts/build_site.py scripts/announce.py docs/ tests/test_build_site.py
git commit -m "Rebrand site builder for HN, Explained (orange theme, points/comments pills)"
```

---

### Task 4: Daily prompt + run_daily.sh

**Files:**
- Modify: `prompts/daily.md` (full rewrite), `scripts/run_daily.sh` (small edits)

**Interfaces:**
- Consumes: candidate JSON array from `pick_story.py` (Task 2), appended below the prompt text by `run_daily.sh`.
- Produces: headless Claude writes one post JSON to `data/posts/<YYYY-MM-DD>-<slug>.json` matching the Global Constraints schema, plus a claim link appended to `data/claim-links.txt`.

- [ ] **Step 1: Rewrite prompts/daily.md**

```markdown
You are the daily content pipeline for "HN, Explained" — a site that explains the day's top technical Hacker News story. Work from the project root at ~/hn-explained. Today's candidate stories are given as a JSON array at the bottom of this prompt, sorted by points.

Do the following, in order:

1. **Pick ONE story** — the highest-ranked candidate that is *technical and explainable*: an article, paper, tool, library, protocol, or engineering write-up whose core idea benefits from a visual walkthrough. Skip candidates that are: politics/policy, layoffs/funding/company drama, obituaries, legal news, or paywalled pages you cannot fetch. Ask HN / Show HN are fine if there's real substance to explain. If NO candidate qualifies, write nothing and exit stating why.

2. **Research the story.** Fetch the linked article (if `url` is null, it's a self-post — fetch the HN item text instead) and skim the HN comment thread (`https://hn.algolia.com/api/v1/items/<hn_id>`) for the top few insightful comments. Understand: what the thing is, how it works at a high level, why HN cares today, and one genuinely interesting technical detail (the comments often surface it).

3. **Create a Scrimba explainer** using the mcp__claude_ai_Explain__* tools (start_explainer_stream, append_explainer_chunk, finish_explainer_stream). Make it a focused 4–7 section walkthrough of the *idea behind the story*: the problem, the core concept/architecture (use a mermaid diagram), the most interesting mechanism or code, and why it matters. Save the explainer's public URL — but strip any `?claim=...` query string before publishing it (the claim token is private; write the bare `https://scrimba.com/explain/<id>` URL into the post, and append the full claim link to `data/claim-links.txt` instead).
   - If the Scrimba tools are unavailable or error out twice, continue WITHOUT an explainer and set `explainer_url` to null.

4. **Write the article** as a JSON file at `data/posts/<YYYY-MM-DD>-<slug>.json` (slug: lowercase, dashes only, derived from the story's subject). Fields:
   - `slug`: "<YYYY-MM-DD>-<slug>"
   - `title`: a specific, curiosity-driven title (not clickbait) — your own, not the HN headline
   - `story_title`: the original HN headline
   - `story_url`: the candidate's `url` (null for self-posts)
   - `domain`: the bare domain of story_url, e.g. "example.com" (null if story_url is null)
   - `hn_id`, `hn_url`, `points`, `num_comments`: from the candidate JSON
   - `date`: today, YYYY-MM-DD
   - `summary`: 1–2 sentences, plain text
   - `explainer_url`: the Scrimba URL or null
   - `body_html`: the article as clean HTML fragments (h2/p/pre/code/ul only, no h1, no inline styles). 500–900 words. Structure: what it is and why HN cares today → how it actually works (with one short concrete example or code excerpt) → the interesting detail the comments surfaced → who should care. Write like a sharp engineer explaining to a peer, not like marketing copy. Link the original article and the HN thread naturally in the text.

5. **Verify** the JSON parses: `python3 -c "import json; json.load(open('data/posts/<file>'))"`.

Do NOT run git commands or the site build — the wrapper script handles those. Your only outputs are the Scrimba explainer and the post JSON file.

Today's candidates:
```

- [ ] **Step 2: Adapt run_daily.sh**

Three edits to `scripts/run_daily.sh` (copied file is otherwise correct):
- Comment header: `# Daily pipeline: pick HN story -> generate explainer + article (headless Claude)`
- `REPO_JSON="$(python3 scripts/pick_repo.py)" || { echo "no new repo to cover"; exit 0; }` becomes:

```zsh
CANDIDATES_JSON="$(python3 scripts/pick_story.py)" || { echo "no eligible story today"; exit 0; }
echo "candidates: $CANDIDATES_JSON"

PROMPT="$(cat prompts/daily.md)
$CANDIDATES_JSON"
```

(The `claude -p` invocation, `--allowedTools` list, build/announce/push block stay exactly as copied.)

- [ ] **Step 3: Verify shell syntax and dry-run the picker path**

Run: `zsh -n scripts/run_daily.sh && python3 scripts/pick_story.py >/dev/null && echo ok`
Expected: `ok` (or exit 3 from the picker, which run_daily treats as a clean no-op day).

- [ ] **Step 4: Commit**

```bash
git add prompts/daily.md scripts/run_daily.sh
git commit -m "Daily prompt + runner for HN stories"
```

---

### Task 5: GitHub repo, Pages, and first end-to-end run

**Files:**
- No source changes; creates `data/posts/<first post>.json`, regenerated `docs/`, remote repo.

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: the live site with post #1.

- [ ] **Step 1: Create the remote and push**

```bash
cd /Users/ibrahim/hn-explained
gh repo create ibrhmvk/hn-explained --public --source . --push
```

- [ ] **Step 2: Enable GitHub Pages from docs/**

```bash
gh api -X POST repos/ibrhmvk/hn-explained/pages \
  -f "source[branch]=main" -f "source[path]=/docs"
```

Expected: 201. (409 means already enabled — fine.)

- [ ] **Step 3: Manual end-to-end run**

Run: `zsh scripts/run_daily.sh && tail -20 logs/$(date +%F).log`
Expected: log shows candidates picked, Claude run completed, `built site: 1 post(s)`, `published`. This takes several minutes (headless Claude writes the article and streams the Scrimba explainer).

- [ ] **Step 4: Verify the acceptance checklist**

- `python3 -c "import json,glob; p=json.load(open(glob.glob('data/posts/*.json')[0])); [p[k] for k in ('slug','title','story_title','hn_id','hn_url','date','summary','body_html','points','num_comments')]; print('schema ok')"` → `schema ok`
- `grep -c "claim=" data/posts/*.json docs/p/*.html docs/index.html; echo "---"; git status --short` → all zero matches for `claim=` in committed files; working tree clean.
- `cat data/claim-links.txt` → contains the full claim link (Ibrahim's manual step: claim it, set link-only visibility).
- Open `https://ibrhmvk.github.io/hn-explained/` in a browser (Pages deploys can lag a couple of minutes): post renders, pills show date / ▲ points / domain / comments, Scrimba iframe loads with the hover-reveal controls cover. **Judge the embed by eye, never by screenshot** — cross-origin iframes screenshot black.
- `curl -s https://ibrhmvk.github.io/hn-explained/feed.xml | python3 -c "import sys,xml.dom.minidom; xml.dom.minidom.parseString(sys.stdin.read()); print('rss ok')"` and same for `sitemap.xml` → both parse.

- [ ] **Step 5: Report to Ibrahim**

Surface: the live post URL, the claim link reminder, and anything that needed manual intervention during the run.

---

### Task 6: launchd automation

**Files:**
- Create: `~/Library/LaunchAgents/io.hn-explained.daily.plist`

**Interfaces:**
- Consumes: `scripts/run_daily.sh` (Task 4), proven end-to-end (Task 5).
- Produces: unattended daily runs at 10:30.

- [ ] **Step 1: Write the plist**

`~/Library/LaunchAgents/io.hn-explained.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>io.hn-explained.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>/Users/ibrahim/hn-explained/scripts/run_daily.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>10</integer>
    <key>Minute</key>
    <integer>30</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/ibrahim/hn-explained/logs/launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/ibrahim/hn-explained/logs/launchd.log</string>
</dict>
</plist>
```

- [ ] **Step 2: Validate and load**

```bash
plutil -lint ~/Library/LaunchAgents/io.hn-explained.daily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/io.hn-explained.daily.plist
launchctl print gui/$(id -u)/io.hn-explained.daily | head -5
```

Expected: `OK`, then the print output shows the job loaded with the calendar trigger.

- [ ] **Step 3: Commit a copy of the plist for reference**

```bash
cd /Users/ibrahim/hn-explained
mkdir -p notes && cp ~/Library/LaunchAgents/io.hn-explained.daily.plist notes/
git add notes/ && git commit -m "Record launchd plist" && git push -q origin main
```

Ibrahim confirms the next scheduled 10:30 run completes unattended (check `logs/` the following day).
