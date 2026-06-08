# microSD Benchmark — Patriot VX Series 32 GB

| Field       | Value |
|---|---|
| Card        | Patriot VX Series 32 GB |
| Speed Class | V30, UHS-I, Class 10 |
| Filesystem  | vfat (28.2 GiB) |
| Test size   | 512 MB per sequential run, 3 runs |
| Host OS     | Linux 7.0.10-1-MANJARO |
| Date        | 2026-06-08 |
| Tools       | hdparm, dd (coreutils), fio 3.42, ioping 1.3 |

Two configurations tested with the same card:

| Config | Interface | Device |
|---|---|---|
| A | USB docking station | `/dev/sda1` |
| B | Direct laptop SD slot | `/dev/mmcblk0p1` |

---

## Comparison Summary

| Metric                      | A — USB dock    | B — Direct slot | Delta       |
|---|---|---|---|
| **Sequential write avg**    | 13.8 MB/s       | **32.2 MB/s**   | +133%       |
| **Sequential read avg**     | 21.0 MB/s       | **86.3 MB/s**   | +311%       |
| **hdparm raw read**         | 19.9 MB/s       | **83.1 MB/s**   | +317%       |
| **4K rnd write IOPS (QD1)** | ~538            | **~666**        | +24%        |
| **4K rnd write IOPS (QD32)**| ~585            | **~729**        | +25%        |
| **4K rnd read IOPS (QD1)**  | ~1017           | **~1614**       | +59%        |
| **4K rnd read IOPS (QD32)** | ~1145           | **~1945**       | +70%        |
| **ioping latency avg**      | **1.30 ms**     | 14.6 ms         | +1023% ⚠️  |
| **ioping latency min/max**  | 0.83 / 1.70 ms  | 13.2 / 18.4 ms  | —           |
| Rated write speed           | 80 MB/s (V30 min: 30 MB/s) | — | — |
| Rated read speed            | 100 MB/s        | —               | —           |

### Key observations

- **Direct slot unlocks the card's real throughput.** Sequential read jumps from 21 to 86 MB/s (~4×); sequential write from 13.8 to 32.2 MB/s (~2.3×). The USB docking station was the bottleneck in both cases.
- **Write speed now meets V30 spec via direct slot.** 32.2 MB/s clears the 30 MB/s sustained-write minimum. Via USB dock it did not.
- **ioping latency is paradoxically 10× worse via direct slot** (14.6 ms vs 1.30 ms). The USB dock appears to buffer or cache small repeated reads to the same location (ioping reads the same directory entry repeatedly), whereas the native SDIO/MMC interface sends each command directly to the flash with full per-command setup overhead. fio random reads — which scatter across a 256 MB file — tell the opposite story and are faster via direct slot.
- **4K random write IOPS improvement is modest** (~25%) compared to sequential (+133%), suggesting the write bottleneck is more in the card's flash controller than in the USB overhead.

---

## Config A — USB Docking Station (`/dev/sda1`)

### hdparm — Raw Block Device Read

```
/dev/sda:
 Timing O_DIRECT disk reads:  60 MB in  3.01 seconds =  19.93 MB/s
```

### dd — Sequential Write (512 MB, fdatasync, 3 runs)

| Run   | Time    | Speed     |
|---|---|---|
| Run 1 | 44.15 s | 12.2 MB/s |
| Run 2 | 35.59 s | 15.1 MB/s |
| Run 3 | 37.68 s | 14.2 MB/s |

**Average: 13.8 MB/s** — Run 1 slower, likely initial write throttle; runs 2–3 reflect steady state.

### dd — Sequential Read (512 MB, cold cache, 3 runs)

| Run   | Time    | Speed     |
|---|---|---|
| Run 1 | 25.63 s | 20.9 MB/s |
| Run 2 | 25.57 s | 21.0 MB/s |
| Run 3 | 25.30 s | 21.2 MB/s |

**Average: 21.0 MB/s** — extremely consistent (±0.2 MB/s).

