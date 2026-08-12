#!/bin/zsh
# Daily pipeline: pick HN story -> generate explainer + article (headless Claude)
# -> rebuild site -> push. Invoked by launchd; safe to run manually.
set -uo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="logs/$(date +%F).log"
exec >>"$LOG" 2>&1
echo "=== run_daily $(date) ==="

CANDIDATES_JSON="$(python3 scripts/pick_story.py)" || { echo "no eligible story today"; exit 0; }
echo "candidates: $CANDIDATES_JSON"

PROMPT="$(cat prompts/daily.md)
$CANDIDATES_JSON"

claude -p "$PROMPT" \
  --allowedTools "Read,Write,Edit,WebFetch,WebSearch,ToolSearch,Bash(python3:*),Bash(curl:*),mcp__claude_ai_Explain__start_explainer_stream,mcp__claude_ai_Explain__append_explainer_chunk,mcp__claude_ai_Explain__finish_explainer_stream" \
  || { echo "claude run failed"; exit 1; }

python3 scripts/build_site.py
python3 scripts/announce.py || true

if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "post: $(date +%F)" -q
  git push -q origin main
  echo "published"
else
  echo "nothing new to publish"
fi
