import sys

TARGET_NAMES = ['Saketh', 'Prajwal', 'Victor', 'Sandeep', 'Thomas', 'Marcel']
COLUMNS = ['Department', 'Name', 'Acc. Delta 2025', 'thereof March 2025', 'thereof prior months']

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 main.py \"<pasted data>\"")
        sys.exit(1)

    raw = sys.argv[1]
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) % 5 != 0:
        print("⚠️ Warning: number of lines isn't a multiple of 5 — the last row might be malformed.")

    rows = [lines[i:i+5] for i in range(0, len(lines), 5)]
    filtered_rows = [r for r in rows if len(r) == 5 and r[0] != COLUMNS[0]]

    within = []
    outside = []

    for row in filtered_rows:
        _, name, acc_delta_str, _, _ = row

        if not any(key in name for key in TARGET_NAMES):
            continue

        try:
            acc_delta = int(acc_delta_str)
        except ValueError:
            continue

        if -8 <= acc_delta <= 8:
            within.append((name.strip(), acc_delta))
        else:
            outside.append((name.strip(), acc_delta))

    if outside:
        print("❌ Outside ±8 hours delta:\n")
        for name, delta in outside:
            print(f"{name}: {delta}h")
        print("\n" + "="*40 + "\n")

    if within:
        print("✅ Within ±8 hours delta:\n")
        for name, delta in within:
            print(f"{name}: {delta}h")
    else:
        print("✅ No one is within ±8 hours.")

if __name__ == "__main__":
    main()
