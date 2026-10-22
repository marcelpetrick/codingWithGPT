#!/usr/bin/env bash
# Compare package versions and build dates: Arch vs Manjaro unstable/testing/stable.
# Reads the repo databases directly, so no website parsing is needed.
# Output sections are tab-separated so make_onepager.py can parse them.
# Usage: ./measure_branch_lag.sh [pkg ...]
set -euo pipefail

manjaro_mirror="${MANJARO_MIRROR:-https://mirror.init7.net/manjaro}"
arch_mirror="${ARCH_MIRROR:-https://geo.mirror.pkgbuild.com}"
pkgs=("$@")
[[ ${#pkgs[@]} -gt 0 ]] || pkgs=(linux71 linux72 linux73 plasma-desktop mesa systemd firefox)
command -v gawk >/dev/null || { echo "gawk is required (strftime)" >&2; exit 1; }

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

# Write "name<TAB>version<TAB>builddate" for every package in a branch.
index() {
  for f in "$work/$1"-core.db "$work/$1"-extra.db; do
    tar -xOf "$f" --wildcards '*/desc'
  done | gawk '
    /^%NAME%$/      {getline; n=$0}
    /^%VERSION%$/   {getline; v=$0}
    /^%BUILDDATE%$/ {getline; print n "\t" v "\t" strftime("%Y-%m-%d", $0, 1)}'
}

echo "## state"
for br in arch unstable testing stable; do
  index "$br" > "$work/$br.idx"
  [[ -s "$work/$br.idx" ]] || { echo "Empty package index for $br" >&2; exit 1; }
  if [[ $br == arch ]]; then st="-"; else
    st=$(curl -fsS --max-time 20 "$manjaro_mirror/$br/state" | grep '^date=' | cut -d= -f2) || true
    [[ -n "$st" ]] || { echo "Cannot read state file for $br" >&2; exit 1; }
  fi
  printf "%s\t%s\n" "$br" "$st"
done

echo
echo "## versions (version (builddate)); columns: package arch unstable testing stable"
for p in "${pkgs[@]}"; do
  line="$p"
  for br in arch unstable testing stable; do
    cell=$(gawk -F'\t' -v p="$p" '$1==p{print $2" ("$3")"}' "$work/$br.idx")
    line+=$'\t'"${cell:--}"
  done
  echo "$line"
done

echo
echo "## builds per ISO week, last 8 weeks (only versions still in the repo)"
for br in arch unstable stable; do
  gawk -F'\t' -v br="$br" '{
      split($3, d, "-"); t = mktime(d[1] " " d[2] " " d[3] " 12 0 0", 1)
      c[strftime("%G-W%V", t, 1)]++
    } END {for (w in c) print br "\t" w "\t" c[w]}' "$work/$br.idx" | sort -k2 | tail -8
done
