# microSD Benchmark — Patriot VX Series 32 GB

| Field       | Value |
|---|---|
| Card        | Patriot VX Series 32 GB |
| Speed Class | V30, UHS-I, Class 10 |
| Device      | /dev/sda1 (vfat, 28.2 GiB) |
| Test size   | 512 MB per sequential run |
| Runs        | 3 |
| Host OS     | Linux 7.0.10-1-MANJARO |
| Date        | 2026-06-08 |
| Tools       | hdparm, dd (coreutils), fio 3.42, ioping 1.3 |

---

## Summary

| Metric                        | Measured        | Rated spec                  |
|---|---|---|
| Sequential write avg (dd)     | **13.8 MB/s**   | 80 MB/s                     |
| Sequential read avg (dd)      | **21.0 MB/s**   | 100 MB/s                    |
| hdparm raw read               | **19.9 MB/s**   | —                           |
| 4K random write IOPS (QD1)    | **~538 IOPS**   | —                           |
| 4K random write IOPS (QD32)   | **~585 IOPS**   | —                           |
| 4K random read IOPS (QD1)     | **~1017 IOPS**  | —                           |
| 4K random read IOPS (QD32)    | **~1145 IOPS**  | —                           |
| Access latency avg (ioping)   | **1.30 ms**     | —                           |
| Access latency min / max      | 0.83 / 1.70 ms  | —                           |

> **Write speed fails V30 spec.** V30 mandates a sustained minimum of 30 MB/s; this card averaged 13.8 MB/s — less than half that floor.
> Read speed (21 MB/s) is roughly 1/5 of the advertised 100 MB/s. Both figures are consistent across all three runs, so this reflects the card's actual flash ceiling, not a one-off dip.

---

## hdparm — Raw Block Device Sequential Read

Reads directly from `/dev/sda` with `O_DIRECT`, bypassing the page cache and filesystem.

```
/dev/sda:
 Timing O_DIRECT disk reads:  60 MB in  3.01 seconds =  19.93 MB/s
```

---

## dd — Sequential Write (512 MB, fdatasync, 3 runs)

`conv=fdatasync` forces a full hardware flush before timing ends — no cache inflation.

| Run   | Bytes copied | Time     | Speed     |
|---|---|---|---|
| Run 1 | 536870912 (512 MiB) | 44.15 s  | 12.2 MB/s |
| Run 2 | 536870912 (512 MiB) | 35.59 s  | 15.1 MB/s |
| Run 3 | 536870912 (512 MiB) | 37.68 s  | 14.2 MB/s |

**Average: 13.8 MB/s**

Run 1 is notably slower (44 s vs ~36 s) — likely the card throttling on the first large write after idle; runs 2–3 are more representative of sustained throughput.

---

## dd — Sequential Read (512 MB, cold cache, 3 runs)

Page cache dropped (`echo 3 > /proc/sys/vm/drop_caches`) before each pass.

| Run   | Bytes copied | Time     | Speed     |
|---|---|---|---|
| Run 1 | 536870912 (512 MiB) | 25.63 s  | 20.9 MB/s |
| Run 2 | 536870912 (512 MiB) | 25.57 s  | 21.0 MB/s |
| Run 3 | 536870912 (512 MiB) | 25.30 s  | 21.2 MB/s |

**Average: 21.0 MB/s**

Read speed is extremely stable across all three runs (±0.2 MB/s), indicating no thermal throttling on reads.

---

## fio — 4K Random Write

`--direct=1`, `--ioengine=libaio`, 256 MB file, 30 s runtime per job.

### Queue Depth 1 (single-threaded / latency-bound)

```
iops: min=222, max=672, avg=537.93, stdev=156.76, samples=60
WRITE: bw=2152 KiB/s (2203 kB/s), io=63.0 MiB, run=30001 ms
```

### Queue Depth 32 (max IOPS pressure)

```
iops: min=218, max=714, avg=584.97, stdev=172.41, samples=60
WRITE: bw=2339 KiB/s (2396 kB/s), io=68.6 MiB, run=30005 ms
```

QD32 yields only ~9% more IOPS than QD1 (585 vs 538). The high stdev (156–172) relative to the average shows the controller is not consistently paced — IOPS swing from 218 to 714 within a single 30 s window, typical of a budget card without a write buffer.

---

## fio — 4K Random Read

