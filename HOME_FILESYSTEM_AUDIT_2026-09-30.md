# Home filesystem audit — 2026-09-30

## Verdict so far

`/home` is 807 GiB total, 700 GiB used, 67 GiB available (92% used). The owner's home directory accounts for about 631 GiB. No files have been deleted.

## Plan and time budget

| Step | Estimate | State |
| --- | ---: | --- |
| Measure filesystem and top-level directories | 2 min | Done |
| Inspect large areas and classify safety | 5–10 min | Running |
| Calculate a conservative path to at least 100 GB recovered | 3 min | Open |
| Report precise commands and cautions | 2 min | Open |

## Chronological status

| Time (UTC) | Status | Finding |
| --- | --- | --- |
| 18:57 | Measured | `/home`: 807G total, 700G used, 67G available. Home tree: 631G. |
| 18:57 | Measured | Largest directories: `VirtualBox VMs` 245G, `repos` 153G, `.local` 50G, `.cache` 20G, `Downloads` 20G. |

## Results

Pending detailed classification. Values from `du` are allocated disk space and are rounded by `-h`.

## Resume here

State: read-only audit in progress; no deletion authorized or performed. The repository already had unrelated uncommitted work when this audit began; leave it alone.

Check commands:

```sh
df -hT /home/mpetrick
du -xhd1 /home/mpetrick 2>/dev/null | sort -h
```

Restart commands: rerun the check commands, inspect the largest directories with `du -xhd1`, and update the results and status table. Do not remove data as part of this audit.
