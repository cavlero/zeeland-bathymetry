import json

from .config import DIVE_SITES_PATH
from .site_cache import site_key


def load_sites() -> list[dict]:
    return json.loads(DIVE_SITES_PATH.read_text())


def save_sites(sites: list[dict]) -> None:
    DIVE_SITES_PATH.write_text(json.dumps(sites, indent=1, ensure_ascii=False) + "\n")


SITES = load_sites()

# selecting a dive site
SITE_KEYS = {site_key(s["lat"], s["lon"]) for s in SITES}
