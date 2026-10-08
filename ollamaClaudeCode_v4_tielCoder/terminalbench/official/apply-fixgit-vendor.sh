#!/usr/bin/env bash
# apply-fixgit-vendor.sh -- make terminal-bench-core 0.1.1's fix-git buildable again.
#
# fix-git's setup.sh clones https://github.com/TheMikeMerrill/personal-site.git and
# resets to d7d3e4b. That repo returns 404 since ~2026-10-08 (account exists, repo
# gone), so every build fails and every trial is booked unknown_agent_error (VOID).
# Upstream (terminal-bench original-tasks/, and terminal-bench-2) still clones it.
#
# The fix is byte-faithful: Terminal-Bench 2.0 publishes a prebuilt image,
# alexgshaw/fix-git:20251031, built from the IDENTICAL setup.sh and patch files
# (same git blob ids). Its reflog shows the clone came in at the repo's then tip
# b0d59cd ("Update email", 2025-03-10), of which the pinned d7d3e4b is an
# ancestor. We export that history, with b0d59cd as master, as a git bundle into
# the task's resources/ and clone from it instead of GitHub, so the clone, the
# reset and the reflog the agent can inspect match the original build. Every
# later step of setup.sh (reset to d7d3e4b, the "Move to Stanford" commit, the
# detached work the agent must recover) is unchanged. The bundle is deleted in
# the same RUN layer, so the agent sees the same /app as before.
#
# Idempotent: re-running changes nothing once applied.
set -euo pipefail
TASK="${TASK_DIR:-$HOME/.cache/terminal-bench/terminal-bench-core/0.1.1/fix-git}"
IMG="alexgshaw/fix-git:20251031"
TIP="b0d59cded7105fea91a4ea0008098295d8895786"   # the clone's master
PIN="d7d3e4ba9350f634d92d39ace2b471433ee57d50"   # what setup.sh resets to
URL="https://github.com/TheMikeMerrill/personal-site.git"
B="$TASK/resources/personal-site.bundle"

[ -f "$TASK/setup.sh" ] || { echo "no fix-git task at $TASK"; exit 4; }
if [ ! -s "$B" ]; then
  tmp="$(mktemp -d)"
  docker pull -q "$IMG" >/dev/null
  docker run --rm --network none -v "$tmp:/out" "$IMG" bash -c \
    'cd /app/personal-site && git update-ref refs/heads/master '"$TIP"' && git bundle create /out/personal-site.bundle master'
  cp "$tmp/personal-site.bundle" "$B"; rm -rf "$tmp"
fi
# the bundle's master must be the original clone tip, or the task is not the same task
head="$(git bundle list-heads "$B" | awk '$2=="refs/heads/master"{print $1}')"
[ "$head" = "$TIP" ] || { echo "bundle master is $head, expected $TIP (delete $B to re-export)"; exit 5; }

if grep -qF "git clone $URL" "$TASK/setup.sh"; then
  [ -f "$TASK/setup.sh.orig" ] || cp "$TASK/setup.sh" "$TASK/setup.sh.orig"
  # clone from the bundle, restore the original URL in the clone's reflog line (the
  # agent may read the reflog), and drop the bundle in the same RUN layer
  sed -i "s|^git clone $URL\$|git clone /app/resources/personal-site.bundle personal-site \&\& sed -i 's#clone: from /app/resources/personal-site.bundle#clone: from $URL#' personal-site/.git/logs/HEAD personal-site/.git/logs/refs/heads/master \&\& rm -f /app/resources/personal-site.bundle|" "$TASK/setup.sh"
fi
grep -qF "clone: from $URL#' personal-site/.git/logs/HEAD" "$TASK/setup.sh" || { echo "patch not applied"; exit 6; }
echo "fix-git vendored: bundle master $TIP (reset to $PIN by setup.sh), setup.sh clones from it"
