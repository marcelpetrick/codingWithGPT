#!/usr/bin/env bash
# cleaner.sh - Manjaro/Arch maintenance: measure, free space, upgrade, clean up.
#
# Usage: ./cleaner.sh [prepare|upgrade|clean|all] [options]
#
#   prepare   measure the partitions and trim the package cache BEFORE upgrading
#   upgrade   pacman + yay (AUR/devel) + snap + flatpak
#   clean     post-upgrade leftovers: cache, orphans, .pacnew, snaps, runtimes
#   all       all three, in that order (default)
#
# Options:
#   -n, --dry-run      print every command instead of running it
#   -y, --yes          do not ask before destructive steps
#       --user-cache   additionally purge the disposable parts of ~/.cache
#       --keep N       package cache versions to keep per package (default 1)
#   -h, --help         show this text
#
# Every step announces what it is about to do and why, then reports how long it
# took and how much space it reclaimed. A summary table follows at the end.
#
# Why 'prepare' runs first: the package cache lives on / and routinely grows
# larger than the free space a big -Syu needs. Cleaning up afterwards is too
# late - the transaction has already run out of disk by then.
#
# Author: Marcel Petrick <mail@marcelpetrick.it>
# License: GPLv3 or later.

set -euo pipefail

# ---- config ----
KEEP_VERSIONS=1          # package cache versions to retain (rollback safety net)
MIN_FREE_GIB=6           # refuse to start an upgrade below this much free on /
SNAP_RETAIN=2            # snap revisions to keep from here on
JOURNAL_MAX="100M"       # cap the systemd journal at this size

DRY_RUN=0
ASSUME_YES=0
CLEAN_USER_CACHE=0
MODE="all"

# ---- output helpers ----
if [ -t 1 ]; then
  GREEN="\033[1;32m"; YELLOW="\033[1;33m"; BLUE="\033[1;34m"
  RED="\033[1;31m";   DIM="\033[2m";       BOLD="\033[1m";  RESET="\033[0m"
else
  GREEN=""; YELLOW=""; BLUE=""; RED=""; DIM=""; BOLD=""; RESET=""
fi

banner()  { echo -e "\n${BLUE}${BOLD}=========================================================${RESET}"
            echo -e "${BLUE}${BOLD}  $1${RESET}"
            echo -e "${BLUE}${BOLD}=========================================================${RESET}"; }
status()  { echo -e "${YELLOW}  -> $1${RESET}"; }
detail()  { echo -e "${DIM}     $1${RESET}"; }
success() { echo -e "${GREEN}  OK $1${RESET}"; }
warn()    { echo -e "${RED}  !! $1${RESET}"; }
err()     { echo -e "${RED}Error: $*${RESET}" >&2; exit 1; }

# Indent a multi-line block of piped-in text.
# shellcheck disable=SC2001  # sed is the clearest way to indent every line
indent()  { sed 's/^/       /'; }

# Run a command, or print it when --dry-run is active.
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    echo -e "${DIM}     [dry-run] $*${RESET}"
  else
    echo -e "${DIM}     \$ $*${RESET}"
    "$@"
  fi
}

# Ask before anything destructive. --yes and --dry-run skip the prompt; without
# a terminal we decline rather than silently destroying something.
confirm() {
  [ "$ASSUME_YES" -eq 1 ] && return 0
  [ "$DRY_RUN" -eq 1 ] && return 0
  if [ ! -t 0 ]; then
    warn "no terminal to ask on - skipping (use --yes to allow this non-interactively)"
    return 1
  fi
  local answer
  read -r -p "$(echo -e "${YELLOW}  ?? $1 [y/N] ${RESET}")" answer
  [[ "$answer" =~ ^[Yy]$ ]]
}

# A safety gate, not a convenience prompt: --yes deliberately does NOT bypass
# this, because the whole point of the check is to stop an unattended run from
# half-upgrading a full disk.
confirm_risky() {
  if [ "$DRY_RUN" -eq 1 ]; then
    warn "dry-run: would require explicit confirmation here"
    return 0
  fi
  if [ ! -t 0 ]; then
    warn "no terminal to confirm on, and --yes does not apply to safety checks"
    return 1
  fi
  local answer
  read -r -p "$(echo -e "${RED}  ?? $1 [y/N] ${RESET}")" answer
  [[ "$answer" =~ ^[Yy]$ ]]
}