### fio — 4K Random Write

```
QD1:  iops min=222  max=672  avg=537.93  stdev=156.76  bw=2152 KiB/s
QD32: iops min=218  max=714  avg=584.97  stdev=172.41  bw=2339 KiB/s
```

High stdev relative to mean (29%) — controller pacing is erratic, no consistent write buffer.

### fio — 4K Random Read

```
QD1:  iops min=918  max=1166  avg=1016.88  stdev=43.82  bw=4064 KiB/s
QD32: iops min=1000 max=1170  avg=1144.75  stdev=21.17  bw=4578 KiB/s
```

### ioping — Access Latency

```
199 requests completed in 257.9 ms, 796 KiB read, 771 iops, 3.01 MiB/s
min/avg/max/mdev = 832.6 us / 1.30 ms / 1.70 ms / 187.4 us
```

<details>
<summary>Full ioping per-request log (USB dock)</summary>

```
request=2   1.40 ms    request=3   1.52 ms    request=4   1.40 ms    request=5   1.40 ms
request=6   1.25 ms    request=7   1.24 ms    request=8   1.48 ms    request=9   1.48 ms
request=10  1.46 ms    request=11  1.45 ms    request=12  1.38 ms    request=13  1.29 ms
request=14  1.17 ms    request=15  1.52 ms    request=16  1.61 ms    request=17  1.43 ms
request=18  1.68 ms    request=19  1.40 ms    request=20  1.51 ms    request=21  1.33 ms
request=22  1.62 ms    request=23  1.67 ms    request=24  1.49 ms    request=25  1.43 ms
request=26  1.56 ms    request=27  1.48 ms    request=28  1.25 ms    request=29  1.47 ms
request=30  1.45 ms    request=31  1.47 ms    request=32  1.37 ms    request=33  1.40 ms
request=34  1.41 ms    request=35  1.39 ms    request=36  1.43 ms    request=37  1.47 ms
request=38  1.32 ms    request=39  1.49 ms    request=40  1.50 ms    request=41  1.52 ms
request=42  1.39 ms    request=43  1.04 ms    request=44  1.28 ms    request=45  1.38 ms
request=46  1.60 ms    request=47  1.53 ms    request=48  1.56 ms    request=49  1.59 ms
request=50  1.42 ms    request=51  1.46 ms    request=52  1.35 ms    request=53  1.39 ms
request=54  1.61 ms    request=55  1.28 ms    request=56  1.39 ms    request=57  1.45 ms
request=58  1.20 ms    request=59  1.28 ms    request=60  1.32 ms    request=61  1.41 ms
request=62  1.08 ms    request=63  1.10 ms    request=64  1.45 ms    request=65  1.24 ms
request=66  1.41 ms    request=67  859.5 us   request=68  1.26 ms    request=69  1.36 ms
request=70  1.09 ms    request=71  1.24 ms    request=72  1.05 ms    request=73  1.24 ms
request=74  1.37 ms    request=75  958.2 us   request=76  1.07 ms    request=77  1.14 ms
request=78  1.27 ms    request=79  1.26 ms    request=80  1.36 ms    request=81  1.09 ms
request=82  832.6 us   request=83  1.48 ms    request=84  1.16 ms    request=85  1.32 ms
request=86  1.07 ms    request=87  1.34 ms    request=88  1.19 ms    request=89  1.30 ms
request=90  1.27 ms    request=91  1.24 ms    request=92  1.19 ms    request=93  1.06 ms
request=94  1.19 ms    request=95  1.16 ms    request=96  979.3 us   request=97  1.03 ms
request=98  1.04 ms    request=99  1.25 ms    request=100 1.21 ms    request=101 1.27 ms
request=102 1.40 ms    request=103 1.46 ms    request=104 1.41 ms    request=105 1.27 ms
request=106 1.24 ms    request=107 1.27 ms    request=108 1.16 ms    request=109 1.46 ms
request=110 1.31 ms    request=111 1.21 ms    request=112 1.17 ms    request=113 1.26 ms
request=114 1.16 ms    request=115 1.27 ms    request=116 1.49 ms    request=117 1.25 ms
request=118 1.21 ms    request=119 1.32 ms    request=120 1.47 ms    request=121 1.39 ms
request=122 1.37 ms    request=123 1.30 ms    request=124 1.58 ms    request=125 1.25 ms
request=126 1.08 ms    request=127 1.04 ms    request=128 974.6 us   request=129 1.46 ms
request=130 1.34 ms    request=131 1.30 ms    request=132 880.9 us   request=133 1.21 ms
request=134 1.59 ms    request=135 1.35 ms    request=136 1.08 ms    request=137 984.3 us
request=138 1.17 ms    request=139 884.2 us   request=140 968.3 us   request=141 1.22 ms
request=142 1.11 ms    request=143 1.25 ms    request=144 1.06 ms    request=145 1.30 ms
request=146 1.36 ms    request=147 1.18 ms    request=148 1.19 ms    request=149 964.5 us
request=150 1.23 ms    request=151 1.18 ms    request=152 1.38 ms    request=153 1.23 ms
request=154 1.41 ms    request=155 1.08 ms    request=156 1.34 ms    request=157 1.27 ms
request=158 1.12 ms    request=159 1.12 ms    request=160 1.12 ms    request=161 968.4 us
request=162 1.36 ms    request=163 913.5 us   request=164 1.27 ms    request=165 1.03 ms
request=166 1.13 ms    request=167 1.06 ms    request=168 922.4 us   request=169 973.5 us
request=170 929.5 us   request=171 1.17 ms    request=172 970.2 us   request=173 1.45 ms
request=174 1.36 ms    request=175 960.2 us   request=176 1.22 ms    request=177 1.12 ms
request=178 1.55 ms    request=179 1.44 ms    request=180 1.51 ms    request=181 1.66 ms
request=182 1.70 ms    request=183 1.46 ms    request=184 1.41 ms    request=185 1.47 ms
request=186 1.48 ms    request=187 1.50 ms    request=188 1.44 ms    request=189 1.46 ms
request=190 1.45 ms    request=191 1.54 ms    request=192 1.07 ms    request=193 1.49 ms
request=194 1.53 ms    request=195 1.39 ms    request=196 1.38 ms    request=197 1.14 ms
request=198 1.43 ms    request=199 1.42 ms    request=200 1.05 ms
```

