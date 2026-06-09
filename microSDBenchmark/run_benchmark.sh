#!/usr/bin/env bash
# Benchmark script for microSD cards.
# Requires root. Run with: sudo bash run_benchmark.sh [runs] [size_mb]
# Defaults: 3 runs, 512 MB each
# Dependencies: hdparm, dd, fio, ioping

set -e

DEVICE=/dev/mmcblk0
PARTITION=/dev/mmcblk0p1
MNT=/tmp/sdcard_bench
TESTFILE=$MNT/bench_test.bin
RUNS=${1:-3}
TEST_SIZE_MB=${2:-512}

extract_speed() {
    grep -oP '\d+(\.\d+)? [MG]B/s' <<< "$1" | tail -1
}

to_mbs() {
    local val unit
    read val unit <<< "$1"
    if [[ "$unit" == "GB/s" ]]; then
        awk "BEGIN{printf \"%.1f\", $val * 1024}"
    else
        awk "BEGIN{printf \"%.1f\", $val}"
    fi
}

avg() {
    local arr=("$@")
    local sum=0 count=${#arr[@]}
    [[ $count -eq 0 ]] && echo "N/A" && return
    for v in "${arr[@]}"; do sum=$(awk "BEGIN{print $sum + $v}"); done
    awk "BEGIN{printf \"%.1f\", $sum / $count}"
}

echo "==> Mounting $PARTITION at $MNT"
mkdir -p "$MNT"
mount "$PARTITION" "$MNT"

# --- hdparm raw read ---
echo ""
echo "==> hdparm: raw block device read"
HDPARM_OUT=$(hdparm -t --direct "$DEVICE" 2>&1)
echo "$HDPARM_OUT"

# --- dd sequential runs ---
WRITE_SPEEDS=()
READ_SPEEDS=()

for i in $(seq 1 "$RUNS"); do
    echo ""
    echo "--- Sequential run $i / $RUNS ---"

    echo "  WRITE ${TEST_SIZE_MB} MB..."
    WRITE_OUT=$(dd if=/dev/zero of="$TESTFILE" bs=1M count="$TEST_SIZE_MB" conv=fdatasync 2>&1)
    WRITE_LINE=$(echo "$WRITE_OUT" | tail -1)
    echo "  $WRITE_LINE"
    spd=$(extract_speed "$WRITE_LINE")
    [[ -n "$spd" ]] && WRITE_SPEEDS+=("$(to_mbs "$spd")")

    echo "  Dropping page cache..."
    echo 3 > /proc/sys/vm/drop_caches

    echo "  READ ${TEST_SIZE_MB} MB..."
    READ_OUT=$(dd if="$TESTFILE" of=/dev/null bs=1M 2>&1)
    READ_LINE=$(echo "$READ_OUT" | tail -1)
    echo "  $READ_LINE"
    spd=$(extract_speed "$READ_LINE")
    [[ -n "$spd" ]] && READ_SPEEDS+=("$(to_mbs "$spd")")

    rm -f "$TESTFILE"
done

avg_write=$(avg "${WRITE_SPEEDS[@]}")
avg_read=$(avg "${READ_SPEEDS[@]}")

# --- fio 4K random I/O ---
echo ""
echo "==> fio: 4K random write (queue depth 1, 30s)"
FIO_RNDW_QD1=$(fio --name=4k_rndwrite_qd1 \
    --filename="$MNT/fio_test.bin" \
    --rw=randwrite --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=1 \
    --size=256m --runtime=30 --time_based \
    --output-format=normal 2>&1)
echo "$FIO_RNDW_QD1" | grep -E "iops|bw="
rm -f "$MNT/fio_test.bin"

echo ""
echo "==> fio: 4K random write (queue depth 32, 30s)"
FIO_RNDW_QD32=$(fio --name=4k_rndwrite_qd32 \
    --filename="$MNT/fio_test.bin" \
    --rw=randwrite --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=32 \
    --size=256m --runtime=30 --time_based \
    --output-format=normal 2>&1)
echo "$FIO_RNDW_QD32" | grep -E "iops|bw="
rm -f "$MNT/fio_test.bin"

echo ""
echo "==> fio: 4K random read (queue depth 1, 30s)"
# pre-create file for read test
dd if=/dev/urandom of="$MNT/fio_test.bin" bs=1M count=256 conv=fdatasync &>/dev/null
echo 3 > /proc/sys/vm/drop_caches
FIO_RNDR_QD1=$(fio --name=4k_rndread_qd1 \
    --filename="$MNT/fio_test.bin" \
    --rw=randread --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=1 \
    --size=256m --runtime=30 --time_based \
    --output-format=normal 2>&1)
echo "$FIO_RNDR_QD1" | grep -E "iops|bw="

echo ""
echo "==> fio: 4K random read (queue depth 32, 30s)"
echo 3 > /proc/sys/vm/drop_caches
FIO_RNDR_QD32=$(fio --name=4k_rndread_qd32 \
    --filename="$MNT/fio_test.bin" \
    --rw=randread --bs=4k --direct=1 \
    --ioengine=libaio --iodepth=32 \
    --size=256m --runtime=30 --time_based \
    --output-format=normal 2>&1)
echo "$FIO_RNDR_QD32" | grep -E "iops|bw="
rm -f "$MNT/fio_test.bin"

# --- ioping latency ---
echo ""
echo "==> ioping: access latency (200 requests)"
IOPING_OUT=$(ioping -c 200 "$MNT" 2>&1)
echo "$IOPING_OUT"

# --- cleanup ---
echo ""
echo "==> Unmounting"
umount "$MNT"

echo ""
echo "==> Done. Results were printed to stdout; no markdown file was updated."
echo "    Avg sequential write: ${avg_write} MB/s | Avg sequential read: ${avg_read} MB/s"