usage() { sed -n '2,20p' "$0" | sed 's/^# \?//'; exit 0; }

# ---- measurement helpers ----
avail_bytes() { df -B1 --output=avail "$1" | tail -1 | tr -dc '0-9'; }
human()       { numfmt --to=iec --suffix=B "${1:-0}" 2>/dev/null || echo "${1}B"; }

# Seconds -> "1m 23s"
duration() {
  local s="$1"
  if [ "$s" -ge 60 ]; then echo "$((s / 60))m $((s % 60))s"; else echo "${s}s"; fi
}

# Signed byte delta -> "freed 3.3GB" / "used 412MB" / "no change"
delta() {
  local d="$1"
  if   [ "$d" -gt 1048576 ]; then echo "freed $(human "$d")"
  elif [ "$d" -lt -1048576 ]; then echo "used $(human "$((-d))")"
  else echo "no measurable change"; fi
}

STEP_NO=0
SUMMARY=()
TOTAL_T0=$(date +%s)
ROOT_FREE_START=$(avail_bytes /)

# step_start <title> <plain-language explanation> [mount to measure, default /]
# The mount matters: ~/.cache lives on /home, so measuring those steps against
# / would report "no change" for a step that freed gigabytes.
step_start() {
  STEP_NO=$((STEP_NO + 1))
  STEP_TITLE="$1"
  STEP_MOUNT="${3:-/}"
  STEP_T0=$(date +%s)
  STEP_FREE0=$(avail_bytes "$STEP_MOUNT")
  echo
  echo -e "${BOLD}[$STEP_NO] $STEP_TITLE${RESET}"
  echo "$2" | fmt -w 72 | sed 's/^/     /'
  echo
}

step_end() {
  local elapsed=$(( $(date +%s) - STEP_T0 ))
  local freed=$(( $(avail_bytes "$STEP_MOUNT") - STEP_FREE0 ))
  local mount_label; mount_label="$(df --output=target "$STEP_MOUNT" | tail -1)"
  echo -e "${GREEN}  == step $STEP_NO done in $(duration "$elapsed") - $(delta "$freed") on $mount_label${RESET}"
  SUMMARY+=("$(printf '%-44s %8s  %-22s %s' \
    "$STEP_TITLE" "$(duration "$elapsed")" "$(delta "$freed")" "$mount_label")")
}

# Print the current partition situation.
show_disks() {
  df -h / /home 2>/dev/null | sed 's/^/     /'
}

# ---- sanity checks ----
[ "$(id -u)" -ne 0 ] || err "do not run this as root - it calls sudo where needed, and yay refuses to build as root"
command -v pacman >/dev/null 2>&1 || err "this script is for Arch/Manjaro (pacman not found)"
command -v paccache >/dev/null 2>&1 || err "paccache is missing. Install it with: sudo pacman -S pacman-contrib"

# ---- args ----
while [ $# -gt 0 ]; do
  case "$1" in
    prepare|upgrade|clean|all) MODE="$1" ;;
    -n|--dry-run)   DRY_RUN=1 ;;
    -y|--yes)       ASSUME_YES=1 ;;
    --user-cache)   CLEAN_USER_CACHE=1 ;;
    --keep)         shift; KEEP_VERSIONS="${1:-1}" ;;
    -h|--help)      usage ;;
    *)              err "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

case "$KEEP_VERSIONS" in
  ''|*[!0-9]*) err "--keep expects a number, got: $KEEP_VERSIONS" ;;
esac

STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/systemCleaner"
mkdir -p "$STATE_DIR"

