# microSD Benchmark

Benchmark results for microSD cards tested with `run_benchmark.sh` on Linux.

## Measurement Points

| ID | Card | Interface | Device / FS | Rated read | Rated write | Date |
|---|---|---|---|---|---|---|
| A | Patriot VX Series 32 GB | USB docking station | `/dev/sda1`, vfat | 100 MB/s | 80 MB/s, V30 min 30 MB/s | 2026-06-08 |
| B | Patriot VX Series 32 GB | Direct laptop SD slot | `/dev/mmcblk0p1`, vfat | 100 MB/s | 80 MB/s, V30 min 30 MB/s | 2026-06-08 |
| C | renkforce microSD UHS-I Class 10 64 GB | Direct laptop SD slot | `/dev/mmcblk0p1`, exfat | 80 MB/s | 10 MB/s | 2026-06-09 |

## Summary

| Metric | A - Patriot USB dock | B - Patriot direct slot | C - renkforce direct slot |
|---|---:|---:|---:|
| Sequential write avg (`dd`) | 13.8 MB/s | 32.2 MB/s | 15.6 MB/s |
| Sequential read avg (`dd`) | 21.0 MB/s | 86.3 MB/s | 86.4 MB/s |
| `hdparm` raw read | 19.9 MB/s | 83.1 MB/s | 81.8 MB/s |
| 4K random write IOPS QD1 | 537.93 | 666.34 | 286.58 |
| 4K random write IOPS QD32 | 584.97 | 728.61 | 174.19 |
| 4K random read IOPS QD1 | 1016.88 | 1613.66 | 1624.31 |
| 4K random read IOPS QD32 | 1144.75 | 1945.22 | 1943.49 |
| `ioping` avg latency | 1.30 ms | 14.6 ms | 14.7 ms |
| `ioping` min / max latency | 0.83 / 1.70 ms | 13.2 / 18.4 ms | 13.1 / 18.6 ms |

## Evaluation

The renkforce 64 GB card meets its advertised numbers in the laptop slot. Sequential read averaged 86.4 MB/s, which is slightly above the 80 MB/s rating. Sequential write averaged 15.6 MB/s, also above the 10 MB/s rating.

Compared with the Patriot card in the same laptop slot, the renkforce card reads almost identically: 86.4 MB/s vs 86.3 MB/s sequential read, and nearly the same 4K random read IOPS. Write behavior is much weaker: sequential write is about half the Patriot direct-slot result, and 4K random write IOPS are substantially lower. The sequential write runs also show visible throttling or variability: 20.8 MB/s on run 1, then 12.3 and 13.6 MB/s.

The laptop slot again gives realistic high read throughput and the same roughly 14-15 ms small-access latency seen on the Patriot direct-slot run. The USB dock's very low `ioping` latency should be treated as a controller/cache artifact, because its real read throughput was much lower.

## Details

### A - Patriot VX Series 32 GB via USB Docking Station

#### Raw Read

```text
/dev/sda:
 Timing O_DIRECT disk reads:  60 MB in  3.01 seconds =  19.93 MB/s
```

#### Sequential Write

| Run | Time | Speed |
|---|---:|---:|
| 1 | 44.15 s | 12.2 MB/s |
| 2 | 35.59 s | 15.1 MB/s |
| 3 | 37.68 s | 14.2 MB/s |

Average: 13.8 MB/s.

#### Sequential Read

| Run | Time | Speed |
|---|---:|---:|
| 1 | 25.63 s | 20.9 MB/s |
| 2 | 25.57 s | 21.0 MB/s |
| 3 | 25.30 s | 21.2 MB/s |

Average: 21.0 MB/s.

#### Random I/O

```text
4K random write QD1:  iops min=222  max=672  avg=537.93  stdev=156.76  bw=2152 KiB/s
4K random write QD32: iops min=218  max=714  avg=584.97  stdev=172.41  bw=2339 KiB/s
4K random read QD1:   iops min=918  max=1166 avg=1016.88 stdev=43.82   bw=4064 KiB/s
4K random read QD32:  iops min=1000 max=1170 avg=1144.75 stdev=21.17   bw=4578 KiB/s
```

