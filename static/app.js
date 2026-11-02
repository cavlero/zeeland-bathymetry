import htm from 'https://unpkg.com/htm@3.1.1/dist/htm.module.js';
import { Scene3D } from './scene3d.js';

const html = htm.bind(React.createElement);
const { useState, useEffect, useRef, useCallback } = React;

// Progress steps in the order /api/generate reports them
function planStages(fillGaps, t) {
  const keys = ["download_vaargeul", "download_ahn", "merge"];
  if (fillGaps) keys.push("fill_gaps");
  keys.push("render_2d", "render_3d");
  return keys.map(key => ({ key, label: t["progress_" + key], status: "pending", detail: null }));
}

function applyProgressEvent(stages, evt, t) {
  const idx = stages.findIndex(s => s.key === evt.stage);
  if (idx === -1) return stages;
  return stages.map((s, i) => {
    if (i < idx) return s.status === "done" ? s : { ...s, status: "done" };
    if (i > idx) return s;
    if (evt.status === "done" && evt.files) {
      const detail = `${evt.files.length} ${evt.files.length === 1 ? t.tile_word : t.tiles_word}`;
      return { ...s, status: "active", detail };
    }
    return { ...s, status: "active" };
  });
}

function coverageColor(pct) {
  if (pct === null || pct === undefined) return '#64748b';
  const hue = Math.max(0, Math.min(100, pct)) * 1.2;
  return `hsl(${hue}, 75%, 55%)`;
}

async function getJSON(url) {
  const res = await fetch(url);
  return res.json();
}

/* subcomponents */

function BrandMark() {
  return html`
    <div class="brand-mark">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M2 17c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"
          stroke="#05131a" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M2 12c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"
          stroke="#05131a" stroke-width="1.8" stroke-linecap="round" opacity="0.55"/>
        <circle cx="12" cy="6" r="2.4" fill="#05131a"/>
      </svg>
    </div>
  `;
}

function Header({ lang, setLang, langNames, t, langs }) {
  const [showHelp, setShowHelp] = useState(false);

  return html`
    <header class="topbar">
      <div class="brand">
        <${BrandMark} />
        <div>
          <div class="brand-title">${t.title}</div>
          <div class="brand-sub">${t.tagline}</div>
        </div>
      </div>
      <div class="topbar-right">
        <button class="help-btn" onClick=${() => setShowHelp(true)} aria-label=${t.help_btn} title=${t.help_btn}>
          <${HelpIcon} />
        </button>
        <div class="lang-pill" role="group" aria-label=${t.lang_nav_label}>
          ${langs.map(code => html`
            <button
              key=${code}
              class=${code === lang ? "active" : ""}
              aria-current=${code === lang ? "true" : "false"}
              onClick=${() => setLang(code)}
            >${langNames[code]}</button>
          `)}
        </div>
      </div>
      ${showHelp ? html`<${HelpModal} t=${t} onClose=${() => setShowHelp(false)} />` : null}
    </header>
  `;
}

function Switch({ checked, onChange, name, hint, id }) {
  return html`
    <div class="switch-row">
      <div class="switch-label">
        <span class="name">${name}</span>
        ${hint ? html`<span class="hint">${hint}</span>` : null}
      </div>
      <label class="switch">
        <input type="checkbox" checked=${checked} onChange=${e => onChange(e.target.checked)} aria-label=${name} />
        <span class="track"></span>
        <span class="thumb"></span>
      </label>
    </div>
  `;
}

function SiteSearch({ sites, t, onSelect }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const q = query.trim().toLowerCase();
  const matches = q.length === 0 ? [] : sites.filter(s => s.name.toLowerCase().includes(q)).slice(0, 8);

  function choose(site) {
    onSelect(site);
    setQuery(site.name);
    setOpen(false);
  }

  return html`
    <div class="site-search" ref=${wrapRef}>
      <svg class="site-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none">
        <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="1.8"/>
        <path d="M21 21l-4.3-4.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
      <input
        type="text" class="site-search-input" placeholder=${t.search_placeholder}
        value=${query}
        onFocus=${() => setOpen(true)}
        onChange=${e => { setQuery(e.target.value); setOpen(true); }}
        onKeyDown=${e => { if (e.key === "Escape") { setOpen(false); e.target.blur(); } }}
      />
      ${open && q.length > 0 ? html`
        <div class="site-search-results">
          ${matches.length > 0
            ? matches.map(site => html`
              <button key=${site.name} type="button" class="site-search-item" onClick=${() => choose(site)}>
                <span class="dot" style=${{ background: coverageColor(site.coverage_pct) }}></span>
                <span class="name">${site.name}</span>
                ${site.coverage_pct != null ? html`<span class="pct mono">${site.coverage_pct.toFixed(0)}%</span>` : null}
              </button>
            `)
            : html`<div class="site-search-empty">${t.search_no_results}</div>`}
        </div>
      ` : null}
    </div>
  `;
}

