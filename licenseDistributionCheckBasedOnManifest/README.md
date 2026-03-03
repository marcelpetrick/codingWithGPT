# License Manifest Summary

Summarizes license usage from a Yocto-style `*.license.manifest` file.

- Resolves **one license per component**
- Prefers (in order): `MIT` → `GPLv2` → `LGPLv2 / v2.1 / v3`
- Falls back to first parsed license if none match preference
- Reports ambiguous or missing license data
- Outputs terminal-friendly summary with ASCII bar charts
- Returns exit code `1` if ambiguities are detected (CI-friendly)

---

## Usage

```bash
./license_manifest_summary.py path/to/file.manifest
````

Optional:

```bash
./license_manifest_summary.py file.manifest --width 120 --show-ambiguous 0
```

### Options

* `--width` – Override terminal width
* `--show-ambiguous` – Number of ambiguous entries to display (`0` = show all)

---

## Output

Displays:

* Total components
* Resolved vs ambiguous count
* License distribution (bar chart)
* Percentage per license
* Detailed list of ambiguous entries

---

## Exit Codes

| Code | Meaning                                |
| ---- | -------------------------------------- |
| `0`  | All components resolved                |
| `1`  | Ambiguous or problematic entries found |
| `2`  | File error (missing/unreadable)        |
