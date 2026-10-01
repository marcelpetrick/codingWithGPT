# System crash investigation — 2026-10-01

## Verdict

At about 18:10 CEST the machine suffered an **unclean, machine-level reset or power cutoff**, not a
normal Linux reboot. The strongest supported precipitating cause is sustained CPU thermal
saturation from the `hr-doccontrol` verification pipeline. The pipeline was running the same
CPU-heavy GUI/OCR test family before the failure and, after the reboot, a resumed run immediately
reproduced the dangerous operating condition: 98–100 °C CPU package temperature, both fans at
maximum, load average 25–30 on 20 logical CPUs, and continuous hardware thermal throttling.

The logs cannot distinguish the final mechanism between (a) firmware/EC thermal protection cutting
or resetting power and (b) a hard power-button reset after the thermally saturated system stopped
responding. Both leave exactly the abrupt journal ending seen here. Confidence is **high** that the
reset was unclean and the test workload caused severe thermal saturation; confidence is **moderate**
that thermal protection itself issued the reset because that action happens below Linux and leaves no
final kernel record.

**Recurrence assessment: high if the workload is run unchanged.** The same pipeline resumed after
boot and was still sitting at the CPU's 100 °C critical threshold during this investigation. There is
also a separate suspend/hibernate instability involving the NVIDIA driver; it explains older unclean
boots but not this 18:10 event.

## Plan and status

| Step | State | Result |
|---|---|---|
| Establish boot/crash timeline | done | Previous boot ended 18:10:00.583; new boot began 18:11:59. No shutdown sequence exists. |
| Inspect kernel, service, coredump, and power paths | done | No panic, OOM kill, GPU Xid, storage error, watchdog, or power warning at the event. |
| Reproduce resource and thermal condition | done | Resumed pipeline reproduced 98–100 °C and continuous throttling. |
| Check earlier failures for recurrence | done | Older failures cluster around suspend/hibernate and NVIDIA allocation/resume errors; distinct from this event. |
| Record conclusion and prevention | done | See below. |

## Timeline

| Time (CEST) | Evidence |
|---|---|
| 17:16–18:09 | Repeated test-related coredumps from headless Chromium, Qt/Python GUI tests, and deliberate `ld-linux.so.2` seccomp tests. |
| 18:07:12 | TCP SYN-cookie protection activates on local sandbox proxy port 3128 during heavy agent/test activity. |
| 18:09:35 | Last test-related coredump completes. |
| 18:10:00.580 | Cron opens the regular five-minute `abtop-codex-reset` session. |
| 18:10:00.583 | Last record in the old boot: the cron command starts. There is no `CMDEND`, shutdown target, filesystem sync, panic, or reboot request after it. |
| 18:11:59 | New kernel boot begins. |
| 18:12–18:14 | Journald reports both system and user journals were corrupted or uncleanly shut down and replaces them. |
| 18:21 onward | A restored Claude/Konsole session resumes `verify_index.sh -> localPipeline.sh -> pytest -n 6`. |
| 18:23–18:26 | CPU remains 98–100 °C, fans approximately 5900/5600 RPM, load 25–30; hardware thermal-throttle count rises continuously. |

## Why the pipeline overloads this machine

The active command is:

```text
pytest -q -n 6 --dist loadscope --cov=hrdoccontrol ...
```