# =============================================================================
# PREPARE
# =============================================================================
do_prepare() {
  banner "PHASE 1 of 3 - PREPARE: measure, then make room"

  step_start "Measure partition usage (before)" \
"Recording the starting point so the numbers at the end mean something. \
/ holds the system and the package cache; /home holds your data and the \
per-user caches. Only / matters for whether the upgrade fits."
  { date -Is; df -h / /home; } > "$STATE_DIR/disk-before.txt"
  show_disks
  step_end

  step_start "Trim the package cache" \
"pacman never deletes a package it downloaded, so /var/cache/pacman/pkg keeps \
growing forever. Keeping $KEEP_VERSIONS older version per package preserves your ability to \
downgrade a broken update, and everything older than that is dead weight. \
This runs BEFORE the upgrade because the upgrade downloads into this same \
directory, on the same partition."
  detail "cache is currently $(du -sh /var/cache/pacman/pkg 2>/dev/null | cut -f1) across $(find /var/cache/pacman/pkg -maxdepth 1 -name '*.pkg.tar*' 2>/dev/null | wc -l) files"
  detail "dry-run says: $(paccache -dk"$KEEP_VERSIONS" 2>&1 | tail -1 | sed 's/^==> //')"
  if confirm "Trim the package cache to $KEEP_VERSIONS version(s) per package?"; then
    run sudo paccache -rk"$KEEP_VERSIONS"
    status "also dropping cached packages that are not installed at all"
    run sudo paccache -ruk0
  else
    warn "skipped - package cache left as it is"
  fi
  step_end

  step_start "Check there is room to upgrade" \
"A pacman transaction that runs out of disk halfway through leaves the system \
in a half-upgraded state, which is exactly the situation this script exists to \
avoid. The threshold is ${MIN_FREE_GIB}GB free on /."
  local avail; avail=$(avail_bytes /)
  local avail_gib=$(( avail / 1073741824 ))
  if [ "$avail_gib" -lt "$MIN_FREE_GIB" ]; then
    warn "/ has only ${avail_gib}GB free, below the ${MIN_FREE_GIB}GB threshold"
    warn "consider: --keep 0, or moving large files off /"
    confirm_risky "Continue anyway?" || err "aborted - / is too full to upgrade safely"
  else
    success "/ has ${avail_gib}GB free - enough to proceed"
  fi
  step_end
}

# =============================================================================
# UPGRADE
# =============================================================================
do_upgrade() {
  banner "PHASE 2 of 3 - UPGRADE: repositories, AUR, snap, flatpak"

  step_start "Refresh the sudo timestamp" \
"AUR packages can take many minutes to compile. Asking for the password now \
means the build does not stall on a re-prompt halfway through."
  run sudo -v
  step_end

  step_start "Upgrade official repository packages" \
"pacman -Syu synchronises the package databases and upgrades everything from \
the Manjaro repositories. Note this is -Syu and not -Syyu: the doubled -y \
force-redownloads every database even when nothing changed, which only helps \
after switching mirrors or branch, and otherwise just wastes bandwidth."
  if command -v checkupdates >/dev/null 2>&1; then
    local pending; pending="$(checkupdates 2>/dev/null || true)"
    if [ -n "$pending" ]; then
      detail "$(echo "$pending" | wc -l) package(s) pending:"
      echo "$pending" | head -20 | indent
      [ "$(echo "$pending" | wc -l)" -gt 20 ] && detail "... and more"
    else
      detail "no repository updates pending - this will be a no-op"
    fi
  fi
  run sudo pacman -Syu
  step_end

  if command -v yay >/dev/null 2>&1; then
    step_start "Upgrade AUR packages (including -git/devel)" \
"--devel makes yay check the upstream git revision of -git packages instead of \
trusting their pkgver, so development packages actually get rebuilt. \
--answerclean All always builds in a clean directory. --answerdiff None skips \
paging through PKGBUILD diffs. Deliberately NOT --noconfirm: the final \
transaction, including any package removals or replacements it wants to make, \
stays visible for you to approve."
    run yay -Syu --devel --answerclean All --answerdiff None --answeredit None
    step_end
  fi

  if command -v snap >/dev/null 2>&1; then
    step_start "Refresh snap packages" \
"Updates installed snaps. This deliberately does not free space - snap keeps \
the previous revision mounted as a loop device so it can roll back. Phase 3 \
prunes those."
    run sudo snap refresh
    step_end
  fi

  if command -v flatpak >/dev/null 2>&1; then
    step_start "Update flatpak applications" \
"Updates flatpak apps and their runtimes. Superseded runtimes are left behind \
as orphans and get removed in phase 3."
    run flatpak update -y
    step_end
  fi
}

