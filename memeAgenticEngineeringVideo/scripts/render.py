#!/usr/bin/env python3
"""Create editable captions and a landscape parody from a JSON card list."""
import argparse
import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def stamp(seconds, ass=False):
    ticks = round(seconds * (100 if ass else 1000))
    unit = 100 if ass else 1000
    hours, ticks = divmod(ticks, 3600 * unit)
    minutes, ticks = divmod(ticks, 60 * unit)
    secs, fraction = divmod(ticks, unit)
    return f'{hours}:{minutes:02}:{secs:02}.{fraction:02}' if ass else f'{hours:02}:{minutes:02}:{secs:02},{fraction:03}'


def build_cards(config):
    duration = float(config['duration'])
    cards = config['cards']
    if not cards or duration <= 0 or float(config.get('source_start', 0)) < 0:
        raise ValueError('Provide cards, a positive duration, and a nonnegative source start.')
    wrapped = []
    for card in cards:
        if not isinstance(card, str) or not card.strip() or any(c in card for c in '{}\\\n'):
            raise ValueError('Each card must be plain, nonempty text on one line.')
        lines = textwrap.wrap(card, width=36, break_long_words=False, break_on_hyphens=False)
        if len(lines) > 2 or any(len(line) > 36 for line in lines):
            raise ValueError(f'Card exceeds two 36-character lines: {card}')
        wrapped.append(lines)
    gap = 0.20
    available = duration - 2.0 - gap * len(cards)
    minimums = [max(2.5, len(''.join(lines)) / 17) for lines in wrapped]
    if sum(minimums) > available:
        raise ValueError('Cards need more time. Shorten the text or increase duration.')
    extra = (available - sum(minimums)) / len(cards)
    t = 1.0
    result = []
    for lines, minimum in zip(wrapped, minimums):
        end = t + minimum + extra
        result.append((t, end, lines))
        t = end + gap
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', type=Path)
    parser.add_argument('--source', type=Path, default=ROOT / 'source/el-risitas-clean.mp4')
    parser.add_argument('--captions-only', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.version.read_text(encoding='utf-8'))
    cards = build_cards(config)
    name = args.version.stem
    subdir = ROOT / 'subtitles'
    outdir = ROOT / 'output'
    subdir.mkdir(exist_ok=True)
    outdir.mkdir(exist_ok=True)
    srt = []
    events = []
    for index, (start, end, lines) in enumerate(cards, 1):
        srt.append(f'{index}\n{stamp(start)} --> {stamp(end)}\n' + '\n'.join(lines) + '\n')
        events.append(f"Dialogue: 0,{stamp(start, True)},{stamp(end, True)},Caption,,0,0,0,," + r'\N'.join(lines))
    (subdir / f'{name}.srt').write_text('\n'.join(srt), encoding='utf-8')
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 960
PlayResY: 930
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,38,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,2,30,30,58,1
Style: Notice,DejaVu Sans,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,8,20,20,12,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 1,0:00:00.00,0:00:06.00,Notice,,0,0,0,,PARODY SUBTITLES — NOT A TRANSLATION
'''
    ass = subdir / f'{name}.ass'
    ass.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')
    if args.captions_only:
        return
    source = args.source.resolve()
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(source)], check=True, capture_output=True, text=True)
    if float(probe.stdout.strip()) < float(config.get('source_start', 0)) + float(config['duration']):
        raise ValueError('Source is shorter than the requested cut.')
    # Use a relative ASS path so FFmpeg filter escaping does not depend on the checkout path.
    vf = f"scale=960:726:force_original_aspect_ratio=decrease,pad=960:930:(ow-iw)/2:0:black,ass=subtitles/{name}.ass"
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(config.get('source_start', 0)), '-i', str(source), '-t', str(config['duration']), '-vf', vf, '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(outdir / f'{name}.mp4')], check=True, cwd=ROOT)


if __name__ == '__main__':
    main()
