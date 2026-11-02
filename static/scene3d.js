import htm from 'https://unpkg.com/htm@3.1.1/dist/htm.module.js';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const html = htm.bind(React.createElement);
const { useEffect, useRef } = React;

function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

// Elevations (m NAP) where the water and land colour ramps flatten out.
const SHALLOW_BREAK = -1;
const ABOVE_BREAK = 1;

// Colour for one vertex, written into `target`
function shadeElevation(target, elev, isLand, zMin, zMax, deepColor, shallowColor, sandColor, aboveColor) {
  if (isLand) {
    if (elev <= ABOVE_BREAK) {
      target.copy(sandColor);
    } else {
      const hi = Math.max(zMax, ABOVE_BREAK + 0.1);
      target.lerpColors(sandColor, aboveColor, clamp01((elev - ABOVE_BREAK) / (hi - ABOVE_BREAK)));
    }
  } else {
    if (elev >= SHALLOW_BREAK) {
      target.copy(shallowColor);
    } else {
      const lo = Math.min(zMin, SHALLOW_BREAK - 0.1);
      target.lerpColors(deepColor, shallowColor, clamp01((elev - lo) / (SHALLOW_BREAK - lo)));
    }
  }
}

// Contour lines every grid_step metres (major every second one), traced
// across the same triangles as the surface. Returns flat [x,y,z, x,y,z, ...]
// segment arrays for LineSegmentsGeometry, plus one depth label per level.
function buildContourSegments(positions, indices, zMin, zMax, gridStart, gridStep, landFlags) {
  const eps = 0.05; // nudge above the surface (pre vertical-exaggeration) to dodge z-fighting
  const period = gridStep * 2;
  const levels = [];
  for (let v = gridStart; v <= zMax + 1e-6; v += period) {
    if (v >= zMin - 1e-6) levels.push({ value: v, major: true });
  }
  for (let v = gridStart + gridStep; v <= zMax + 1e-6; v += period) {
    if (v >= zMin - 1e-6) levels.push({ value: v, major: false });
  }

  const minor = [];
  const major = [];
  const pts = [];
  const levelPts = new Map(levels.map((lvl) => [lvl.value, []]));

  function addCrossing(da, db, xa, za, xb, zb) {
    if (pts.length >= 4) return; // each point uses 2 slots -- stop only once both crossings are found
    if ((da > 0 && db > 0) || (da < 0 && db < 0) || da === db) return;
    const frac = da / (da - db);
    pts.push(xa + (xb - xa) * frac, za + (zb - za) * frac);
  }

  for (let i = 0; i < indices.length; i += 3) {
    const va = indices[i], vb = indices[i + 1], vc = indices[i + 2];
    const ia = va * 3, ib = vb * 3, ic = vc * 3;
    const x0 = positions[ia], e0 = positions[ia + 1], z0 = positions[ia + 2];
    const x1 = positions[ib], e1 = positions[ib + 1], z1 = positions[ib + 2];
    const x2 = positions[ic], e2 = positions[ic + 1], z2 = positions[ic + 2];
    const triMin = Math.min(e0, e1, e2), triMax = Math.max(e0, e1, e2);
    // Only water triangles get a label anchor -- above-water contour rings
    // are still drawn as lines but a "depth" figure means nothing on dry
    // land, see shadeElevation() for why isLand (not elevation sign) is the
    // water/land split.
    const isWaterTri = landFlags && !landFlags[va] && !landFlags[vb] && !landFlags[vc];

    for (const level of levels) {
      if (level.value < triMin || level.value > triMax) continue;
      pts.length = 0;
      addCrossing(e0 - level.value, e1 - level.value, x0, z0, x1, z1);
      addCrossing(e1 - level.value, e2 - level.value, x1, z1, x2, z2);
      addCrossing(e2 - level.value, e0 - level.value, x2, z2, x0, z0);
      if (pts.length === 4) {
        const out = level.major ? major : minor;
        const y = level.value + eps;
        out.push(pts[0], y, pts[1], pts[2], y, pts[3]);
        if (isWaterTri) {
          const lp = levelPts.get(level.value);
          lp.push(pts[0], pts[1]);
          lp.push(pts[2], pts[3]);
        }
      }
    }
  }

  const labels = [];
  for (const level of levels) {
    const lp = levelPts.get(level.value);
    if (lp.length === 0) continue;
    let cx = 0, cz = 0, n = 0;
    for (let i = 0; i < lp.length; i += 2) { cx += lp[i]; cz += lp[i + 1]; n++; }
    cx /= n; cz /= n;
    let bestI = 0, bestD = Infinity;
    for (let i = 0; i < lp.length; i += 2) {
      const dx = lp[i] - cx, dz = lp[i + 1] - cz;
      const d = dx * dx + dz * dz;
      if (d < bestD) { bestD = d; bestI = i; }
    }
    labels.push({ x: lp[bestI], y: level.value + eps, z: lp[bestI + 1], value: level.value, major: level.major });
  }

  return { minor: new Float32Array(minor), major: new Float32Array(major), labels };
}

