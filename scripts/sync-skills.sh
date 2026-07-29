#!/usr/bin/env bash
# Mirror the live spinup skills from ~/.claude/skills into this repo, then commit and push.
# Wired as a Stop hook in ~/.claude/settings.json, so it runs at the end of every turn.
#
# Design decisions, each deliberate:
#   * The set of skills to sync is derived from the directories already in repo/skills/.
#     A brand-new skill has to be copied in once by hand, which is what keeps the 12
#     unrelated Panacea ops skills in ~/.claude/skills out of this repo.
#   * A skill missing from ~/.claude/skills is LOGGED, never deleted from the repo. An
#     accidental rm in the live dir must not silently delete the only backup. Real
#     deletions are rare and deliberate, so they are done by hand (with a commit).
#   * Only `skills/` is staged, never `git add -A`. Two sessions have edited this repo
#     concurrently; sweeping the whole tree would commit someone else's in-flight work.
#   * Always exits 0 and prints nothing on success. A backup hook must never fail a turn.
#   * GIT_CONFIG_NOSYSTEM=1 because a stale /Volumes/Ryu entry in the system git config
#     hangs every git call in this workspace.

set -uo pipefail
export GIT_CONFIG_NOSYSTEM=1

REPO="$HOME/Desktop/MERCOR/new-project-spinup"
LIVE="$HOME/.claude/skills"
LOG="$REPO/.sync-skills.log"
LOCK="$REPO/.sync-skills.lock"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*" >>"$LOG" 2>/dev/null || true; }

[ -d "$REPO/.git" ] || exit 0
[ -d "$LIVE" ] || exit 0
[ -d "$REPO/skills" ] || exit 0

# mkdir is atomic, and macOS has no flock. A stale lock older than 5 minutes is cleared.
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +5 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null || true
    mkdir "$LOCK" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

cd "$REPO" || exit 0

missing=""
for dir in skills/*/; do
  name="${dir%/}"; name="${name#skills/}"
  if [ -d "$LIVE/$name" ]; then
    rsync -a --delete --exclude '.DS_Store' --exclude '._*' --exclude 'spinup.env' \
      "$LIVE/$name/" "$REPO/skills/$name/" 2>/dev/null || log "rsync FAILED for $name"
  else
    missing="$missing $name"
  fi
done
[ -n "$missing" ] && log "not in live dir, left in repo (delete by hand if intended):$missing"

# Nothing to do is the common case. Stay silent.
git add -A skills/ 2>/dev/null || exit 0
git diff --cached --quiet 2>/dev/null && exit 0

changed=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
git -c user.name="Ryu Go-eun" -c user.email="ryugo-eun@mercor.com" \
  commit -q -m "chore(skills): sync $changed file(s) from ~/.claude/skills

Automated by the Stop hook (scripts/sync-skills.sh)." 2>/dev/null || {
  log "commit FAILED"; exit 0; }

log "committed $changed file(s)"

# Push only from main, and never fail the turn over it. An unpushed commit is
# picked up by the next run.
[ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" = "main" ] || { log "not on main, not pushed"; exit 0; }
if git push -q origin main 2>/dev/null; then
  log "pushed"
else
  log "push FAILED (offline?), commit is local and will go with the next run"
fi
exit 0