</details>

---

## Config B — Direct Laptop SD Slot (`/dev/mmcblk0p1`)

### hdparm — Raw Block Device Read

```
/dev/mmcblk0:
 Timing O_DIRECT disk reads: 250 MB in  3.01 seconds =  83.11 MB/s
```

### dd — Sequential Write (512 MB, fdatasync, 3 runs)

| Run   | Time    | Speed     |
|---|---|---|
| Run 1 | 16.39 s | 32.8 MB/s |
| Run 2 | 16.88 s | 31.8 MB/s |
| Run 3 | 16.85 s | 31.9 MB/s |

**Average: 32.2 MB/s** — highly stable across all three runs; no first-run throttle effect seen with USB.

### dd — Sequential Read (512 MB, cold cache, 3 runs)

| Run   | Time   | Speed     |
|---|---|---|
| Run 1 | 6.11 s | 87.8 MB/s |
| Run 2 | 6.31 s | 85.1 MB/s |
| Run 3 | 6.25 s | 85.9 MB/s |

**Average: 86.3 MB/s** — approaches the rated 100 MB/s ceiling.

### fio — 4K Random Write

```
QD1:  iops min=236  max=952  avg=666.34  stdev=285.86  bw=2487 KiB/s
QD32: iops min=202  max=940  avg=728.61  stdev=270.03  bw=2925 KiB/s
```

Stdev even higher than USB dock (~43% of mean) — write variance is a card-controller property, not USB-induced.

