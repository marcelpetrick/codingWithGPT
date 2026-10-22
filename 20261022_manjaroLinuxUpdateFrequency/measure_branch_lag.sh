#!/usr/bin/env bash
# Compare package versions and build dates: Arch vs Manjaro unstable/testing/stable.
# Reads the repo databases directly, so no website parsing is needed.
# Usage: ./measure_branch_lag.sh [pkg ...]
set -euo pipefail

manjaro_mirror="${MANJARO_MIRROR:-https://mirror.init7.net/manjaro}"
arch_mirror="${ARCH_MIRROR:-https://geo.mirror.pkgbuild.com}"
pkgs=("$@")
[[ ${#pkgs[@]} -gt 0 ]] || pkgs=(linux71 linux72 linux73 plasma-desktop mesa systemd firefox)

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

fetch() {  # url, out — an empty or failed download stops the script
  curl -fsS --max-time 60 -o "$2" "$1" || { echo "Download failed: $1" >&2; exit 1; }
  [[ -s "$2" ]] || { echo "Empty download: $1" >&2; exit 1; }
}

for repo in core extra; do
  fetch "$arch_mirror/$repo/os/x86_64/$repo.db" "$work/arch-$repo.db"
  for br in unstable testing stable; do
    fetch "$manjaro_mirror/$br/$repo/x86_64/$repo.db" "$work/$br-$repo.db"
  done
done

# Print "name version builddate" for every package in a branch.
index() {
  for f in "$work/$1"-core.db "$work/$1"-extra.db; do
    tar -xOf "$f" --wildcards '*/desc'
  done | awk '
    /^%NAME%$/      {getline; n=$0}
    /^%VERSION%$/   {getline; v=$0}
    /^%BUILDDATE%$/ {getline; print n, v, strftime("%Y-%m-%d", $0, 1)}'
}

for br in arch unstable testing stable; do
  index "$br" > "$work/$br.idx"
  echo "$br state: $( [[ $br == arch ]] && echo - || curl -fsS --max-time 20 "$manjaro_mirror/$br/state" | grep '^date=' | cut -d= -f2)"
done
echo

printf "%-16s %-26s %-26s %-26s %-26s\n" package arch unstable testing stable
for p in "${pkgs[@]}"; do
  row=()
  for br in arch unstable testing stable; do
    row+=("$(awk -v p="$p" '$1==p{print $2" ("$3")"}' "$work/$br.idx")")
  done
  printf "%-16s %-26s %-26s %-26s %-26s\n" "$p" "${row[0]:--}" "${row[1]:--}" "${row[2]:--}" "${row[3]:--}"
done

echo
echo "Packages built per ISO week, last 8 weeks (only versions still in the repo):"
for br in arch stable; do
  echo "  $br:"
  awk '{print $3}' "$work/$br.idx" | while read -r d; do date -d "$d" +%G-W%V; done \
    | sort | uniq -c | tail -8 | awk '{printf "    %s %5d\n", $2, $1}'
done
