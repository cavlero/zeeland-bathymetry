#!/usr/bin/env python3

import argparse
import sys
import time

import _path  # noqa: F401

from bathymetry.config import DEFAULT_RADIUS
from bathymetry.dive_sites import load_sites, save_sites
from bathymetry.terrain import PipelineError, get_coverage_stats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recompute", action="store_true", help="redo every site")
    args = parser.parse_args()

    sites = load_sites()
    for i, site in enumerate(sites, 1):
        prefix = f"[{i}/{len(sites)}] {site['name']}"
        if not args.recompute and "coverage_pct" in site:
            continue

        t0 = time.time()
        try:
            stats = get_coverage_stats(lat=site["lat"], lon=site["lon"], radius=DEFAULT_RADIUS)
            site["coverage_pct"] = round(stats["combined_pct"], 1)
        except PipelineError:
            site["coverage_pct"] = 0.0
        except Exception as e:
            print(f"{prefix}: FAILED ({e}), leaving unset", file=sys.stderr)
            continue

        save_sites(sites)
        print(f"{prefix}: {site['coverage_pct']:.1f}% ({time.time() - t0:.1f}s)")

    print("done")


if __name__ == "__main__":
    main()