### fio — 4K Random Read

```
QD1:  iops min=1432 max=1838  avg=1613.66  stdev=70.01  bw=6444 KiB/s
QD32: iops min=1828 max=2018  avg=1945.22  stdev=43.31  bw=7780 KiB/s
```

QD32 improves by 21% over QD1 (vs 13% via USB) — the native interface exposes more parallelism benefit.

### ioping — Access Latency

```
199 requests completed in 2.90 s, 796 KiB read, 68 iops, 274.1 KiB/s
min/avg/max/mdev = 13.2 ms / 14.6 ms / 18.4 ms / 698.4 us
```

⚠️ Latency is 10× higher than via USB dock despite higher throughput. See analysis below.

<details>
<summary>Full ioping per-request log (direct slot)</summary>

```
request=2   14.5 ms    request=3   14.6 ms    request=4   15.5 ms    request=5   14.4 ms
request=6   15.5 ms    request=7   13.4 ms    request=8   14.5 ms    request=9   15.3 ms
request=10  15.4 ms    request=11  14.6 ms    request=12  15.3 ms    request=13  14.6 ms
request=14  14.2 ms    request=15  15.2 ms    request=16  15.5 ms    request=17  13.4 ms
request=18  14.6 ms    request=19  14.4 ms    request=20  15.1 ms    request=21  15.6 ms
request=22  15.4 ms    request=23  14.6 ms    request=24  14.3 ms    request=25  15.5 ms
request=26  16.7 ms    request=27  14.5 ms    request=28  14.5 ms    request=29  15.2 ms
request=30  14.7 ms    request=31  14.4 ms    request=32  14.6 ms    request=33  14.7 ms
request=34  14.3 ms    request=35  14.6 ms    request=36  14.4 ms    request=37  14.3 ms
request=38  14.4 ms    request=39  15.8 ms    request=40  14.2 ms    request=41  15.5 ms
request=42  14.3 ms    request=43  14.5 ms    request=44  14.6 ms    request=45  15.5 ms
request=46  14.2 ms    request=47  15.4 ms    request=48  14.3 ms    request=49  13.2 ms
request=50  13.5 ms    request=51  14.5 ms    request=52  14.2 ms    request=53  14.4 ms
request=54  14.4 ms    request=55  15.5 ms    request=56  13.3 ms    request=57  14.3 ms
request=58  14.5 ms    request=59  14.5 ms    request=60  14.3 ms    request=61  14.3 ms
request=62  14.5 ms    request=63  14.4 ms    request=64  15.4 ms    request=65  14.5 ms
request=66  14.5 ms    request=67  13.5 ms    request=68  15.6 ms    request=69  18.4 ms
request=70  14.4 ms    request=71  14.5 ms    request=72  17.3 ms    request=73  14.3 ms
request=74  15.5 ms    request=75  13.5 ms    request=76  14.2 ms    request=77  13.2 ms
request=78  15.2 ms    request=79  16.5 ms    request=80  15.4 ms    request=81  16.4 ms
request=82  15.5 ms    request=83  13.6 ms    request=84  14.8 ms    request=85  14.6 ms
request=86  14.4 ms    request=87  14.7 ms    request=88  14.3 ms    request=89  14.5 ms
request=90  14.5 ms    request=91  15.6 ms    request=92  14.2 ms    request=93  14.3 ms
request=94  14.3 ms    request=95  13.3 ms    request=96  14.4 ms    request=97  13.4 ms
request=98  14.3 ms    request=99  13.5 ms    request=100 14.3 ms    request=101 14.3 ms
request=102 15.4 ms    request=103 14.5 ms    request=104 14.3 ms    request=105 13.4 ms
request=106 14.2 ms    request=107 14.4 ms    request=108 14.4 ms    request=109 14.4 ms
request=110 14.5 ms    request=111 14.5 ms    request=112 14.6 ms    request=113 14.7 ms
request=114 14.6 ms    request=115 14.4 ms    request=116 14.6 ms    request=117 14.3 ms
request=118 14.4 ms    request=119 14.3 ms    request=120 14.6 ms    request=121 14.5 ms
request=122 14.3 ms    request=123 14.3 ms    request=124 13.4 ms    request=125 14.3 ms
request=126 15.9 ms    request=127 14.2 ms    request=128 14.4 ms    request=129 15.2 ms
request=130 14.4 ms    request=131 14.4 ms    request=132 13.5 ms    request=133 15.5 ms
request=134 14.6 ms    request=135 14.5 ms    request=136 14.3 ms    request=137 14.5 ms
request=138 14.3 ms    request=139 13.5 ms    request=140 14.5 ms    request=141 15.3 ms
request=142 14.3 ms    request=143 14.2 ms    request=144 14.2 ms    request=145 14.7 ms
request=146 13.9 ms    request=147 14.5 ms    request=148 14.2 ms    request=149 14.4 ms
request=150 14.6 ms    request=151 15.3 ms    request=152 14.6 ms    request=153 16.1 ms
request=154 14.3 ms    request=155 14.3 ms    request=156 13.4 ms    request=157 15.3 ms
request=158 14.4 ms    request=159 14.3 ms    request=160 14.5 ms    request=161 15.2 ms
request=162 14.2 ms    request=163 15.3 ms    request=164 14.3 ms    request=165 14.2 ms
request=166 14.4 ms    request=167 14.3 ms    request=168 16.2 ms    request=169 15.6 ms
request=170 15.3 ms    request=171 14.2 ms    request=172 14.3 ms    request=173 14.3 ms
request=174 14.6 ms    request=175 14.1 ms    request=176 14.2 ms    request=177 15.4 ms
request=178 14.0 ms    request=179 14.5 ms    request=180 14.6 ms    request=181 14.4 ms
request=182 14.4 ms    request=183 14.6 ms    request=184 14.4 ms    request=185 14.3 ms
request=186 14.2 ms    request=187 14.4 ms    request=188 14.2 ms    request=189 14.4 ms
request=190 14.1 ms    request=191 14.3 ms    request=192 15.6 ms    request=193 14.7 ms
request=194 14.5 ms    request=195 14.3 ms    request=196 14.4 ms    request=197 14.2 ms
request=198 14.6 ms    request=199 14.7 ms    request=200 14.4 ms
```