function MapCard({ mapRef, picked, t, showLowCoverage, setShowLowCoverage, sites, onSelectSite }) {
  return html`
    <div class="card">
      <h2>${t.pick_location_heading}</h2>
      <${SiteSearch} sites=${sites} t=${t} onSelect=${onSelectSite} />
      <div id="map" ref=${mapRef}></div>
      <div class=${"picked-line" + (picked ? " has-pick" : "")}>
        <span class="dot"></span>
        <span class="mono">
          ${picked
            ? (picked.label ? picked.label + " - " : "") + `lat ${picked.lat.toFixed(5)}, lon ${picked.lon.toFixed(5)}`
            : t.picked_default}
        </span>
      </div>
      <div class="low-cov-row">
        <${Switch}
          checked=${showLowCoverage}
          onChange=${setShowLowCoverage}
          name=${t.low_coverage_short}
        />
      </div>
    </div>
  `;
}

function ControlsCard({ t, radius, setRadius, fillGaps, setFillGaps, picked, status, onGenerate }) {
  const busy = status === "loading";
  return html`
    <div class="card">
      <h2>${t.settings_heading}</h2>

      <div class="switch-label" style=${{ marginBottom: "0.15rem" }}>
        <span class="name">${t.radius_label}</span>
      </div>
      <input
        type="range" min="20" max="300" step="10" value=${radius}
        onInput=${e => setRadius(Number(e.target.value))}
      />
      <div class="radius-value">${radius} m</div>

      <div class="divider"></div>

      <${Switch} checked=${fillGaps} onChange=${setFillGaps} name=${t.fill_gaps_label} />

      <button class="btn-generate" disabled=${!picked || busy} onClick=${onGenerate}>
        ${busy ? html`<span class="spin"></span>` : null}
        ${busy ? t.generating_short : t.generate_btn}
      </button>
    </div>
  `;
}

function ShareIcon() {
  return html`
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <circle cx="18" cy="5" r="2.5" stroke="currentColor" stroke-width="1.7"/>
      <circle cx="6" cy="12" r="2.5" stroke="currentColor" stroke-width="1.7"/>
      <circle cx="18" cy="19" r="2.5" stroke="currentColor" stroke-width="1.7"/>
      <path d="M8.2 10.8l7.6-4.6M8.2 13.2l7.6 4.6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
    </svg>
  `;
}

function HomeIcon() {
  return html`
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M4 11.5L12 4l8 7.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M6 10v9h12v-9" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M10 19v-5h4v5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `;
}

function HelpIcon() {
  return html`
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/>
      <path d="M9.3 9.3a2.7 2.7 0 1 1 3.9 2.4c-.75.4-1.2.9-1.2 1.8v.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="12" cy="17.2" r="1.05" fill="currentColor"/>
    </svg>
  `;
}

function CloseIcon() {
  return html`
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M5 5l14 14M19 5L5 19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `;
}

