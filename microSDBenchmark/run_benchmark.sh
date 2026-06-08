#!/usr/bin/env bash
# Benchmark script for Patriot VX Series 32GB microSD (sda1)
# Requires root. Run with: sudo bash run_benchmark.sh [runs] [size_mb]
# Defaults: 5 runs, 512 MB each

set -e

DEVICE=/dev/sda
PARTITION=/dev/sda1
MNT=/tmp/sdcard_bench
TESTFILE=$MNT/bench_test.bin
RESULT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULT_FILE="$RESULT_DIR/microSDBenchmark.md"
RUNS=${1:-5}
TEST_SIZE_MB=${2:-512}

extract_speed() {
    # Pulls "X MB/s" or "X GB/s" from dd/hdparm output
    grep -oP '\d+(\.\d+)? [MG]B/s' <<< "$1" | tail -1
}

to_mbs() {
    local val unit
    read val unit <<< "$1"
    if [[ "$unit" == "GB/s" ]]; then
        echo "$(awk "BEGIN{printf \"%.1f\", $val * 1024}")"
    else
        echo "$(awk "BEGIN{printf \"%.1f\", $val}")"
    fi
}

echo "==> Mounting $PARTITION at $MNT"
mkdir -p "$MNT"
mount "$PARTITION" "$MNT"

echo "==> hdparm raw read (single pass on block device)"
HDPARM_OUT=$(hdparm -t --direct "$DEVICE" 2>&1)
echo "$HDPARM_OUT"

WRITE_SPEEDS=()
READ_SPEEDS=()
WRITE_LINES=()
READ_LINES=()

for i in $(seq 1 "$RUNS"); do
    echo ""
    echo "--- Run $i / $RUNS ---"

    echo "  WRITE ${TEST_SIZE_MB} MB..."
    WRITE_OUT=$(dd if=/dev/zero of="$TESTFILE" bs=1M count="$TEST_SIZE_MB" conv=fdatasync 2>&1)
    WRITE_LINE=$(echo "$WRITE_OUT" | tail -1)
    echo "  $WRITE_LINE"
    WRITE_LINES+=("Run $i: $WRITE_LINE")
    spd=$(extract_speed "$WRITE_LINE")
    [[ -n "$spd" ]] && WRITE_SPEEDS+=("$(to_mbs "$spd")")

    echo "  Dropping page cache..."
    echo 3 > /proc/sys/vm/drop_caches

    echo "  READ ${TEST_SIZE_MB} MB..."
    READ_OUT=$(dd if="$TESTFILE" of=/dev/null bs=1M 2>&1)
    READ_LINE=$(echo "$READ_OUT" | tail -1)
    echo "  $READ_LINE"
    READ_LINES+=("Run $i: $READ_LINE")
    spd=$(extract_speed "$READ_LINE")
    [[ -n "$spd" ]] && READ_SPEEDS+=("$(to_mbs "$spd")")

    rm -f "$TESTFILE"
done

echo ""
echo "==> Unmounting"
umount "$MNT"

# Compute averages
avg() {
    local arr=("$@")
    local sum=0 count=${#arr[@]}
    [[ $count -eq 0 ]] && echo "N/A" && return
    for v in "${arr[@]}"; do sum=$(awk "BEGIN{print $sum + $v}"); done
    awk "BEGIN{printf \"%.1f\", $sum / $count}"
}

avg_write=$(avg "${WRITE_SPEEDS[@]}")
avg_read=$(avg "${READ_SPEEDS[@]}")

# Build run table rows
write_table=""
for line in "${WRITE_LINES[@]}"; do write_table+="| $line |"$'\n'; done
read_table=""
for line in "${READ_LINES[@]}"; do read_table+="| $line |"$'\n'; done

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

cat > "$RESULT_FILE" <<EOF
# microSD Benchmark — Patriot VX Series 32 GB

| Field       | Value |
|---|---|
| Card        | Patriot VX Series 32 GB |
| Speed Class | V30, UHS-I, Class 10 |
| Device      | $PARTITION (vfat) |
| Test size   | ${TEST_SIZE_MB} MB per run |
| Runs        | $RUNS |
| Host OS     | $(uname -sr) |
| Date        | $TIMESTAMP |

## Summary

| Metric              | Value |
|---|---|
| Avg sequential write | ${avg_write} MB/s |
| Avg sequential read  | ${avg_read} MB/s |
| Rated read speed     | 100 MB/s |
| Rated write speed    | 80 MB/s (V30 min: 30 MB/s) |

## hdparm — Raw Block Device Read

\`\`\`
$HDPARM_OUT
\`\`\`

## dd — Sequential Write (${TEST_SIZE_MB} MB, fdatasync, $RUNS runs)

| Run | Result |
|---|---|
$write_table
**Average: ${avg_write} MB/s**

## dd — Sequential Read (${TEST_SIZE_MB} MB, cold cache, $RUNS runs)

| Run | Result |
|---|---|
$read_table
**Average: ${avg_read} MB/s**

## Methodology

- Write: \`dd if=/dev/zero of=<file> bs=1M count=${TEST_SIZE_MB} conv=fdatasync\` — forces hardware flush before timing ends.
- Read: \`echo 3 > /proc/sys/vm/drop_caches\` before each pass to ensure cold cache.
- \`hdparm -t --direct\` reads the raw block device, bypassing filesystem and page cache.
- Test file is deleted between runs; card stays mounted for the full session.
EOF

echo ""
echo "==> Done. Results written to: $RESULT_FILE"
echo "    Avg write: ${avg_write} MB/s | Avg read: ${avg_read} MB/s"
