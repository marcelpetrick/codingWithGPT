#!/bin/bash
# run with ./runTestContinuously.sh ./tst_name
# or full path

# Check if test executable is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <test_executable>"
    exit 1
fi

test_executable=$1
run_counter=0

while true; do
    run_counter=$((run_counter + 1))
    result=$(echo -n "Run #$run_counter: " && $test_executable 2>&1 | grep "^Totals:")

    if [ -z "$result" ]; then
        echo "Run #$run_counter: No 'Totals:' line found. Continuing to next iteration."
        continue
    else
        echo "$result"
    fi

    # Extract the numbers of passed, failed, skipped, and blacklisted tests
    failed=$(echo "$result" | awk '{print $6}' | grep -o '[0-9]*')
    skipped=$(echo "$result" | awk '{print $10}' | grep -o '[0-9]*')
    blacklisted=$(echo "$result" | awk '{print $14}' | grep -o '[0-9]*')

    # Providing default values if variables are not set
    failed=${failed:-0}
    skipped=${skipped:-0}
    blacklisted=${blacklisted:-0}

    # Check if any of these numbers are greater than 0
    if [ "$failed" -gt 0 ] || [ "$skipped" -gt 0 ] || [ "$blacklisted" -gt 0 ]; then
        echo "Test failed, skipped, or blacklisted. Stopping the loop."
        break
    fi
done
