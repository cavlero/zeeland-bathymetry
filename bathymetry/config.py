from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = ROOT_DIR / "static"
CACHE_DIR = ROOT_DIR / "site_cache"

DIVE_SITES_PATH = DATA_DIR / "dive_sites_zeeland.json"
AHN_INDEX_PATH = DATA_DIR / "kaartbladindex_dtm.json"

# Roughly covers Zeeland
ZEELAND_BOUNDS = {"south": 51.10, "west": 3.20, "north": 51.90, "east": 4.50}

MAX_RADIUS_M = 300 # keep low to prevent overloading public APIs

# to hide low coverage sites
LOW_COVERAGE_THRESHOLD = 60

DEFAULT_RADIUS = MAX_RADIUS_M
DEFAULT_FILL_GAPS = True

RD_CRS = "EPSG:28992"
WGS84_CRS = "EPSG:4326"
