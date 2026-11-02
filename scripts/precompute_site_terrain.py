#!/usr/bin/env python3

import argparse
import sys
import time

import _path  # noqa: F401

from bathymetry import site_cache
from bathymetry.config import DEFAULT_FILL_GAPS, DEFAULT_RADIUS
from bathymetry.dive_sites import load_sites
from bathymetry.terrain import PipelineError, load_elevation_grid, render_terrain


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--from-cache", action="store_true")
    args = parser.parse_args()

    sites = load_sites()
    for i, site in enumerate(sites, 1):
        lat, lon = site["lat"], site["lon"]
        prefix = f"[{i}/{len(sites)}] {site['name']}"
        if not args.recompute and site_cache.load(lat, lon) is not None:
            continue

        t0 = time.time()
        try:
            grid = site_cache.load_grid(lat, lon) if args.from_cache else None
            if grid is None:
                grid = load_elevation_grid(lat=lat, lon=lon, radius=DEFAULT_RADIUS)
                site_cache.save_grid(lat, lon, grid)
            result = render_terrain(grid, fill_gaps=DEFAULT_FILL_GAPS)
        except PipelineError as e:
            print(f"{prefix}: no data ({e}), skipping", file=sys.stderr)
            continue
        except Exception as e:
            print(f"{prefix}: FAILED ({e}), leaving uncached", file=sys.stderr)
            continue

        site_cache.save(lat, lon, result)
        print(f"{prefix}: cached ({time.time() - t0:.1f}s)")

    print("done")


if __name__ == "__main__":
    main()
