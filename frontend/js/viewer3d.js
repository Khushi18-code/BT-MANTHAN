/**
 * Browser-native 3D ocean field renderer.
 *
 * Renders the water column as stacked depth bands, places observation
 * markers in true geographic position, and holds the View A / View B
 * state for raw vs assimilated comparison.
 */

import * as THREE from "[cdn.jsdelivr.net](https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js)";
import { OrbitControls } from "[cdn.jsdelivr.net](https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js)";

export class OceanViewer {
  constructor(container) {
    this.container = container;
    this.state = {
      verticalExaggeration: 1,
      opacity: 1.0,
      view: "raw",          // "raw" | "assimilated"
      showCurrents: true,
      showDepthGrid: true,
    };
    this._init();
  }

  _init() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x060b18);

    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 5000);
    this.camera.position.set(120, 80, 160);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(50, 100, 50);
    this.scene.add(key);

    this.fieldGroup = new THREE.Group();
    this.markerGroup = new THREE.Group();
    this.scene.add(this.fieldGroup, this.markerGroup);

    window.addEventListener("resize", () => this._resize());
    this._animate();
  }

  /** Build depth bands from a model field subset. */
  renderField(field) {
    this.fieldGroup.clear();

    const { latitude, longitude, values, unit } = field;
    const nLat = latitude.length;
    const nLon = longitude.length;
    const nx = 200, nz = 200;
    const verticalScale = 60 * this.state.verticalExaggeration;

    const colours = this._temperatureScale(values, unit);

    for (let i = 0; i < nLat - 1; i++) {
      for (let j = 0; j < nLon - 1; j++) {
        const v = values[i]?.[j] ?? values[i * nLon + j];
        if (v === undefined || v <= -900) continue;

        const geo = new THREE.PlaneGeometry(nx / (nLon - 1), nz / (nLat - 1));
        const mat = new THREE.MeshBasicMaterial({
          color: colours(v),
          transparent: true,
          opacity: 0.85 * this.state.opacity,
          side: THREE.DoubleSide,
          depthWrite: false,
        });
        const mesh = new THREE.Mesh(geo, mat);

        const x = (j / (nLon - 1) - 0.5) * nx;
        const z = (i / (nLat - 1) - 0.5) * nz;
        const y = -field.depth * verticalScale / 200;
        mesh.position.set(x, y, z);
        mesh.rotation.x = -Math.PI / 2;
        this.fieldGroup.add(mesh);
      }
    }
  }

  /** Place float markers at their geographic position. */
  renderMarkers(floats) {
    this.markerGroup.clear();
    if (!floats?.length) return;

    const lats = floats.map((f) => f.latitude);
    const lons = floats.map((f) => f.longitude);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLon = Math.min(...lons), maxLon = Math.max(...lons);

    floats.forEach((f) => {
      const x = maxLon === minLon ? 0 : ((f.longitude - minLon) / (maxLon - minLon) - 0.5) * 200;
      const z = maxLat === minLat ? 0 : ((f.latitude - minLat) / (maxLat - minLat) - 0.5) * 200;

      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(1.2, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x22d3ee })
      );
      dot.position.set(x, 2, z);

      const ring = new THREE.Mesh(
        new THREE.RingGeometry(2.2, 2.8, 32),
        new THREE.MeshBasicMaterial({
          color: 0x22d3ee, side: THREE.DoubleSide, transparent: true, opacity: 0.7,
        })
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.copy(dot.position);

      dot.userData = { floatId: f.platform_id, record: f };
      ring.userData = dot.userData;

      this.markerGroup.add(dot, ring);
    });
  }

  /** View A (raw) / View B (assimilated) — recolour, do not re-fetch. */
  setView(view) {
    if (view !== "raw" && view !== "assimilated") return;
    this.state.view = view;
    if (this._lastField) this.renderField(this._lastField);
  }

  setVerticalExaggeration(value) {
    this.state.verticalExaggeration = value;
    if (this._lastField) this.renderField(this._lastField);
  }

  setOpacity(value) {
    this.state.opacity = value;
    if (this._lastField) this.renderField(this._lastField);
  }

  _temperatureScale(values, unit) {
    const flat = (Array.isArray(values[0]) ? values.flat() : values)
      .filter((v) => v !== null && v !== undefined && v > -900);
    const lo = flat.length ? Math.min(...flat) : 0;
    const hi = flat.length ? Math.max(...flat) : 30;

    return (value) => {
      const t = hi === lo ? 0.5 : (value - lo) / (hi - lo);
      const c = new THREE.Color();
      c.setHSL(0.62 - t * 0.62, 0.85, 0.35 + t * 0.25);  // deep blue → warm red
      return c;
    };
  }

  _resize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