`--direct=1`, `--ioengine=libaio`, 256 MB pre-written file, cache dropped before each job.

### Queue Depth 1

```
iops: min=918, max=1166, avg=1016.88, stdev=43.82, samples=59
READ: bw=4064 KiB/s (4161 kB/s), io=119 MiB, run=30001 ms
```

### Queue Depth 32

```
iops: min=1000, max=1170, avg=1144.75, stdev=21.17, samples=59
READ: bw=4578 KiB/s (4688 kB/s), io=134 MiB, run=30002 ms
```

QD32 gains ~13% over QD1 on reads (1145 vs 1017 IOPS). Stdev is much lower under QD32 (21 vs 44), indicating the controller queues reads more predictably than writes. 4K read bandwidth (~4–4.5 MB/s) is roughly double the 4K write bandwidth (~2.2 MB/s).

---

## ioping — Access Latency

200 sequential 4 KiB read requests to the mounted filesystem (`ioping -c 200`).

```
--- /tmp/sdcard_bench (vfat /dev/sda1 28.2 GiB) ioping statistics ---
199 requests completed in 257.9 ms, 796 KiB read, 771 iops, 3.01 MiB/s
generated 200 requests in 3.32 min, 800 KiB, 1 iops, 4.02 KiB/s
min/avg/max/mdev = 832.6 us / 1.30 ms / 1.70 ms / 187.4 us
```

Latency is consistent and low. mdev of 187 µs on a 1.30 ms average (~14% variation) with no outlier spikes across 200 requests. The card responds predictably for small random reads — this is the one area where it behaves well.

<details>
<summary>Full ioping per-request log</summary>

