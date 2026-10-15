# Root disk analysis — 2026-10-15

## Verdict

After user-performed cleanup, root (`/dev/nvme0n1p1`, ext4, 98 GiB usable) is at 87%, with 13 GiB available. Initially it was at 100%, with 0 available. Inodes are only 14% used. `/home` is a separate filesystem with 91 GiB available; `/tmp` is tmpfs and cannot explain root usage.

## Plan and estimated times

1. Confirm filesystems and access (1 minute).
2. Measure root directories, caches, logs, and deleted open files (2–5 minutes).
3. Rank cleanup options with measured savings and risks; review findings (1–2 minutes).

## Chronological status

| Step | Status | Time |
|---|---|---|
| Filesystems and inodes | Done | Initial inspection |
| Directory and service usage | Done; privileged directories inaccessible | Approximately 4 minutes |
| Recommendations and review | Done | Approximately 1 minute |

## Results

- Root: 98 GiB total, 93 GiB used, 0 available; ext4 reserved capacity may explain the difference.
- Home: separate 807 GiB filesystem, 675 GiB used, 91 GiB available.
- `/tmp`: separate 16 GiB tmpfs, 14 GiB used; removing its contents does not free root disk space.
- No cleanup or system changes authorized or performed.

## Resume here

State: user completed package-cache, journal, and coredump cleanup; root has 13 GiB available (87% used). User supplied privileged measurements confirming Ollama storage as the main hidden usage. No further cleanup or configuration changes authorized.

Check commands: `df -hT`, `df -ih`, `lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS`.

Restart from repository root: `cat ROOT_DISK_ANALYSIS_2026-10-15.md`; then `sudo du -xhd1 / 2>/dev/null | sort -h` and inspect the largest directories. Do not delete files during analysis.

## Measured findings and recommended actions

All directory figures are allocated GiB rounded by `du`, unless noted. Permission errors mean totals are lower bounds.

| Location | Measured usage | Interpretation |
|---|---:|---|
| `/usr` | 29 GiB visible | Installed software; excludes protected `/usr/share/ollama` |
| `/var` | 23 GiB visible | Includes caches, logs, Flatpak, dumps |
| `/opt` | 7.5 GiB visible | CUDA 4.8 GiB, Qt 1.6 GiB; uninstall only if unused |
| `/var/cache/pacman/pkg` | 5.95 GiB | Downloaded package archives |
| `/var/log/journal` | 4.01 GiB | Historical system logs |
| `/var/lib/systemd/coredump` | 3.16 GiB | Crash dumps, including two QEMU dumps near 1 GiB each |
| `/var/lib/flatpak` | 8.7 GiB | Apps 3.6 GiB, repository 5 GiB; not all reclaimable |

### Immediate relief

1. `sudo paccache -r -k0`: dry run found 874 package archives totaling **5.95 GiB**. Removes cached archives, leaving installed packages intact; local cached downgrade/reinstall copies are lost. Keeping one version (`-k1`) frees only **458 MiB**, keeping two frees **220.74 MiB**. Protected incomplete-download directories are excluded from these measured savings.
2. `sudo journalctl --rotate --vacuum-size=500M`: target roughly **3.5 GiB** of savings by discarding historical logs. Active journals and concurrent writes mean the final total is approximate.
3. If crash debugging is no longer needed: `sudo find /var/lib/systemd/coredump -maxdepth 1 -type f -name 'core.*' -delete` frees approximately **3.16 GiB**, losing stored crash diagnostics.
4. `df -h /`: verify available space after each action. The above removes approximately **12.6 GiB**; about 5 GiB may first replenish the ext4 reserve, leaving roughly **7–8 GiB** available to ordinary users. This is an estimate, not a measured post-cleanup result.

### Find the remaining usage before further deletion

`du` sees approximately 60 GiB versus `df` reporting 93 GiB used. This approximately 33 GiB difference includes unreadable directories and potentially filesystem metadata/deleted open files; it is **not proven** to be any single directory.

Run interactively:

```sh
sudo du -xhd1 / /usr/share/ollama /var/lib/containerd /root /var/cache/pacman/pkg 2>/dev/null | sort -h
```

If available, `sudo lsof +L1` identifies deleted files still held open; check their device/filesystem before attributing them to root. `lsof` is not currently installed, so do not install it while root is full.

The local Ollama service runs as `ollama`, has no visible `OLLAMA_MODELS` override, and `/usr/share/ollama` is unreadable to this user. Its API lists nine model tags with logical sizes from 1.62 to 7.28 GiB. Shared blobs prevent summing tags as physical usage. This makes Ollama a priority for privileged inspection, not a confirmed 33 GiB culprit. If its model store is large, remove unwanted models through Ollama or migrate the store to `/home` in a planned maintenance window; do not remove blobs manually or change a busy service.

Docker reports large reclaimable usage but `DockerRootDir` is **`/home/docker`**, on the separate home filesystem. Its reported storage is not a root-cleanup target. The separate `/var/lib/containerd` remains unmeasured and could still consume root space.

For prevention, `paccache.timer` exists and is disabled: `sudo systemctl enable --now paccache.timer` enables its weekly default retention of three versions. Consider a journald `SystemMaxUse=500M` limit and a coredump storage cap during maintenance. Flatpak unused runtimes are a secondary option: `sudo flatpak uninstall --system --unused` requires reviewing its proposed removals; no reclaimable amount was measured.

## Review

- Verified filesystem boundaries: `/home/docker` and `/tmp` cannot explain root usage.
- Verified package savings by dry runs; the full 5.95 GiB is available only with zero cached versions retained.
- Avoided attributing the unreadable 33 GiB to Ollama or containerd without privileged measurement.
- Distinguished GiB from Docker's decimal GB and logical model sizes from physical blob usage.
- Accounted for ext4 reserved capacity when estimating usable space after cleanup.
- No deletions, service changes, package changes, or pushes performed.

Sources for command semantics: [paccache manual](https://man.archlinux.org/man/paccache.8), [journalctl manual](https://www.freedesktop.org/software/systemd/man/255/journalctl.html). Installed `paccache --help` and dry runs were also checked.

## Follow-up: user-confirmed cleanup and privileged measurements

- Package cache is now 404 KiB; repeat `paccache -r -k0` found no candidates.
- Journal vacuum reported 3.4 GiB removed; repeat vacuum freed zero.
- User removed stored core dumps.
- Final supplied `df`: 98 GiB total, 81 GiB used, 13 GiB available, 87% used.
- Privileged `du`: `/usr/share/ollama` 32 GiB, comprising `.ollama` 31 GiB and `.nv` 803 MiB; `/root` 2.2 GiB; `/var/lib/containerd` only 1.8 MiB.
- Correction to the initial available-space estimate: actual final availability is 13 GiB, higher than the estimated 7–8 GiB. The initial estimate assumed the approximately 5 GiB reserved capacity would first need replenishing; observed filesystem accounting did not follow that assumption. Prefer measured `df` availability.
- Immediate disk exhaustion is resolved. Next optional action: remove unwanted models through `ollama rm MODEL`, or migrate the model store to `/home` with a verified copy and service maintenance. Measure blob sharing; tag sizes are not additive. Do not delete model blobs by hand.
- Prevention remains recommended: enable weekly `paccache.timer`, bound journal disk use, and cap stored crash dumps. No such configuration changes have been made.
