LANGS = ("en", "nl")
DEFAULT_LANG = "en"
LANG_NAMES = {"en": "English", "nl": "Nederlands"}

TR = {
    "en": {
        "title": "Zeeland Dive Maps",
        "tagline": "Interactive 3D terrain explorer",
        "pick_location_heading": "Pick a location",
        "search_placeholder": "Search dive site…",
        "search_no_results": "No matching dive sites",
        "settings_heading": "Settings",
        "low_coverage_short": "Show low-coverage sites",
        "picked_default": "No location picked yet.",
        "radius_label": "Radius (m)",
        "vaargeul": "Fairway",
        "vaargeul_tooltip": (
            "Measured subtidal bathymetry (RWS soundings, 1-10m resolution), source below the waterline. "
        ),
        "ahn_tooltip": (
            "AHN (0.5m resolution), national LiDAR elevation for dry land -- DTM (bare ground). "
        ),
        "fill_gaps_label": "Fill remaining gaps by interpolation",
        "generate_btn": "Generate",
        "generating_short": "Generating…",
        "progress_download_vaargeul": "Downloading fairway tiles",
        "progress_download_ahn": "Downloading AHN tiles",
        "progress_merge": "Merging elevation sources",
        "progress_fill_gaps": "Filling data gaps",
        "progress_render_2d": "Rendering 2D map",
        "progress_render_3d": "Building 3D model",
        "progress_cache_hit": "Loading from cache",
        "coverage_word": "coverage",
        "lang_nav_label": "Language",
        "tile_word": "tile",
        "tiles_word": "tiles",
        "empty_heading": "Pick a spot to begin",
        "empty_body": "Click the map or choose a dive site, then hit Generate to build the 2D map and 3D model.",
        "stat_rd": "Coordinates",
        "stats_unfilled_word": "unfilled after merge:",
        "stat_vaargeul_coverage": "fairway coverage",
        "stat_ahn_coverage": "ahn coverage",
        "map2d_heading": "2D map",
        "map2d_alt": "2D elevation map",
        "model3d_heading": "3D model",
        "share_btn": "Share",
        "share_copied": "Link copied!",
        "help_btn": "Help",
        "help_title": "About this tool",
        "help_intro": (
            "Pick a spot in Zeeland by clicking the map or choosing a divesite, and this tool "
            "merges elevation data from Dutch government sources into a single "
            "terrain grid, and renders a 2D elevation map plus an interactive 3D model you "
            "can rotate and zoom."
        ),
        "help_datum": (
            "Heights and depths are shown in m NAP. Land (from AHN, e.g. diked land that can sit below NAP) is "
            "shown in sand/brown tones by height above ground; open water (from vaargeul soundings) is shown in "
            "blue tones by depth."
        ),
        "help_merge": (
            "Where sources overlap, AHN (land) takes priority and vaargeul (water) fills in "
            "the rest, any pixel neither one reaches is a gap in the survey data."
        ),
        "help_gaps": (
            "Interpolation smooths over those gaps for a continuous 3D model; leave it off to see real holes where no survey data "
            "exists."
        ),
        "help_share": "Use Share to copy a link that reopens this exact location, radius and settings.",
        "help_close": "Close",
    },
    "nl": {
        "title": "Zeeland Duikkaarten",
        "tagline": "Interactieve 3D terreinverkenner",
        "pick_location_heading": "Kies een locatie",
        "search_placeholder": "Zoek duiklocatie…",
        "search_no_results": "Geen duiklocaties gevonden",
        "settings_heading": "Instellingen",
        "low_coverage_short": "Toon locaties met lage dekking",
        "picked_default": "Nog geen locatie gekozen.",
        "radius_label": "Straal (m)",
        "vaargeul": "Vaargeul",
        "vaargeul_tooltip": (
            "Gemeten onderwaterbathymetrie (RWS-lodingen, 1-10m resolutie)"
        ),
        "ahn_tooltip": (
            "AHN (0,5m resolutie), Actueel Hoogtebestand Nederland op basis van luchtlaserscanning "
            "voor droog land - DTM (kaal maaiveld)."
        ),
        "fill_gaps_label": "Resterende gaten opvullen door interpolatie",
        "generate_btn": "Genereer",
        "generating_short": "Bezig met genereren…",
        "progress_download_vaargeul": "Vaargeul-data downloaden",
        "progress_download_ahn": "AHN-data downloaden",
        "progress_merge": "Hoogtebronnen samenvoegen",
        "progress_fill_gaps": "Missende data opvullen",
        "progress_render_2d": "2D-kaart renderen",
        "progress_render_3d": "3D-model opbouwen",
        "progress_cache_hit": "Bezig met laden uit cache",
        "coverage_word": "dekking",
        "lang_nav_label": "Taal",
        "tile_word": "tegel",
        "tiles_word": "tegels",
        "empty_heading": "Kies een plek om te beginnen",
        "empty_body": "Klik op de kaart of kies een duiklocatie, en klik daarna op Genereer voor de 2D-kaart en het 3D-model.",
        "stat_rd": "Coördinaten",
        "stats_unfilled_word": "niet ingevuld na samenvoegen:",
        "stat_vaargeul_coverage": "vaargeul dekking",
        "stat_ahn_coverage": "ahn dekking",
        "map2d_heading": "2D-kaart",
        "map2d_alt": "2D-hoogtekaart",
        "model3d_heading": "3D-model",
        "share_btn": "Delen",
        "share_copied": "Link gekopieerd!",
        "help_btn": "Help",
        "help_title": "Over deze tool",
        "help_intro": (
            "Kies een plek in Zeeland door op de kaart te klikken of een duiklocatie te selecteren en deze tool "
            "voegt hoogtedata uit Nederlandse overheidsbronnen samen tot één "
            "raster, en toont een 2D-hoogtekaart en een interactief 3D-model."
        ),
        "help_datum": (
            "Hoogtes en dieptes worden getoond in m NAP. Land (uit AHN, zoals ingedijkt land dat onder NAP kan "
            "liggen) wordt in zand/bruine tinten getoond op basis van hoogte boven maaiveld; open water (uit "
            "vaargeul-lodingen) in blauwe tinten op basis van diepte."
        ),
        "help_merge": (
            "Waar bronnen overlappen heeft AHN (land) voorrang en vult vaargeul (water) de "
            "rest aan. Een pixel die door geen van beide wordt bereikt is een gat in de "
            "meetdata."
        ),
        "help_gaps": (
            "Interpolatie vult die gaten glad voor een doorlopend 3D-model. Laat de optie uit om echte gaten te zien waar geen "
            "meetdata bestaat."
        ),
        "help_share": "Gebruik Delen om een link te kopiëren die deze exacte locatie, straal en instellingen weer opent.",
        "help_close": "Sluiten",
    },
}


def normalize_lang(lang: str | None) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