function HelpModal({ t, onClose }) {
  useEffect(() => {
    const onKey = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return html`
    <div class="help-overlay" onClick=${onClose}>
      <div class="help-modal" onClick=${e => e.stopPropagation()}>
        <button class="help-modal-close" onClick=${onClose} aria-label=${t.help_close}><${CloseIcon} /></button>
        <h2>${t.help_title}</h2>
        <p>${t.help_intro}</p>
        <p>${t.help_datum}</p>
        <ul>
          <li><strong>AHN</strong>: ${t.ahn_tooltip}</li>
          <li><strong>${t.vaargeul}</strong>: ${t.vaargeul_tooltip}</li>
        </ul>
        <p>${t.help_merge}</p>
        <p>${t.help_gaps}</p>
        <p>${t.help_share}</p>
      </div>
    </div>
  `;
}

function StatCard({ label, value, barPct, barColor }) {
  return html`
    <div class="stat-card">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
      ${barPct !== undefined ? html`
        <div class="stat-bar"><div class="fill" style=${{ width: barPct + "%", background: barColor }}></div></div>
      ` : null}
    </div>
  `;
}

function EmptyState({ t }) {
  return html`
    <div class="empty-state">
      <div class="icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path d="M3 16c1.6 1.4 3.2 1.4 4.8 0s3.2-1.4 4.8 0 3.2 1.4 4.8 0 3.2-1.4 4.8 0"
            stroke="#22d3ee" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M3 11c1.6 1.4 3.2 1.4 4.8 0s3.2-1.4 4.8 0 3.2 1.4 4.8 0 3.2-1.4 4.8 0"
            stroke="#6366f1" stroke-width="1.6" stroke-linecap="round" opacity="0.6"/>
          <circle cx="12" cy="6" r="2" stroke="#e8edf5" stroke-width="1.6"/>
        </svg>
      </div>
      <h3>${t.empty_heading}</h3>
      <p>${t.empty_body}</p>
    </div>
  `;
}

function CheckIcon() {
  return html`
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M4 12.5l5 5.5L20 6" stroke="#34d399" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `;
}

function ProgressCard({ t, stages }) {
  const total = stages.length || 1;
  const doneCount = stages.filter(s => s.status === "done").length;
  const activeCount = stages.some(s => s.status === "active") ? 0.5 : 0;
  const pct = Math.min(100, Math.round(((doneCount + activeCount) / total) * 100));

  return html`
    <div class="progress-card">
      <div class="progress-bar-track"><div class="progress-bar-fill" style=${{ width: pct + "%" }}></div></div>
      <ul class="progress-steps">
        ${stages.map(s => html`
          <li key=${s.key} class=${"progress-step " + s.status}>
            <span class="step-icon">
              ${s.status === "done"
                ? html`<${CheckIcon} />`
                : s.status === "active"
                  ? html`<span class="spin"></span>`
                  : html`<span class="step-dot"></span>`}
            </span>
            <span class="step-label">${s.label}</span>
            ${s.detail ? html`<span class="step-detail mono">${s.detail}</span>` : null}
          </li>
        `)}
      </ul>
    </div>
  `;
}

function ResultsPanel({ t, status, error, result, activeTab, setActiveTab, stages }) {
  const [copied, setCopied] = useState(false);

  if (status === "idle") return html`<${EmptyState} t=${t} />`;

  if (status === "loading") {
    return html`<${ProgressCard} t=${t} stages=${stages} />`;
  }

  if (status === "error") {
    return html`
      <div class="error-card">
        <strong>⚠</strong>
        <span>${error}</span>
      </div>
    `;
  }

  const stats = result.stats;
  const cov = stats.coverage;
  const center = result.center;

  function onShare() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  }

  return html`
    <div>
      <div class="stat-row">
        <${StatCard} label=${t.stat_rd} value=${`${center.lat.toFixed(5)}, ${center.lon.toFixed(5)}`} />
        <${StatCard} label=${t.stat_vaargeul_coverage} value=${cov.vaargeul.toFixed(1) + "%"} barPct=${cov.vaargeul} barColor="var(--vaargeul)" />
        <${StatCard} label=${t.stat_ahn_coverage} value=${cov.ahn.toFixed(1) + "%"} barPct=${cov.ahn} barColor="var(--ahn)" />
      </div>

      <div class="tabs">
        <button class=${"tab-btn" + (activeTab === "3d" ? " active" : "")} onClick=${() => setActiveTab("3d")}>${t.model3d_heading}</button>
        <button class=${"tab-btn" + (activeTab === "2d" ? " active" : "")} onClick=${() => setActiveTab("2d")}>${t.map2d_heading}</button>
        <button class=${"tab-btn share-btn" + (copied ? " copied" : "")} onClick=${onShare}>
          <${ShareIcon} />${copied ? t.share_copied : t.share_btn}
        </button>
      </div>

      <div class="media-card">
        ${activeTab === "3d"
          ? html`<${Scene3D} scene=${result.scene3d} t=${t} />`
          : html`<img src=${"data:image/png;base64," + result.png_base64} alt=${t.map2d_alt} />`}
      </div>

      <div class="gap-info">${t.stats_unfilled_word} ${stats.gap_pct.toFixed(1)}%</div>
    </div>
  `;
}

/* app */

function App() {
  const [lang, setLang] = useState(localStorage.getItem("bx_lang") || "en");
  const [config, setConfig] = useState(null);
  const [strings, setStrings] = useState(null);
  const [picked, setPicked] = useState(null);
  const [radius, setRadius] = useState(300);
  const [fillGaps, setFillGaps] = useState(true);
  const [showLowCoverage, setShowLowCoverage] = useState(false);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("3d");
  const [stages, setStages] = useState([]);

  const mapRef = useRef(null);
  const mapObjRef = useRef(null);
  const markerRef = useRef(null);
  const circleRef = useRef(null);
  const siteLayerRef = useRef(null);
  const lowCoverageLayerRef = useRef(null);
  const autoGenerateRef = useRef(false);
  const sharedLinkReadRef = useRef(false);

  useEffect(() => { getJSON("/api/config").then(setConfig); }, []);

  useEffect(() => {
    getJSON("/api/strings?lang=" + lang).then(setStrings);
    localStorage.setItem("bx_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const pick = useCallback((lat, lon, label = null) => setPicked({ lat, lon, label }), []);

  const selectSite = useCallback((site) => {
    pick(site.lat, site.lon, site.name);
    const map = mapObjRef.current;
    if (map) map.flyTo([site.lat, site.lon], Math.max(map.getZoom(), 14), { duration: 0.6 });
  }, [pick]);

  // init leaflet map once config/strings are loaded and #map has mounted
  useEffect(() => {
    if (!config || !strings || mapObjRef.current || !mapRef.current) return;
    const b = config.bounds;
    const bounds = L.latLngBounds([b.south, b.west], [b.north, b.east]);
    const map = L.map(mapRef.current, { maxBounds: bounds, maxBoundsViscosity: 1.0, minZoom: 9 }).fitBounds(bounds);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors", maxZoom: 18,
    }).addTo(map);
    map.on("click", e => pick(e.latlng.lat, e.latlng.lng));
    siteLayerRef.current = L.layerGroup().addTo(map);
    lowCoverageLayerRef.current = L.layerGroup();
    mapObjRef.current = map;
  }, [config, strings, pick]);

  // parse a shared link's ?lat=&lon=&radius=&fill_gaps= once the map is ready,
  // apply the settings and flag the location for auto-generation below.
  useEffect(() => {
    if (!config || !strings || !mapObjRef.current || sharedLinkReadRef.current) return;
    sharedLinkReadRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const latStr = params.get("lat");
    const lonStr = params.get("lon");
    if (latStr === null || lonStr === null) return;
    const lat = Number(latStr);
    const lon = Number(lonStr);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    const radiusStr = params.get("radius");
    if (radiusStr !== null) {
      const radiusParam = Number(radiusStr);
      if (Number.isFinite(radiusParam)) setRadius(Math.min(300, Math.max(20, Math.round(radiusParam / 10) * 10)));
    }

    const fillGapsParam = params.get("fill_gaps");
    if (fillGapsParam !== null) setFillGaps(fillGapsParam === "1");

    mapObjRef.current.setView([lat, lon], Math.max(mapObjRef.current.getZoom(), 14));
    pick(lat, lon);
    autoGenerateRef.current = true;
  }, [config, strings, pick]);

  // (re)draw dive-site markers
  useEffect(() => {
    if (!config || !strings || !mapObjRef.current) return;
    const map = mapObjRef.current;
    siteLayerRef.current.clearLayers();
    lowCoverageLayerRef.current.clearLayers();
    if (showLowCoverage) lowCoverageLayerRef.current.addTo(map);
    else map.removeLayer(lowCoverageLayerRef.current);

    for (const site of config.sites) {
      const hasCoverage = site.coverage_pct !== null && site.coverage_pct !== undefined;
      const isLow = !hasCoverage || site.coverage_pct < config.lowCoverageThreshold;
      const color = coverageColor(site.coverage_pct);
      const tooltipText = hasCoverage
        ? `${site.name} (${site.coverage_pct.toFixed(0)}% ${strings.coverage_word})`
        : site.name;
      const tooltipEl = document.createElement("span");
      tooltipEl.textContent = tooltipText;
      const marker = L.circleMarker([site.lat, site.lon], {
        radius: 6, color, fillColor: color, fillOpacity: 0.9, weight: 2,
      })
        .bindTooltip(tooltipEl)
        .on("click", (e) => { L.DomEvent.stopPropagation(e); selectSite(site); });
      marker.addTo(isLow ? lowCoverageLayerRef.current : siteLayerRef.current);
    }
  }, [config, strings, showLowCoverage, selectSite]);

  // marker + radius circle for the picked point
  useEffect(() => {
    const map = mapObjRef.current;
    if (!map || !picked) return;
    if (markerRef.current) map.removeLayer(markerRef.current);
    markerRef.current = L.marker([picked.lat, picked.lon]).addTo(map);
    if (circleRef.current) map.removeLayer(circleRef.current);
    circleRef.current = L.circle([picked.lat, picked.lon], {
      radius, color: "#22d3ee", fill: false, dashArray: "4 4", weight: 2,
    }).addTo(map);
  }, [picked]);

  useEffect(() => {
    if (circleRef.current) circleRef.current.setRadius(radius);
  }, [radius]);

  // fires once, after the shared-link effect above has applied lat/lon/radius/fill_gaps
  useEffect(() => {
    if (!autoGenerateRef.current || !picked) return;
    autoGenerateRef.current = false;
    generate();
  }, [picked]);

  async function generate() {
    if (!picked) return;

    let currentStages = planStages(fillGaps, strings);
    setStages(currentStages);
    setStatus("loading");
    setError("");
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: picked.lat, lon: picked.lon, radius,
          fill_gaps: fillGaps,
        }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finished = false;

      while (!finished) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          const evt = JSON.parse(line);
          if (evt.type === "progress") {
            currentStages = evt.stage === "cache_hit"
              ? [{ key: "cache_hit", label: strings.progress_cache_hit, status: "active", detail: null }]
              : applyProgressEvent(currentStages, evt, strings);
            setStages(currentStages);
          } else if (evt.type === "result") {
            setStages(currentStages.map(s => ({ ...s, status: "done" })));
            setResult({ ...evt, center: { lat: picked.lat, lon: picked.lon } });
            setStatus("done");
            setActiveTab("3d");
            finished = true;

            const params = new URLSearchParams();
            params.set("lat", picked.lat.toFixed(6));
            params.set("lon", picked.lon.toFixed(6));
            params.set("radius", String(radius));
            params.set("fill_gaps", fillGaps ? "1" : "0");
            window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
          } else if (evt.type === "error") {
            setError(evt.message);
            setStatus("error");
            finished = true;
          }
        }
      }
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }

  if (!config || !strings) {
    return html`<div class="boot"><div class="spinner"></div></div>`;
  }

  return html`
    <div class="shell">
      <${Header} lang=${lang} setLang=${setLang} langNames=${config.langNames} langs=${config.langs} t=${strings} />
      <main class="layout">
        <aside class="sidebar">
          <${MapCard}
            mapRef=${mapRef} picked=${picked} t=${strings}
            showLowCoverage=${showLowCoverage} setShowLowCoverage=${setShowLowCoverage}
            sites=${config.sites} onSelectSite=${selectSite}
          />
          <${ControlsCard}
            t=${strings} radius=${radius} setRadius=${setRadius}
            fillGaps=${fillGaps} setFillGaps=${setFillGaps}
            picked=${picked} status=${status} onGenerate=${generate}
          />
        </aside>
        <section class="results">
          <${ResultsPanel} t=${strings} status=${status} error=${error} result=${result}
            activeTab=${activeTab} setActiveTab=${setActiveTab} stages=${stages} />
        </section>
      </main>
    </div>
  `;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
