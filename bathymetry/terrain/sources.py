import json
import logging
import re
import urllib.request
from functools import lru_cache
from pathlib import Path

from ..config import AHN_INDEX_PATH

log = logging.getLogger(__name__)

RWS_DOWNLOADS = "https://downloads.rijkswaterstaatdata.nl"
VAARGEUL_10M_URL = f"{RWS_DOWNLOADS}/bodemhoogte_zeeland/bodemhoogte_zeeland.tif"
VAARGEUL_1M_DIR = f"{RWS_DOWNLOADS}/bodemhoogte_1mtr/"

# Keeps /vsicurl/ reads limited to the byte ranges actually needed.
GDAL_STREAMING_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
    VSI_CACHE="TRUE",
)

_VSICURL = "/vsicurl/"


def vsicurl(url: str) -> str:
    return _VSICURL + url


def display_path(path: str) -> str:
    """Strip the /vsicurl/ prefix so the URL can be shown to users."""
    return path.removeprefix(_VSICURL)


# AHN

def _feature_bbox(feature) -> tuple[float, float, float, float]:
    """(minx, maxx, miny, maxy) of a Polygon/MultiPolygon feature."""
    xs, ys = [], []

    def collect(coords):
        if isinstance(coords[0], (int, float)):
            xs.append(coords[0])
            ys.append(coords[1])
        else:
            for c in coords:
                collect(c)

    collect(feature["geometry"]["coordinates"])
    return min(xs), max(xs), min(ys), max(ys)


def _overlaps(a, b) -> bool:
    aminx, amaxx, aminy, amaxy = a
    bminx, bmaxx, bminy, bmaxy = b
    return aminx <= bmaxx and amaxx >= bminx and aminy <= bmaxy and amaxy >= bminy


@lru_cache(maxsize=None)
def _load_tile_index(index_path: Path) -> tuple[tuple[tuple, str], ...]:
    """((bbox, url), ...) for every tile in a kaartbladindex file. Cached,
    since the files are ~1 MB and don't change at runtime."""
    index = json.loads(index_path.read_text())
    return tuple(
        (_feature_bbox(f), f["properties"]["url"]) for f in index["features"]
    )


def tile_urls_in_bbox(index_path: Path, rd_bbox) -> list[str]:
    """URLs of every tile overlapping rd_bbox (minx, maxx, miny, maxy, RD New)."""
    return [url for bbox, url in _load_tile_index(index_path) if _overlaps(bbox, rd_bbox)]


def ahn_paths(minx, miny, maxx, maxy) -> list[str]:
    """/vsicurl/ paths of every AHN tile overlapping the RD bbox."""
    urls = tile_urls_in_bbox(AHN_INDEX_PATH, (minx, maxx, miny, maxy))
    return [vsicurl(u) for u in urls]


# vaargeul

@lru_cache(maxsize=None)
def _list_tif_filenames(dir_url: str) -> frozenset[str]:
    """.tif filenames linked from an HTML directory listing. Cached for the
    life of the process (source does not update frequently)"""
    with urllib.request.urlopen(dir_url, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    return frozenset(re.findall(r'href="([^"/?][^"]*\.TIF)"', html, re.IGNORECASE))


def _vaargeul_1m_zeeland_tiles() -> list[str]:
    """NAP-referenced 1 m tiles covering Zeeland (the Z*_NAP.tif files).
    The _LAT.tif variants use a different datum and are skipped."""
    try:
        filenames = _list_tif_filenames(VAARGEUL_1M_DIR)
    except Exception as e:
        log.warning("vaargeul 1m listing failed: %s", e)
        return []
    return sorted(
        f for f in filenames
        if f.upper().startswith("Z") and f.upper().endswith("_NAP.TIF")
    )


def vaargeul_paths() -> list[str]:
    """/vsicurl/ paths, highest resolution first. Earlier tiles win when
    merging, 10m composite fills only missed area from 1m tiles"""
    paths = [vsicurl(VAARGEUL_1M_DIR + f) for f in _vaargeul_1m_zeeland_tiles()]
    paths.append(vsicurl(VAARGEUL_10M_URL))
    return paths