```
request=2   time=1.40 ms    request=3   time=1.52 ms    request=4   time=1.40 ms
request=5   time=1.40 ms    request=6   time=1.25 ms    request=7   time=1.24 ms
request=8   time=1.48 ms    request=9   time=1.48 ms    request=10  time=1.46 ms
request=11  time=1.45 ms    request=12  time=1.38 ms    request=13  time=1.29 ms
request=14  time=1.17 ms    request=15  time=1.52 ms    request=16  time=1.61 ms
request=17  time=1.43 ms    request=18  time=1.68 ms    request=19  time=1.40 ms
request=20  time=1.51 ms    request=21  time=1.33 ms    request=22  time=1.62 ms
request=23  time=1.67 ms    request=24  time=1.49 ms    request=25  time=1.43 ms
request=26  time=1.56 ms    request=27  time=1.48 ms    request=28  time=1.25 ms
request=29  time=1.47 ms    request=30  time=1.45 ms    request=31  time=1.47 ms
request=32  time=1.37 ms    request=33  time=1.40 ms    request=34  time=1.41 ms
request=35  time=1.39 ms    request=36  time=1.43 ms    request=37  time=1.47 ms
request=38  time=1.32 ms    request=39  time=1.49 ms    request=40  time=1.50 ms
request=41  time=1.52 ms    request=42  time=1.39 ms    request=43  time=1.04 ms
request=44  time=1.28 ms    request=45  time=1.38 ms    request=46  time=1.60 ms
request=47  time=1.53 ms    request=48  time=1.56 ms    request=49  time=1.59 ms
request=50  time=1.42 ms    request=51  time=1.46 ms    request=52  time=1.35 ms
request=53  time=1.39 ms    request=54  time=1.61 ms    request=55  time=1.28 ms
request=56  time=1.39 ms    request=57  time=1.45 ms    request=58  time=1.20 ms
request=59  time=1.28 ms    request=60  time=1.32 ms    request=61  time=1.41 ms
request=62  time=1.08 ms    request=63  time=1.10 ms    request=64  time=1.45 ms
request=65  time=1.24 ms    request=66  time=1.41 ms    request=67  time=859.5 us
request=68  time=1.26 ms    request=69  time=1.36 ms    request=70  time=1.09 ms
request=71  time=1.24 ms    request=72  time=1.05 ms    request=73  time=1.24 ms
request=74  time=1.37 ms    request=75  time=958.2 us   request=76  time=1.07 ms
request=77  time=1.14 ms    request=78  time=1.27 ms    request=79  time=1.26 ms
request=80  time=1.36 ms    request=81  time=1.09 ms    request=82  time=832.6 us
request=83  time=1.48 ms    request=84  time=1.16 ms    request=85  time=1.32 ms
request=86  time=1.07 ms    request=87  time=1.34 ms    request=88  time=1.19 ms
request=89  time=1.30 ms    request=90  time=1.27 ms    request=91  time=1.24 ms
request=92  time=1.19 ms    request=93  time=1.06 ms    request=94  time=1.19 ms
request=95  time=1.16 ms    request=96  time=979.3 us   request=97  time=1.03 ms
request=98  time=1.04 ms    request=99  time=1.25 ms    request=100 time=1.21 ms
request=101 time=1.27 ms    request=102 time=1.40 ms    request=103 time=1.46 ms
request=104 time=1.41 ms    request=105 time=1.27 ms    request=106 time=1.24 ms
request=107 time=1.27 ms    request=108 time=1.16 ms    request=109 time=1.46 ms
request=110 time=1.31 ms    request=111 time=1.21 ms    request=112 time=1.17 ms
request=113 time=1.26 ms    request=114 time=1.16 ms    request=115 time=1.27 ms
request=116 time=1.49 ms    request=117 time=1.25 ms    request=118 time=1.21 ms
request=119 time=1.32 ms    request=120 time=1.47 ms    request=121 time=1.39 ms
request=122 time=1.37 ms    request=123 time=1.30 ms    request=124 time=1.58 ms
request=125 time=1.25 ms    request=126 time=1.08 ms    request=127 time=1.04 ms
request=128 time=974.6 us   request=129 time=1.46 ms    request=130 time=1.34 ms
request=131 time=1.30 ms    request=132 time=880.9 us   request=133 time=1.21 ms
request=134 time=1.59 ms    request=135 time=1.35 ms    request=136 time=1.08 ms
request=137 time=984.3 us   request=138 time=1.17 ms    request=139 time=884.2 us
request=140 time=968.3 us   request=141 time=1.22 ms    request=142 time=1.11 ms
request=143 time=1.25 ms    request=144 time=1.06 ms    request=145 time=1.30 ms
request=146 time=1.36 ms    request=147 time=1.18 ms    request=148 time=1.19 ms
request=149 time=964.5 us   request=150 time=1.23 ms    request=151 time=1.18 ms
request=152 time=1.38 ms    request=153 time=1.23 ms    request=154 time=1.41 ms
request=155 time=1.08 ms    request=156 time=1.34 ms    request=157 time=1.27 ms
request=158 time=1.12 ms    request=159 time=1.12 ms    request=160 time=1.12 ms
request=161 time=968.4 us   request=162 time=1.36 ms    request=163 time=913.5 us
request=164 time=1.27 ms    request=165 time=1.03 ms    request=166 time=1.13 ms
request=167 time=1.06 ms    request=168 time=922.4 us   request=169 time=973.5 us
request=170 time=929.5 us   request=171 time=1.17 ms    request=172 time=970.2 us
request=173 time=1.45 ms    request=174 time=1.36 ms    request=175 time=960.2 us
request=176 time=1.22 ms    request=177 time=1.12 ms    request=178 time=1.55 ms
request=179 time=1.44 ms    request=180 time=1.51 ms    request=181 time=1.66 ms
request=182 time=1.70 ms    request=183 time=1.46 ms    request=184 time=1.41 ms
request=185 time=1.47 ms    request=186 time=1.48 ms    request=187 time=1.50 ms
request=188 time=1.44 ms    request=189 time=1.46 ms    request=190 time=1.45 ms
request=191 time=1.54 ms    request=192 time=1.07 ms    request=193 time=1.49 ms
request=194 time=1.53 ms    request=195 time=1.39 ms    request=196 time=1.38 ms
request=197 time=1.14 ms    request=198 time=1.43 ms    request=199 time=1.42 ms
request=200 time=1.05 ms
```

</details>

---

## Methodology

| Test | Command / flags | Notes |
|---|---|---|
| hdparm raw read | `hdparm -t --direct /dev/sda` | Block device, bypasses FS and page cache |
| dd write | `dd … bs=1M conv=fdatasync` | Full hardware flush before timing |
| dd read | `echo 3 > drop_caches` before each run | Forces cold read from media |
| fio random | `--direct=1 --ioengine=libaio --bs=4k --runtime=30s` | Bypasses page cache; two queue depths |
| ioping | `ioping -c 200 <mountpoint>` | Filesystem-level, 4 KiB requests |
