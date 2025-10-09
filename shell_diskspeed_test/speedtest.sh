#!/usr/bin/env bash
# io-speedtest-pretty.sh — test disk write/read speed using dd or fio.
# Usage: ./io-speedtest-pretty.sh [dd|fio] [filename]
# Env: SIZE_GB=10 (default 10 GB)

set -euo pipefail
METHOD="${1:-dd}"
FILE="${2:-io_testfile.bin}"
SIZE_GB="${SIZE_GB:-1}"

# Colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
RED="\033[1;31m"
RESET="\033[0m"

banner() {
  echo -e "\n${BLUE}=============================="
  echo -e "  $1"
  echo -e "==============================${RESET}\n"
}

status() {
  echo -e "${YELLOW}▶ $1${RESET}"
}

success() {
  echo -e "${GREEN}✔ $1${RESET}"
}

banner "Disk I/O Speed Test (${METHOD})"
echo "File: $FILE"
echo "Size: ${SIZE_GB}G"
echo

dd_write() {
  banner "WRITE TEST (dd)"
  status "Writing ${SIZE_GB}G of data to $FILE..."
  dd if=/dev/zero of="$FILE" bs=1G count="$SIZE_GB" oflag=direct status=progress conv=fdatasync 2>&1 | tee dd_write.log
  speed=$(grep -Eo '[0-9.]+ [MG]B/s' dd_write.log | tail -1 || true)
  success "Write completed — speed: ${speed:-unknown}"
}

dd_read() {
  banner "READ TEST (dd)"
  status "Reading ${SIZE_GB}G from $FILE..."
  dd if="$FILE" of=/dev/null bs=1G iflag=direct status=progress 2>&1 | tee dd_read.log
  speed=$(grep -Eo '[0-9.]+ [MG]B/s' dd_read.log | tail -1 || true)
  success "Read completed — speed: ${speed:-unknown}"
}

fio_write() {
  banner "WRITE TEST (fio)"
  status "Running fio write benchmark..."
  fio --name=write --filename="$FILE" --size="${SIZE_GB}G" \
      --rw=write --bs=1M --ioengine=libaio --direct=1 --iodepth=32 --numjobs=1 \
      --group_reporting | tee fio_write.log
  success "fio write test done."
}

fio_read() {
  banner "READ TEST (fio)"
  status "Running fio read benchmark..."
  fio --name=read --filename="$FILE" --size="${SIZE_GB}G" \
      --rw=read --bs=1M --ioengine=libaio --direct=1 --iodepth=32 --numjobs=1 \
      --group_reporting | tee fio_read.log
  success "fio read test done."
}

case "$METHOD" in
  dd)
    dd_write
    dd_read
    ;;
  fio)
    command -v fio >/dev/null || { echo -e "${RED}Error: fio not found${RESET}"; exit 1; }
    fio_write
    fio_read
    ;;
  *)
    echo -e "${RED}Error: unknown method '$METHOD' (use 'dd' or 'fio')${RESET}"
    exit 1
    ;;
esac

banner "SUMMARY"
if [ -f dd_write.log ]; then grep -Eo '[0-9.]+ [MG]B/s' dd_write.log | tail -1 | awk '{print "Write speed:", $0}'; fi
if [ -f dd_read.log ]; then grep -Eo '[0-9.]+ [MG]B/s' dd_read.log | tail -1 | awk '{print "Read speed:", $0}'; fi

echo
success "Test complete! File kept at $FILE — delete when done."
