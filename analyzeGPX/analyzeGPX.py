"""
analyzeGpx.py
--------------
Compute the total length of a GPX track using accurate geodesic distance.

Usage::

    python3 analyzeGpx.py my_track.gpx

Dependencies are listed in *requirements.txt* (see below).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator

import gpxpy  # type: ignore
from geopy.distance import geodesic  # type: ignore


def load_gpx(path: Path) -> gpxpy.gpx.GPX:
    """Parse *path* into a :class:`gpxpy.gpx.GPX` object."""
    with path.open(encoding="utf‑8") as fh:
        return gpxpy.parse(fh)


def iter_points(gpx: gpxpy.gpx.GPX) -> Iterator[gpxpy.gpx.GPXTrackPoint]:
    """Yield every point in every track/segment in the GPX file."""
    for track in gpx.tracks:
        for segment in track.segments:
            yield from segment.points


def total_length_km(gpx: gpxpy.gpx.GPX) -> float:
    """Return the 2‑D geodesic length of *gpx* in kilometres."""
    length_m = 0.0
    prev = None

    for pt in iter_points(gpx):
        if prev is not None:
            length_m += geodesic(
                (prev.latitude, prev.longitude),
                (pt.latitude, pt.longitude),
            ).meters
        prev = pt

    return length_m / 1000.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute total distance of a GPX file.",
        epilog="Example: python3 analyzeGpx.py foo.gpx",
    )
    parser.add_argument("gpx_file", type=Path, help="Path to GPX file")
    args = parser.parse_args()

    gpx = load_gpx(args.gpx_file)
    distance = total_length_km(gpx)
    print(f"Total distance: {distance:.2f} km")


if __name__ == "__main__":
    main()
