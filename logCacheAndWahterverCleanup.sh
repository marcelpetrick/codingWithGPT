#!/usr/bin/env bash
# Clean logs, crash dumps and package caches on the system partition (Manjaro).
#
# Careful by design:
#   - Each step says what it removes, why it is safe, and how big it is.
#   - Each step asks before it deletes anything (default answer: No).
#   - It keeps 2 versions of every package (downgrade path) and all kernels.
#   - It stops if pacman is running or its database is locked.
#
# Usage:
#   ./logCacheAndWahterverCleanup.sh            ask before every step
#   ./logCacheAndWahterverCleanup.sh --dry-run  only show what it would do
#   ./logCacheAndWahterverCleanup.sh --yes      do all steps without asking
#
# Run it as your normal user, not with sudo: yay refuses to run as root.

set -u

DRY_RUN=0
ASSUME_YES=0
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=1 ;;
        --yes)     ASSUME_YES=1 ;;
        -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

if [[ -t 1 ]]; then
    BOLD=$'\e[1m'; DIM=$'\e[2m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; RED=$'\e[31m'; RESET=$'\e[0m'
else
    BOLD=''; DIM=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

say()   { printf '%s\n' "$*"; }
info()  { printf '%s   %s%s\n' "$DIM" "$*" "$RESET"; }
ok()    { printf '%s   OK: %s%s\n' "$GREEN" "$*" "$RESET"; }
warn()  { printf '%s   NOTE: %s%s\n' "$YELLOW" "$*" "$RESET"; }
fail()  { printf '%sERROR: %s%s\n' "$RED" "$*" "$RESET" >&2; }

STEP=0
step() {
    STEP=$((STEP + 1))
    printf '\n%s[%d] %s%s\n' "$BOLD" "$STEP" "$*" "$RESET"
}

# Size of a path in human units, or "0" if it does not exist.
size_of() {
    local out
    out=$(sudo du -shc -- "$@" 2>/dev/null | tail -1 | awk '{print $1}')
    printf '%s' "${out:-0}"
}

# Ask before an action. Returns 0 to go ahead, 1 to skip.
confirm() {
    if (( DRY_RUN )); then
        info "Dry run: nothing is deleted."
        return 1
    fi
    if (( ASSUME_YES )); then
        return 0
    fi
    local answer
    read -rp "   Do this step? [y/N] " answer
    if [[ $answer == [yY] ]]; then
        return 0
    fi
    info "Skipped."
    return 1
}

# Run a command and show it first, so you always see what happens.
run() {
    printf '%s   $ %s%s\n' "$DIM" "$*" "$RESET"
    if "$@"; then
        return 0
    fi
    warn "The command returned an error. The script continues with the next step."
    return 1
}

avail_mb() { df --output=avail -B1M / | tail -1 | tr -d ' '; }

# ---------------------------------------------------------------- checks

if [[ $EUID -eq 0 ]]; then
    fail "Run this as your normal user, not as root or with sudo."
    exit 1
fi

say "${BOLD}System partition cleanup${RESET}"
(( DRY_RUN )) && warn "Dry run mode: the script only measures and explains."
(( ASSUME_YES )) && warn "--yes mode: the script does every step without asking."
# pamac-daemon always runs in the background, so only real package operations count.
busy=$(pgrep -a -x 'pacman|yay|paru|makepkg|pamac|pamac-manager' || true)
if [[ -n $busy ]]; then
    fail "A package operation is running. Let it finish, then run this script again:"
    printf '     %s\n' "$busy" >&2
    exit 1
fi
if [[ -e /var/lib/pacman/db.lck ]]; then
    fail "/var/lib/pacman/db.lck exists. Pamac may be updating in the background."
    say "   Close Pamac, wait a few minutes, then run this script again."
    say "   Do not delete the lock while an update can still be running."
    exit 1
fi
ok "No package operation is running."

say "The script asks for your sudo password once."
sudo -v || { fail "sudo failed."; exit 1; }

BEFORE=$(avail_mb)
say ""
df -h /

# ---------------------------------------------------------------- steps

step "Crash dumps (/var/lib/systemd/coredump)"
info "systemd stores a dump each time a program crashes."
info "You only need them to debug a crash. Nothing else uses them."
info "Files: $(sudo find /var/lib/systemd/coredump -type f 2>/dev/null | wc -l), size: $(size_of /var/lib/systemd/coredump)"
if confirm; then
    run sudo find /var/lib/systemd/coredump -type f -delete && ok "Crash dumps removed."
fi

step "systemd journal"
info "The journal holds the system logs. The script keeps the last 2 weeks, max 100 MB."
info "Current: $(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]')"
if confirm; then
    run sudo journalctl --vacuum-time=2weeks --vacuum-size=100M && ok "Journal reduced."
    warn "To make this permanent, set SystemMaxUse=200M in /etc/systemd/journald.conf."
fi

step "pacman package cache (/var/cache/pacman/pkg)"
info "pacman keeps every downloaded package. The script keeps the last 2 versions"
info "of each installed package, so you can still downgrade after a bad update."
info "It also removes cached packages of software that is no longer installed."
info "Size: $(size_of /var/cache/pacman/pkg)"
info "Preview:"
paccache -dk2 2>/dev/null | sed 's/^/     /' | tail -2
paccache -duk0 2>/dev/null | sed 's/^/     /' | tail -2
if confirm; then
    run sudo paccache -rk2
    run sudo paccache -ruk0
    ok "Package cache trimmed."
fi

if command -v yay >/dev/null; then
    step "yay AUR build cache (~/.cache/yay)"
    info "yay keeps the source and build files of AUR packages here."
    info "It downloads them again for the next AUR update. Size: $(du -sh ~/.cache/yay 2>/dev/null | cut -f1)"
    if confirm; then
        run yay -Sc --aur --noconfirm && ok "yay cache cleaned."
    fi
fi

# Not "pamac clean -b": its build directory is all of /var/tmp in pamac.conf.
pamac_build="/var/tmp/pamac-build-$USER"
if [[ -d $pamac_build ]]; then
    step "pamac AUR build files ($pamac_build)"
    info "Pamac (Manjaro's GUI updater) builds AUR packages here. They are safe to remove."
    info "Size: $(size_of "$pamac_build")"
    if confirm; then
        run sudo rm -rf -- "$pamac_build" && ok "Pamac build files removed."
    fi
fi

if [[ -d /var/lib/snapd/cache ]]; then
    step "Snap download cache (/var/lib/snapd/cache)"
    info "snapd keeps extra copies of the installed snaps here. The snaps themselves stay."
    info "Size: $(size_of /var/lib/snapd/cache)"
    if confirm; then
        run sudo find /var/lib/snapd/cache -type f -delete && ok "Snap cache removed."
    fi
fi

if command -v flatpak >/dev/null; then
    step "Unused Flatpak runtimes"
    info "These are runtimes that no installed Flatpak app needs any more."
    info "Flatpak shows the list itself and asks again before it removes anything."
    info "Size of all Flatpak data: $(size_of /var/lib/flatpak)"
    if confirm; then
        # Interactive on purpose: flatpak has no preview for --unused.
        run flatpak uninstall --unused
    fi
fi

step "Rotated logs older than 30 days (/var/log)"
info "Old rotated copies (*.old, *.1, *.gz). Current log files are not touched."
mapfile -t oldlogs < <(sudo find /var/log -type f \( -name '*.old' -o -name '*.[0-9]' -o -name '*.gz' \) -mtime +30 2>/dev/null)
if (( ${#oldlogs[@]} == 0 )); then
    ok "None found. Nothing to do."
else
    printf '     %s\n' "${oldlogs[@]}"
    if confirm; then
        run sudo rm -f -- "${oldlogs[@]}" && ok "${#oldlogs[@]} old log files removed."
    fi
fi

step "ThoraxBench leftovers (/var/tmp/thoraxbench-*)"
info "Work files from finished ThoraxBench runs. Other files in /var/tmp stay."
shopt -s nullglob
thorax=(/var/tmp/thoraxbench-*)
shopt -u nullglob
if (( ${#thorax[@]} == 0 )); then
    ok "None found. Nothing to do."
else
    printf '     %s\n' "${thorax[@]}"
    info "Size: $(size_of "${thorax[@]}")"
    if confirm; then
        run sudo rm -rf -- "${thorax[@]}" && ok "ThoraxBench leftovers removed."
    fi
fi

step "Orphan packages"
info "Packages that were installed as a dependency, but nothing needs them now."
info "Read the list: remove them only if you do not use these tools directly."
orphans=$(pacman -Qdtq)
if [[ -z $orphans ]]; then
    ok "None found. Nothing to do."
else
    printf '%s\n' "$orphans" | sed 's/^/     /'
    # This step always asks, also with --yes: it removes software.
    if (( DRY_RUN )); then
        info "Dry run: nothing is deleted."
    else
        read -rp "   Remove these packages? pacman shows the list again. [y/N] " answer
        if [[ $answer == [yY] ]]; then
            # shellcheck disable=SC2086 # one package name per word
            run sudo pacman -Rns $orphans
        else
            info "Skipped."
        fi
    fi
fi

# ---------------------------------------------------------------- result

step "Result"
AFTER=$(avail_mb)
df -h /
if (( DRY_RUN )); then
    say "Dry run complete. Nothing was deleted."
else
    ok "Freed: $(( AFTER - BEFORE )) MB on /"
fi
info "Not touched: kernels, /home, other files in /var/tmp."
