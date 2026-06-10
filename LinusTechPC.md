# Linus Tech Tips — Threadripper 9960X Build
## Germany Price Check via Geizhals

> **Source:** [geizhals.at](https://geizhals.at) / [geizhals.de](https://geizhals.de) · Cheapest German (DE) vendor per component · Checked **2026-06-10**

---

## Parts List

| # | Category | Component | Vendor | Price |
|--:|----------|-----------|--------|------:|
| 1 | **CPU** | AMD Ryzen Threadripper 9960X (boxed) | ARLT Computer | €1,435.00 |
| 2 | **Motherboard** | GIGABYTE TRX50 AERO D | ARLT Computer | €666.22 |
| 3 | **SSD** | Samsung SSD 9100 PRO 2TB | ARLT Computer | €379.00 |
| 4 | **CPU Cooler** | Noctua NH-U14S TR5-SP6 | Cyberport | €128.23 |
| 5 | **GPU** | Intel Arc B580 Limited Edition | SD-Handel | €326.22 |
| 6 | **Case** | Fractal Design Torrent Black Solid | Caseking | €181.41 |
| 7 | **PSU** | Seasonic PRIME TX-1600 1600W 80+ Ti | ARLT Computer | €463.98 |
| 8 | **Monitor** | ASUS ProArt PA32QCV 31.5" 6K HDR | cw-mobile | €1,306.49 |
| 9 | **RAM** ⚠️ | G.Skill Zeta R5 Neo 192GB DDR5-6000 RDIMM | geizhals.de | ~€1,276.18 |

---

## Cost Breakdown

```
CPU        ████████████████████████████████████████  €1,435.00  (23.3%)
Monitor    ██████████████████████████████████        €1,306.49  (21.2%)
RAM        █████████████████████████████████         ~€1,276.18  (20.7%)
Mobo       █████████████████                           €666.22  (10.8%)
PSU        ████████████                                €463.98   (7.5%)
SSD        ██████████                                  €379.00   (6.1%)
GPU        █████████                                   €326.22   (5.3%)
Case       █████                                       €181.41   (2.9%)
Cooler     ████                                        €128.23   (2.1%)
           ──────────────────────────────────────────────────────────
TOTAL                                               ~€6,162.73
```

---

## Budget Summary

| Line item | EUR |
|-----------|----:|
| CPU + Motherboard | €2,101.22 |
| Storage (SSD) | €379.00 |
| Cooling (CPU cooler) | €128.23 |
| Graphics (GPU) | €326.22 |
| Chassis + PSU | €645.39 |
| Display | €1,306.49 |
| **LTT Parts Subtotal** | **€4,886.55** |
| RAM *(missing from LTT list — see below)* | ~€1,276.18 |
| **Grand Total** | **~€6,162.73** |

---

## ⚠️ Missing from LTT Parts List: RAM

The original Linus Tech Tips spec sheet **does not include memory** — the system will not POST without it.

**Why this RAM is special:**
The TRX50 platform (sTR5 socket) requires **DDR5 RDIMM (ECC Registered)** — regular desktop DDR5 UDIMM is electrically incompatible and will not work.

| Spec | Detail |
|------|--------|
| Type | DDR5 RDIMM ECC Registered |
| Recommended kit | G.Skill Zeta R5 Neo 192GB (4×48GB) DDR5-6000 CL30 |
| Slots used | 4 / 4 (quad-channel — fills all TRX50 AERO D slots) |
| Estimated DE price | ~€1,276 |
| Geizhals link | [Zeta R5 Neo 192GB on geizhals.de](https://geizhals.de/g-skill-zeta-r5-neo-rdimm-kit-192gb-f5-6000r3036g48gq4-zr5nk-a3221575.html) |

> **Note:** 128GB (4×32GB) kits have very limited German stock as of 2026-06-10. The 192GB (4×48GB) kit is the most readily available quad-channel option in DE. Monitor [the Zeta R5 Neo overview](https://geizhals.de/g-skill-zeta-r5-neo-ecc-rdimm-ddr5-v153551.html) for restock.

---

## Geizhals Links

| Component | Link |
|-----------|------|
| AMD Ryzen Threadripper 9960X | [geizhals.at](https://geizhals.at/amd-ryzen-threadripper-9960x-100-100001595wof-a3504021.html?hloc=de) |
| GIGABYTE TRX50 AERO D | [geizhals.at](https://geizhals.at/gigabyte-trx50-aero-d-a3047646.html?hloc=de) |
| Samsung SSD 9100 PRO 2TB | [geizhals.at](https://geizhals.at/samsung-ssd-9100-pro-2tb-mz-vap2t0bw-a3427162.html?hloc=de) |
| Noctua NH-U14S TR5-SP6 | [geizhals.at](https://geizhals.at/noctua-nh-u14s-tr5-sp6-a3047283.html?hloc=de) |
| Intel Arc B580 Limited Edition | [geizhals.at](https://geizhals.at/intel-arc-b580-limited-edition-31p06hb0ba-a3365436.html?hloc=de) |
| Fractal Design Torrent Black Solid | [geizhals.at](https://geizhals.at/fractal-design-torrent-black-solid-fd-c-tor1a-05-a2584614.html?hloc=de) |
| Seasonic PRIME TX-1600 ATX 3.1 | [geizhals.at](https://geizhals.at/seasonic-prime-tx-1600-1600w-atx-3-0-atx3-prime-tx-1600-a2986507.html?hloc=de) |
| ASUS ProArt PA32QCV | [geizhals.at](https://geizhals.at/asus-proart-pa32qcv-90lm0bd0-b01k71-a3553120.html?hloc=de) |
| G.Skill Zeta R5 Neo 192GB DDR5-6000 | [geizhals.de](https://geizhals.de/g-skill-zeta-r5-neo-rdimm-kit-192gb-f5-6000r3036g48gq4-zr5nk-a3221575.html) |

---

## Notes & Alternatives

- **GPU:** Board partner Arc B580 cards (Sparkle, ASRock) start from ~€258 in DE — cheaper than the Intel reference card if brand doesn't matter.
- **SSD:** A heatsink variant (MZ-VAP2T0GW) is available from ~€292 overall and is better suited to sustained high I/O workloads on a Threadripper platform.
- **Case:** The Fractal Design Torrent natively supports E-ATX. Black Solid is the cheapest variant; TG/RGB versions run €20–100 more.
- **RAM bandwidth:** Fully populating all 4 DIMM slots on the TRX50 is required to achieve peak quad-channel bandwidth on the 9960X.
