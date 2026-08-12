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
