/**
 * API client for the Sagar-Drishti backend.
 *
 * Every function maps one-to-one with a backend route, so swapping
 * demo data for live data is a source change, not a rewrite.
 */

const API_BASE = window.location.origin;

async function request(path, params = {}) {
  const url = new URL(path, API_BASE);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.append(k, v);
  });

  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchModelField({ variable, depth, bbox, start, end }) {
  return request("/api/model-field", {
    variable, depth,
    min_lat: bbox.minLat, max_lat: bbox.maxLat,
    min_lon: bbox.minLon, max_lon: bbox.maxLon,
    start, end,
  });
}

export async function fetchFloats({ basin, start, end }) {
  return request("/api/floats", { basin, start, end });
}

export async function fetchComparison({ floatId, variable, depth }) {
  return request("/api/compare", { float_id: floatId, variable, depth });
}

export async function fetchProvenance({ source, variable }) {
  return request("/api/provenance", { source, variable });
}

export async function health() {
  return request("/api/health");
}