# =============================================================================
# CLEAN
# =============================================================================
do_clean() {
  banner "PHASE 3 of 3 - CLEAN: the leftovers an upgrade creates"

  step_start "Trim the package cache again" \
"The upgrade just refilled /var/cache/pacman/pkg with everything it downloaded, \
and the versions it replaced are now stale. Same rule as before: keep \
$KEEP_VERSIONS version per package as a rollback path, drop the rest."
  run sudo paccache -rk"$KEEP_VERSIONS"
  run sudo paccache -ruk0
  step_end

  if [ -d "$HOME/.cache/yay" ]; then
    # shellcheck disable=SC2088  # the tilde is prose for the reader, not a path
    step_start "Clear AUR build trees" \
"~/.cache/yay holds the cloned sources and compiled artefacts of every AUR \
package built. All of it is re-clonable from upstream on the next build, so \
none of it is worth keeping. Note this lives on /home, not /."
    detail "currently $(du -sh "$HOME/.cache/yay" 2>/dev/null | cut -f1)"
    run rm -rf "${HOME:?}/.cache/yay/"*
    step_end
  fi

  step_start "Review orphaned packages" \
"Orphans are packages that were pulled in as a dependency of something that has \
since been removed or rebuilt against a newer library. Nothing on the system \
requires them any more. They are listed rather than deleted, because a package \
you installed intentionally can look like an orphan if it was never marked as \
explicitly installed."
  local orphans
  orphans="$(pacman -Qtdq 2>/dev/null || true)"
  if [ -n "$orphans" ]; then
    local count; count=$(echo "$orphans" | wc -l)
    detail "$count orphan(s) found:"
    while read -r pkg; do
      [ -n "$pkg" ] || continue
      printf '       %-42s %s\n' "$pkg" "$(pacman -Qi "$pkg" 2>/dev/null | awk -F': ' '/^Installed Size/{print $2}')"
    done <<< "$orphans"
    if confirm "Remove these $count orphan(s)?"; then
      # -Rns: remove the packages, their now-unneeded dependencies, and their
      # config files. Word splitting on the newline-separated list is intended.
      # shellcheck disable=SC2046
      run sudo pacman -Rns $(echo "$orphans" | tr '\n' ' ')
    else
      warn "skipped - orphans kept"
    fi
  else
    success "no orphaned packages"
  fi
  step_end

  step_start "Check for .pacnew config leftovers" \
"When an upgrade ships a new default config for a file you have edited, pacman \
writes it alongside as .pacnew rather than overwriting your version. Left \
unmerged these quietly accumulate, and you miss new upstream defaults."
  local pacnew
  pacnew="$(find /etc -name '*.pacnew' -o -name '*.pacsave' 2>/dev/null || true)"
  if [ -n "$pacnew" ]; then
    warn "$(echo "$pacnew" | wc -l) file(s) need attention:"
    echo "$pacnew" | indent
    if command -v pacdiff >/dev/null 2>&1 && confirm "Run pacdiff to merge them interactively?"; then
      run sudo pacdiff
    else
      warn "run 'sudo pacdiff' when you have time"
    fi
  else
    success "no .pacnew/.pacsave files - configuration is in sync"
  fi
  step_end

  if command -v snap >/dev/null 2>&1; then
    step_start "Prune old snap revisions" \
"snap keeps superseded revisions mounted as loop devices indefinitely. Capping \
retention at $SNAP_RETAIN keeps one rollback target, and the already-disabled revisions \
below are pure waste."
    run sudo snap set system refresh.retain="$SNAP_RETAIN"
    local disabled; disabled="$(snap list --all 2>/dev/null | awk '/disabled/{print $1, $3}' || true)"
    if [ -n "$disabled" ]; then
      detail "disabled revisions to remove:"
      echo "$disabled" | indent
      while read -r name rev; do
        [ -n "$name" ] || continue
        run sudo snap remove "$name" --revision="$rev"
      done <<< "$disabled"
    else
      success "no disabled snap revisions"
    fi
    step_end
  fi

  if command -v flatpak >/dev/null 2>&1; then
    step_start "Remove unused flatpak runtimes" \
"Runtimes and SDK extensions that no installed application references any more. \
Flatpak does not collect these on its own."
    run flatpak uninstall --unused -y
    step_end
  fi

  step_start "Cap the systemd journal" \
"Logs grow without bound until a size or time limit is set. Capping at \
$JOURNAL_MAX keeps enough history to debug a recent problem without letting the \
journal quietly eat the root partition."
  detail "currently: $(journalctl --disk-usage 2>/dev/null | sed 's/^Archived and active journals take up //')"
  run sudo journalctl --vacuum-size="$JOURNAL_MAX"
  step_end

  if [ "$CLEAN_USER_CACHE" -eq 1 ]; then
    do_user_cache
  else
    echo
    # shellcheck disable=SC2088  # prose, not a path
    detail "~/.cache was not touched. Re-run with --user-cache to purge the"
    detail "disposable parts of it (it is on /home, so it will not help /)."
  fi
}

