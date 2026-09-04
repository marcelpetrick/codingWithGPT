# What?

A maintenance script for Manjaro/Arch that upgrades the system and cleans up
after itself, in the right order, while telling you what it is doing and why.

It replaces the usual one-liner:

```bash
time ( sudo pacman -Syyu && yay -Syu --devel --noconfirm --answerclean All \
       --answerdiff None --answeredit None && sudo snap refresh && flatpak update -y )
```

The differences that matter:

* **Cleans before, not after.** `/var/cache/pacman/pkg` lives on `/` and grows
  without bound. If it has eaten the free space, a large `-Syu` can run out of
  disk mid-transaction and leave a half-upgraded system. So the cache is trimmed
  first, and the script refuses to start an upgrade below a free-space threshold.
* **`-Syu`, not `-Syyu`.** The doubled `-y` force-redownloads every package
  database even when nothing changed. That only helps after switching mirrors or
  branch; otherwise it is wasted bandwidth and mirror load.
* **No `--noconfirm` for AUR.** Unattended AUR upgrades silently accept
  dependency removals and package replacements. The final transaction stays
  visible for approval.
* **Handles the leftovers the one-liner ignores:** orphaned packages, `.pacnew`
  config drift, disabled snap revisions still mounted as loop devices, unused
  flatpak runtimes, and an uncapped systemd journal.
* **Measures.** Per-step wall time and reclaimed space, against the partition
  each step actually affects, with a summary table and before/after `df`.

## Run

```bash
./cleaner.sh --dry-run          # see exactly what would happen, change nothing
./cleaner.sh                    # all three phases, asks before destructive steps
./cleaner.sh prepare            # just measure and free space
./cleaner.sh clean --user-cache # cleanup, plus the disposable parts of ~/.cache
```

Options: `-n/--dry-run`, `-y/--yes`, `--user-cache`, `--keep N`, `-h/--help`.

## Safety

* `set -euo pipefail`, shellcheck-clean, refuses to run as root.
* Every destructive step is confirmed unless `--yes` is passed.
* `--yes` deliberately does **not** bypass the free-space check. That one is a
  safety gate, not a convenience prompt, and an unattended run must not be able
  to talk itself into upgrading onto a full disk.
* Orphaned packages are **listed, never auto-removed** — a package you installed
  deliberately can look like an orphan if it was never marked explicitly
  installed.
* The package cache keeps one version per package by default, so a broken
  update can still be rolled back with `pacman -U`.

## ~/.cache

`--user-cache` is opt-in and conservative. Everything under `~/.cache` is safe
to delete by definition, but *safe* is not *free*: LLM model weights, Playwright
browser binaries and downloaded OS images cost hours to refetch.

So the script only clears caches that regenerate on demand at no real cost
(browser caches, thumbnails, shader caches), uses `uv cache clean` and
`pip cache purge` rather than `rm` for the Python tooling, and merely **reports**
the large expensive ones for you to judge.

Note that `~/.cache` is on `/home`, so clearing it does nothing for the root
partition an upgrade needs.

## Ideas for later

* optional `--report-only` mode that measures and lists without touching anything
* remember the last few runs and show the trend in reclaimed space
* detect `linux*` kernel packages that are installed but no longer in the repos