#### Access Latency

```text
199 requests completed in 257.9 ms, 796 KiB read, 771 iops, 3.01 MiB/s
min/avg/max/mdev = 832.6 us / 1.30 ms / 1.70 ms / 187.4 us
```

### B - Patriot VX Series 32 GB via Direct Laptop SD Slot

#### Raw Read

```text
/dev/mmcblk0:
 Timing O_DIRECT disk reads: 250 MB in  3.01 seconds =  83.11 MB/s
```

#### Sequential Write

| Run | Time | Speed |
|---|---:|---:|
| 1 | 16.39 s | 32.8 MB/s |
| 2 | 16.88 s | 31.8 MB/s |
| 3 | 16.85 s | 31.9 MB/s |

Average: 32.2 MB/s.

#### Sequential Read

| Run | Time | Speed |
|---|---:|---:|
| 1 | 6.11 s | 87.8 MB/s |
| 2 | 6.31 s | 85.1 MB/s |
| 3 | 6.25 s | 85.9 MB/s |

Average: 86.3 MB/s.

#### Random I/O

```text
4K random write QD1:  iops min=236  max=952  avg=666.34  stdev=285.86  bw=2487 KiB/s
4K random write QD32: iops min=202  max=940  avg=728.61  stdev=270.03  bw=2925 KiB/s
4K random read QD1:   iops min=1432 max=1838 avg=1613.66 stdev=70.01   bw=6444 KiB/s
4K random read QD32:  iops min=1828 max=2018 avg=1945.22 stdev=43.31   bw=7780 KiB/s
```

#### Access Latency

```text
199 requests completed in 2.90 s, 796 KiB read, 68 iops, 274.1 KiB/s
min/avg/max/mdev = 13.2 ms / 14.6 ms / 18.4 ms / 698.4 us
```

### C - renkforce microSD UHS-I Class 10 64 GB via Direct Laptop SD Slot

#### Raw Read

```text
/dev/mmcblk0:
 Timing O_DIRECT disk reads: 246 MB in  3.01 seconds =  81.84 MB/sec
```

#### Sequential Write

| Run | Time | Speed |
|---|---:|---:|
| 1 | 25.8162 s | 20.8 MB/s |
| 2 | 43.7288 s | 12.3 MB/s |
| 3 | 39.5284 s | 13.6 MB/s |

Average: 15.6 MB/s.

#### Sequential Read

| Run | Time | Speed |
|---|---:|---:|
| 1 | 6.19168 s | 86.7 MB/s |
| 2 | 6.27674 s | 85.5 MB/s |
| 3 | 6.16952 s | 87.0 MB/s |

Average: 86.4 MB/s.

#### Random I/O

```text
4K random write QD1:  iops min=130  max=440  avg=286.58  stdev=102.02  bw=1138 KiB/s
4K random write QD32: iops min=70   max=244  avg=174.19  stdev=21.13   bw=700 KiB/s
4K random read QD1:   iops min=1242 max=2034 avg=1624.31 stdev=258.37  bw=6482 KiB/s
4K random read QD32:  iops min=1866 max=1986 avg=1943.49 stdev=25.84   bw=7770 KiB/s
```

#### Access Latency

```text
199 requests completed in 2.93 s, 796 KiB read, 67 iops, 271.3 KiB/s
min/avg/max/mdev = 13.1 ms / 14.7 ms / 18.6 ms / 663.6 us
```

## Methodology

| Test | Command / flags | Notes |
|---|---|---|
| Raw read | `hdparm -t --direct` | Block-device read, bypassing filesystem and page cache |
| Sequential write | `dd if=/dev/zero ... bs=1M conv=fdatasync` | Flushes to media before timing ends |
| Sequential read | `dd if=<testfile> of=/dev/null bs=1M` | Page cache dropped before each run |
| Random I/O | `fio --direct=1 --ioengine=libaio --bs=4k --runtime=30s` | Tested at queue depth 1 and 32 |
| Access latency | `ioping -c 200 <mountpoint>` | Filesystem-level 4 KiB access latency |