`HRDOC_TEST_WORKERS=6` creates six pytest-xdist processes. Each observed worker had 62–77 threads,
including separate numerical-library thread pools, while the tests also launch CPU-heavy Tesseract
OCR processes. That is roughly 400 worker threads plus OCR and desktop/agent work competing for 20
logical CPUs. No `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, or
`NUMEXPR_NUM_THREADS` cap was present in the pipeline environment.

Measured live evidence:

- load average reached 30.23 on 20 logical CPUs;
- CPU package repeatedly read exactly 100 °C, its reported high and critical threshold;
- Dell CPU sensor read 99 °C;
- both fans were at their maximum speeds;
- package thermal-throttle count increased by 406 in five seconds in one sample, then by about
  500 every five seconds in a 15-second persistence sample;
- NVMe was about 52–54 °C, well below its 84.8 °C critical threshold;
- NVIDIA GPU was about 78 °C and idle at 0% compute during the live check.

## Paths checked and ruled out for this event

| Candidate | Finding |
|---|---|
| Orderly reboot/shutdown | Ruled out. No systemd shutdown sequence, reboot request, filesystem sync, or journal stop. |
| Kernel panic/oops/lockup/watchdog | No matching kernel record. Persistent pstore could not be read without root, so a panic that failed to reach the journal is not disproved absolutely. |
| Linux OOM | Ruled out by logs: no OOM-killer invocation or killed process. `vm.panic_on_oom=0`; the machine has 31 GiB RAM and 33 GiB swap. |
| Disk full or NVMe error | Ruled out as immediate cause: no NVMe/I/O/ext4 errors; `/` had 12 GiB free and `/home` 237 GiB free. SMART requires root and was not available. |
| NVIDIA GPU crash | No Xid, reset, or GPU fault near 18:10. Historical NVIDIA errors exist around sleep, not at this crash. |
| External AC loss | No power/battery warnings. After boot AC was online and the battery was full, so loss of wall power alone should not have stopped the laptop. |
| `abtop-codex-reset` cron | Coincidental last writer. It ran and completed every five minutes beforehand in about 0.08 s and only reads/atomically rewrites a small JSON cache. At 18:10 the machine disappeared before its normal `CMDEND`. |
| `ld-linux.so.2` SIGSYS coredumps | Test artifacts. Their command lines are the `test_run_ldd_on_a_real_binary_0` pytest case and `SYS_SECCOMP` is the expected sandbox enforcement signal. |
| Chromium and Qt/Python coredumps | Real user-space test failures and evidence of the active GUI-test workload, but not a kernel/system crash by themselves. |
| Port 3128 SYN warning | Local Claude sandbox proxy connection churn; TCP switched to SYN cookies. No evidence that it reset the machine. |

## Separate older failure mode

The boot ending 2026-09-30 13:55 and another boot ending 2026-09-25 show a different sequence:
hibernate or `suspend-then-hibernate`, NVIDIA `NV_ERR_NO_MEMORY` / ACPI D-notifier errors, device
resume failures, then an abrupt end. That pattern can recur when sleeping or hibernating with the
NVIDIA driver active. There was no suspend or hibernate transition near the 2026-10-01 18:10 crash,
so it is not the immediate explanation here.

## Prevention

For the current test path, use both levels of containment:

```sh
HRDOC_TEST_WORKERS=1 \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
./localPipeline.sh
```

Start with one xdist worker and raise to two only after observing that package temperature stays below
the critical threshold. The numerical-library thread caps are as important as the pytest worker cap;
otherwise every xdist worker creates its own large thread pools. Avoid running multiple full local
pipelines concurrently. The currently resumed pipeline was not stopped or modified during this
read-only investigation.

For the separate sleep failure, avoid suspend-then-hibernate while long GPU/agent jobs are active and
test the installed Linux 6.18 kernel as an A/B comparison with Linux 7.1 before attributing the issue
to hardware. Firmware, cooling-path inspection, and privileged crash evidence should be checked if a
reduced single-worker run still reaches 100 °C or the machine resets while idle.

## Limitations

Root access was not available non-interactively, so `/sys/fs/pstore` and NVMe SMART data could not be
read. Those are the two remaining sources that could reveal a firmware-preserved panic or a storage
health warning. Neither missing source weakens the directly observed thermal overload, but they are
needed to make the final reset mechanism certain.

## Resume here

State: diagnosis complete; no configuration or running jobs changed.

Check commands:

```sh
journalctl --list-boots
journalctl -k -b -1 -r --no-pager | head -120
sensors
cat /sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count
ps -eo pid,ppid,pcpu,pmem,nlwp,comm,args --sort=-pcpu | head -40
```

Privileged follow-up commands:

```sh
sudo find /sys/fs/pstore -maxdepth 1 -type f -print -exec sed -n '1,240p' {} \;
sudo smartctl -x /dev/nvme0
```

Exact safe restart command for the pipeline is the capped command in **Prevention**. Do not restart
the six-worker uncapped form until its nested thread pools are limited.