</details>

---

## Analysis: The ioping Latency Paradox

The direct slot is faster on every throughput metric yet shows 10× higher ioping latency. The explanation lies in how the two interfaces handle repeated small reads to the same location:

- **ioping** reads 4 KiB from the same filesystem directory entry 200 times in sequence. The USB mass storage layer in the docking station has its own internal read buffer (a small USB controller cache). After the first request, subsequent reads to the same block are served from that buffer — hence sub-millisecond responses.
- The **native SDIO/MMC interface** (direct slot) has no such intermediate cache. Every ioping request is dispatched as a real SD command to the flash media, incurring the card's full per-command latency (~14 ms), which is the card's actual hardware response time.
- **fio** scattered reads across a 256 MB file break the USB buffer effect. There the direct slot's bandwidth advantage dominates, yielding 59–70% more IOPS.

In short: the USB dock's ioping numbers were artificially good; the direct slot's ioping numbers reflect real flash latency.

---

## Methodology

| Test | Command / flags | Notes |
|---|---|---|
| hdparm raw read | `hdparm -t --direct /dev/mmcblk0` | Block device, bypasses FS and page cache |
| dd write | `dd … bs=1M conv=fdatasync` | Full hardware flush before timing |
| dd read | `echo 3 > drop_caches` before each run | Forces cold read from media |
| fio random | `--direct=1 --ioengine=libaio --bs=4k --runtime=30s` | Bypasses page cache; QD1 and QD32 |
| ioping | `ioping -c 200 <mountpoint>` | Filesystem-level, 4 KiB requests |