# =============================================================================
# USER CACHE - opt-in, deliberately conservative
# =============================================================================
do_user_cache() {
  banner "OPTIONAL - USER CACHE (~/.cache)"

  # Everything under ~/.cache is safe to delete by definition - that is the
  # directory's contract. But "safe" is not "free": model weights and browser
  # binaries cost hours of re-download. Only self-regenerating caches are
  # cleared automatically; the expensive ones are reported for a human to judge.
  local disposable=(mozilla google-chrome chromium thumbnails mesa_shader_cache
                    wine pnpm pre-commit node virtualenv bookmarksrunner fontconfig)

  step_start "Clear self-regenerating caches" \
"Browser caches, thumbnails, shader caches and package-manager metadata. Every \
one of these rebuilds itself on demand at no cost beyond a slightly slower \
first launch. Nothing here is user data. Close your browsers first - clearing \
the cache underneath a running Firefox or Chrome can confuse it until restart." \
    "$HOME"
  local found=0
  for dir in "${disposable[@]}"; do
    [ -d "$HOME/.cache/$dir" ] || continue
    found=1
    status "$dir ($(du -sh "$HOME/.cache/$dir" 2>/dev/null | cut -f1))"
    run rm -rf "${HOME:?}/.cache/${dir:?}"
  done
  [ "$found" -eq 1 ] || success "nothing to clear"
  step_end

  step_start "Purge Python tooling caches" \
"uv and pip cache every wheel they have ever downloaded. Their own purge \
commands are used instead of rm, so the tools keep a consistent index." \
    "$HOME"
  if command -v uv >/dev/null 2>&1; then
    run uv cache clean
  fi
  if command -v pip >/dev/null 2>&1; then
    run pip cache purge
  fi
  step_end

  step_start "Report expensive caches (not deleted)" \
"These are large but costly to refetch - LLM model weights, browser binaries \
for test automation, downloaded OS images. Deleting them breaks nothing \
permanently, but it can mean hours of re-downloading. Judge them yourself." \
    "$HOME"
  du -sh "$HOME"/.cache/* 2>/dev/null | sort -rh | head -10 | indent
  step_end
}

# =============================================================================
# MAIN
# =============================================================================
banner "SYSTEM CLEANER - mode: $MODE"
echo
detail "started:      $(date '+%Y-%m-%d %H:%M:%S')"
detail "keep cache:   $KEEP_VERSIONS version(s) per package"
detail "user cache:   $([ "$CLEAN_USER_CACHE" -eq 1 ] && echo 'will be purged (--user-cache)' || echo 'untouched')"
detail "confirmation: $([ "$ASSUME_YES" -eq 1 ] && echo 'skipped (--yes)' || echo 'asked before destructive steps')"
echo
if [ "$DRY_RUN" -eq 1 ]; then
  warn "DRY RUN - commands are printed, nothing is changed"
fi
echo "  Partitions at start:"
show_disks

case "$MODE" in
  prepare) do_prepare ;;
  upgrade) do_upgrade ;;
  clean)   do_clean ;;
  all)     do_prepare; do_upgrade; do_clean ;;
esac

# ---- summary ----
TOTAL_ELAPSED=$(( $(date +%s) - TOTAL_T0 ))
ROOT_FREED=$(( $(avail_bytes /) - ROOT_FREE_START ))

banner "SUMMARY"
echo
printf '  %-44s %8s  %-22s %s\n' "STEP" "TIME" "SPACE" "ON"
printf '  %s\n' "------------------------------------------------------------------------------------"
for line in "${SUMMARY[@]}"; do
  echo "  $line"
done
printf '  %s\n' "------------------------------------------------------------------------------------"
printf '  %-44s %8s  %-22s %s\n' "TOTAL" "$(duration "$TOTAL_ELAPSED")" "$(delta "$ROOT_FREED")" "/"

echo
echo "  Partitions before:"
if [ -f "$STATE_DIR/disk-before.txt" ]; then
  sed '1d;s/^/     /' "$STATE_DIR/disk-before.txt"
else
  echo "     (not recorded - 'prepare' did not run in this invocation)"
fi
echo
echo "  Partitions after:"
{ date -Is; df -h / /home; } > "$STATE_DIR/disk-after.txt"
show_disks

echo
detail "finished: $(date '+%Y-%m-%d %H:%M:%S')  (log of measurements in $STATE_DIR)"
success "all done"
