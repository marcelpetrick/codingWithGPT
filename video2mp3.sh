#!/usr/bin/env bash
# Convert a video to MP3 and split into 10-minute pieces with 2-digit numbering.
# Usage: video_to_mp3_chunks.sh <input_video> [output_dir] [bitrate]
# Example: video_to_mp3_chunks.sh "My Talk.mp4" ./out 192k

set -euo pipefail
IFS=$'\n\t'

# ---- helpers ----
err() { printf "Error: %s\n" "$*" >&2; exit 1; }

# ---- deps ----
command -v ffmpeg >/dev/null 2>&1 || err "ffmpeg is not installed. On Manjaro: sudo pacman -S ffmpeg"

# ---- args ----
INPUT="${1:-}"
OUTDIR="${2:-}"
BITRATE="${3:-192k}"     # MP3 bitrate; change if you want

[ -n "$INPUT" ] || err "No input file provided.\nUsage: $0 <input_video> [output_dir] [bitrate]"
[ -f "$INPUT" ] || err "Input file not found: $INPUT"

if [ -z "$OUTDIR" ]; then
  OUTDIR="$(pwd)"
fi

mkdir -p "$OUTDIR"

# Base name without extension, preserve spaces
BASENAME="$(basename -- "$INPUT")"
NAME="${BASENAME%.*}"

# ---- work ----
# -vn                 : drop video
# -c:a libmp3lame     : encode to MP3
# -b:a $BITRATE       : target bitrate (e.g., 192k)
# -map a              : map only audio streams
# -f segment          : use the segment muxer
# -segment_time 600   : 600s = 10 minutes
# -segment_start_number 1 : start numbering at 01 (not 00)
# -reset_timestamps 1 : clean timestamps per segment
# -write_xing 0       : avoid writing VBR/Xing header per segment (helps duration accuracy)
# Output template     : NAME_01.mp3, NAME_02.mp3, ...
OUT_TEMPLATE="${OUTDIR}/${NAME}_%02d.mp3"

echo "Converting and splitting:"
echo "  Input:      $INPUT"
echo "  Output dir: $OUTDIR"
echo "  Bitrate:    $BITRATE"
echo

ffmpeg -hide_banner -y \
  -i "$INPUT" \
  -vn -c:a libmp3lame -b:a "$BITRATE" -map a \
  -f segment -segment_time 600 -segment_start_number 1 \
  -reset_timestamps 1 -write_xing 0 \
  "$OUT_TEMPLATE"

echo
echo "Done. Files written to: $OUTDIR"
