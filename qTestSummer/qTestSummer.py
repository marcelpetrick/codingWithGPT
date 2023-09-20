# Helper to determine the totals for passed, failed, .. tests when running `make check`.
# Run cat make_check.txt | grep Totals | python3 QTest_prepareTotals.py

import sys
import re

def process_input(input_string):
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_blacklisted = 0
    total_runtime = 0

    for line in input_string.split("\n"):
        if line:  # check if line is not empty
            # Extract numbers using regular expression
            numbers = re.findall(r'\d+', line)
            if len(numbers) == 5:
                total_passed += int(numbers[0])
                total_failed += int(numbers[1])
                total_skipped += int(numbers[2])
                total_blacklisted += int(numbers[3])
                total_runtime += int(numbers[4])

    print(f"Totals: {total_passed} passed, {total_failed} failed, {total_skipped} skipped, {total_blacklisted} blacklisted, {total_runtime}ms")

# Read from stdin
if __name__ == "__main__":
    input_string = sys.stdin.read()
    process_input(input_string)
