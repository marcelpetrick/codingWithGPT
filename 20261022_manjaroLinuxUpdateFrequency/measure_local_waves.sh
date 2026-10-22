#!/usr/bin/env bash
# Measure Manjaro update waves from the local pacman log.
# A "wave" is a day with at least MIN_PKGS upgraded packages.
# Usage: ./measure_local_waves.sh [MIN_PKGS] [LOGFILE]
set -euo pipefail

min_pkgs="${1:-200}"
log="${2:-/var/log/pacman.log}"

[[ -r "$log" ]] || { echo "Cannot read $log" >&2; exit 1; }
grep -q '\[ALPM\] upgraded' "$log" || { echo "No upgrades found in $log" >&2; exit 1; }

# Whole days between two ISO dates; UTC midnights avoid DST off-by-one.
days_between() { echo $(( ($(date -u -d "$2" +%s) - $(date -u -d "$1" +%s)) / 86400 )); }

echo "Branch: $(pacman-mirrors -G 2>/dev/null || echo unknown)"
echo "Log starts: $(head -1 "$log" | cut -c2-11)"
echo
echo "Upgraded packages per month:"
grep '\[ALPM\] upgraded' "$log" | cut -c2-8 | sort | uniq -c | awk '{printf "  %s %5d\n", $2, $1}'
echo
echo "Waves (days with >= $min_pkgs upgrades) and gap to previous wave:"
waves=$(grep '\[ALPM\] upgraded' "$log" | cut -c2-11 | sort | uniq -c | awk -v min="$min_pkgs" '$1>=min{print $2, $1}')
[[ -n "$waves" ]] || { echo "  none"; exit 0; }
prev=""
while read -r day n; do
  gap="-"
  [[ -n "$prev" ]] && gap=$(days_between "$prev" "$day")
  printf "  %s %5d pkgs  gap %s d\n" "$day" "$n" "$gap"
  prev="$day"
done <<< "$waves"
echo
echo "Days since last wave ($prev): $(days_between "$prev" "$(date +%F)")"
