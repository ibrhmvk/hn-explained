# HN, Explained — Design Spec

Date: 2026-08-13
Status: Approved (brainstorm with Ibrahim)

## Goal

A sibling site to **Repo, Explained** (https://ibrhmvk.github.io/trending-explained/): one automated post per day explaining the day's top technical Hacker News story, with a Scrimba explainer embedded in an iframe. Same passive-income model — fully automated, no client work; Scrimba claim-link remains the single manual step per post.

## Decisions made

- **Separate repo + site**, not a section of trending-explained. Repo `ibrhmvk/hn-explained`, GitHub Pages from `docs/`, live at `ibrhmvk.github.io/hn-explained`. Local checkout: `~/hn-explained`.
- **Story selection:** top *technical/explainable* front-page story (article, paper, tool) — skip politics, layoffs, drama, paywalled news. Not strictly #1, not Show-HN-only.
- **Fully automated daily** via launchd, mirroring the existing pipeline.
- **Name:** "HN, Explained" — matches the sibling brand and avoids the "Hacker News" / YC trademark in the site name.

## Approach

Copy `~/trending-explained` to `~/hn-explained` and adapt (Approach A from brainstorm). Keep the proven skeleton:

```
launchd io.hn-explained.daily (10:30)
  → run_daily.sh
    → pick_story.py           (candidates from HN Algolia API)
    → headless claude -p prompts/daily.md   (post JSON + Scrimba explainer)
    → build_site.py           (site + sitemap/RSS/OG/JSON-LD)
    → announce.py             (Bluesky; skips until data/announce-config.json exists)
    → git push
```

A shared-engine refactor across both sites was rejected (YAGNI until a third site exists).

## Components

### pick_story.py (new, replaces pick_repo.py)

- Query `https://hn.algolia.com/api/v1/search?tags=front_page` for current front-page stories.
- Filter: score ≥ 100; story ID not already covered (post files in `data/posts/` keyed by HN story ID).
- Output the remaining candidates (id, title, url, points, comment count) for the daily prompt. **Technical/explainable classification is NOT done here** — no keyword filters. The picker only does mechanical filtering; editorial judgment lives in the prompt.
- If no eligible candidates: log and exit non-zero (no post today; retries tomorrow).

### prompts/daily.md (new, adapted from repo version)

- From the candidate list, pick the most explainable technical story; skip politics/layoffs/paywalled news.
- Fetch the story's article and top HN comments for context.
- Write post JSON to `data/posts/`: title, summary, why-it-matters, HN story ID, links to both the article and the HN comments thread, points/comment count at time of writing.
- Create a Scrimba explainer via `mcp__claude_ai_Explain__*` explaining the concept/tool/paper behind the story; store the embed URL in the post JSON.
- Append the claim link to `data/claim-links.txt` (gitignored — claim tokens must never be published).

### build_site.py + style.css (carried over, rethemed)

- Same layout, design language, and SEO plumbing: sitemap.xml, feed.xml (RSS), OG tags, JSON-LD, robots.txt.
- Keep the `.controls-cover` iframe mask (52px hover-reveal) over the Scrimba player.
- Changes: site name "HN, Explained", new accent color, post metadata shows HN points + link to comments instead of GitHub stars.
- AD SLOT placeholder retained for future monetization.

### run_daily.sh + launchd (carried over)

- `io.hn-explained.daily` at **10:30** (one hour after `io.trending-explained.daily` at 09:30 so headless Claude runs never overlap).
- Same logging pattern to `logs/`.

### announce.py (carried over)

- Bluesky announce; skips until `data/announce-config.json` exists (Ibrahim owns creds).

## Error handling

Same posture as trending-explained: any stage failure (no eligible story, Claude run fails, build fails) logs and exits without publishing a partial post. Next day's run retries naturally. Nothing is pushed unless the build completes.

## Known gotchas (inherited)

- Scrimba explainers are login-walled until claimed and set to link-only visibility — the one manual step per post.
- Chrome-extension screenshots render cross-origin iframes black; never conclude an embed is broken from a screenshot.
- No autoplay: Scrimba has no autoplay param and browsers block narrated audio autoplay.
- `.controls-cover` is pixel-tuned to Scrimba's UI; retune if they redesign.

## Testing / acceptance

- One manual end-to-end run before loading the launchd job.
- Verify: post renders on the site, Scrimba iframe embeds (checked by eye, not screenshot), points + comments link correct, RSS and sitemap validate, claim link written to gitignored file, git push succeeds.
- Then load launchd and confirm the next scheduled run completes unattended.

## Out of scope

- Shared engine refactor with trending-explained.
- Bluesky credentials, Search Console registration, custom domain, ads — Ibrahim owns these later (same open items as the sibling site).