export function Scene3D({ scene, t }) {
  const containerRef = useRef(null);
  const readoutRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !scene) return;

    const { xs, ys, elevation, is_land, z_min, z_max, grid_step, grid_start, vertical_exaggeration, colors } = scene;
    const rows = ys.length, cols = xs.length;

    const positions = new Float32Array(rows * cols * 3);
    const present = new Uint8Array(rows * cols);
    const colorArr = new Float32Array(rows * cols * 3);
    const landFlags = new Uint8Array(rows * cols);

    const deepColor = new THREE.Color(colors.deep);
    const shallowColor = new THREE.Color(colors.shallow);
    const sandColor = new THREE.Color(colors.sand);
    const aboveColor = new THREE.Color(colors.above);
    const cellColor = new THREE.Color();

    let p = 0;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        const raw = elevation[r][c];
        const has = raw !== null;
        present[i] = has ? 1 : 0;
        const elev = has ? raw : 0;
        positions[p++] = xs[c];
        positions[p++] = elev;
        positions[p++] = -ys[r]; // flip so "north" (larger y) reads as "away from camera"

        // Very old cache entries have no is_land; guess from elevation.
        const land = is_land ? !!is_land[r][c] : elev >= 0;
        landFlags[i] = land ? 1 : 0;
        shadeElevation(cellColor, elev, land, z_min, z_max, deepColor, shallowColor, sandColor, aboveColor);
        colorArr[i * 3] = cellColor.r;
        colorArr[i * 3 + 1] = cellColor.g;
        colorArr[i * 3 + 2] = cellColor.b;
      }
    }

    const indices = [];
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const v00 = r * cols + c, v01 = r * cols + c + 1;
        const v10 = (r + 1) * cols + c, v11 = (r + 1) * cols + c + 1;
        if (!present[v00] || !present[v01] || !present[v10] || !present[v11]) continue;
        indices.push(v00, v10, v11, v00, v11, v01);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colorArr, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
      vertexColors: true, side: THREE.DoubleSide, roughness: 0.95, metalness: 0.02,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.scale.y = vertical_exaggeration;

    const width = container.clientWidth, height = container.clientHeight;

    // Contour lines and labels are children of `mesh`, so they share its
    // vertical exaggeration.
    const segments = buildContourSegments(positions, indices, z_min, z_max, grid_start, grid_step, landFlags);
    const contourLines = [];
    for (const [seg, linewidth, opacity] of [[segments.minor, 1.1, 0.45], [segments.major, 2.2, 0.85]]) {
      if (seg.length === 0) continue;
      const lineGeom = new LineSegmentsGeometry();
      lineGeom.setPositions(seg);
      const lineMat = new LineMaterial({
        color: 0xffffff, linewidth, transparent: true, opacity, depthTest: true,
      });
      lineMat.resolution.set(width, height);
      const line = new LineSegments2(lineGeom, lineMat);
      mesh.add(line);
      contourLines.push(line);
    }

    const contourLabels = [];
    for (const lbl of segments.labels) {
      const el = document.createElement("div");
      el.className = "contour-label" + (lbl.major ? "" : " minor");
      el.textContent = `${Math.abs(Math.round(lbl.value))}m`;
      const obj = new CSS2DObject(el);
      obj.position.set(lbl.x, lbl.y, lbl.z);
      mesh.add(obj);
      contourLabels.push(obj);
    }

    const scene3js = new THREE.Scene();
    scene3js.background = new THREE.Color(0x04070d);
    scene3js.add(mesh);
    scene3js.add(new THREE.AmbientLight(0xffffff, 0.65));
    const sun = new THREE.DirectionalLight(0xffffff, 0.9);
    sun.position.set(1, 1.4, 0.6);
    scene3js.add(sun);
    const fillLight = new THREE.DirectionalLight(0xaad4ff, 0.35);
    fillLight.position.set(-1, 0.6, -0.8);
    scene3js.add(fillLight);

    const xRange = Math.abs(xs[xs.length - 1] - xs[0]);
    const yRange = Math.abs(ys[ys.length - 1] - ys[0]);
    const horiz = Math.max(xRange, yRange, 1);

    // "N" label above the north edge (ys[0]; y is flipped to -z).
    const nEl = document.createElement("div");
    nEl.className = "north-label";
    nEl.textContent = "N";
    const nLabel = new CSS2DObject(nEl);
    nLabel.position.set((xs[0] + xs[cols - 1]) / 2, z_max * vertical_exaggeration + 2, -ys[0]);
    scene3js.add(nLabel);

    const camera = new THREE.PerspectiveCamera(45, width / (height || 1), 0.1, horiz * 50);
    camera.position.set(horiz * 0.75, horiz * 0.65, horiz * 0.9);

    const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(width, height);
    Object.assign(labelRenderer.domElement.style, { position: "absolute", top: "0", left: "0", pointerEvents: "none" });
    container.appendChild(labelRenderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = horiz * 0.05;
    controls.maxDistance = horiz * 4;
    controls.update();

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function onPointerMove(e) {
      const rect = container.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObject(mesh, false)[0];
      if (hit && readoutRef.current) {
        const pt = hit.point;
        readoutRef.current.textContent =
          `X ${pt.x.toFixed(1)}  Y ${(-pt.z).toFixed(1)}  Z ${(pt.y / vertical_exaggeration).toFixed(2)} m NAP`;
        readoutRef.current.style.display = "block";
      } else if (readoutRef.current) {
        readoutRef.current.style.display = "none";
      }
    }
    function onPointerLeave() {
      if (readoutRef.current) readoutRef.current.style.display = "none";
    }
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerleave", onPointerLeave);

    let frameId;
    function animate() {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene3js, camera);
      labelRenderer.render(scene3js, camera);
    }
    animate();

    function onResize() {
      const w = container.clientWidth, h = container.clientHeight;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      labelRenderer.setSize(w, h);
      for (const line of contourLines) line.material.resolution.set(w, h);
    }
    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerleave", onPointerLeave);
      controls.dispose();
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      for (const line of contourLines) {
        line.geometry.dispose();
        line.material.dispose();
      }
      for (const obj of contourLabels) obj.element.remove();
      nEl.remove();
      if (renderer.domElement.parentNode === container) container.removeChild(renderer.domElement);
      if (labelRenderer.domElement.parentNode === container) container.removeChild(labelRenderer.domElement);
    };
  }, [scene]);

  return html`
    <div class="scene3d" ref=${containerRef}>
      <div class="scene3d-readout mono" ref=${readoutRef} style=${{ display: "none" }}></div>
      <div class="scene3d-hint">drag to rotate · pinch to zoom</div>
    </div>
  `;
}
