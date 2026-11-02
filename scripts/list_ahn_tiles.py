#!/usr/bin/env python3

import argparse
import sys
import urllib.request
from pathlib import Path

import _path
from pyproj import Transformer

from bathymetry.config import AHN_INDEX_PATH, RD_CRS, WGS84_CRS, ZEELAND_BOUNDS
from bathymetry.terrain.sources import tile_urls_in_bbox


def bounds_to_rd_bbox(bounds):
    """{south, west, north, east} in lat/lon -> (minx, maxx, miny, maxy) in RD New."""
    to_rd = Transformer.from_crs(WGS84_CRS, RD_CRS, always_xy=True)
    corners = [(bounds[lon], bounds[lat]) for lon in ("west", "east") for lat in ("south", "north")]
    xs, ys = zip(*(to_rd.transform(lon, lat) for lon, lat in corners))
    return min(xs), max(xs), min(ys), max(ys)


def download(urls, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        out_path = dest_dir / url.rsplit("/", 1)[-1]
        if out_path.exists():
            print(f"skip (exists): {out_path.name}", file=sys.stderr)
            continue
        print(f"downloading {out_path.name} ...", file=sys.stderr)
        tmp_path = out_path.with_suffix(out_path.suffix + ".part")
        urllib.request.urlretrieve(url, tmp_path)
        tmp_path.rename(out_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", metavar="DIR", type=Path,
                        help="download matching tiles into DIR instead of printing URLs")
    args = parser.parse_args()

    urls = tile_urls_in_bbox(AHN_INDEX_PATH, bounds_to_rd_bbox(ZEELAND_BOUNDS))
    if args.download:
        download(urls, args.download)
    else:
        print("\n".join(urls))


if __name__ == "__main__":
    main()
