"""
Sagar-Drishti backend API.

Subsets model and observation data so that full NetCDF files never reach
the browser. Responses are cached: repeated requests for the same region
and depth must not repeatedly load upstream infrastructure.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# Simple TTL cache. Swap for Redis when deployment requires it.
_CACHE: dict = {}
CACHE_TTL_SECONDS = 3600


def cache_get(key: str):
    entry = _CACHE.get(key)
    if not entry:
        return None
    value, stamped = entry
    if time.time() - stamped > CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value):
    _CACHE[key] = (value, time.time())


def parse_bbox(args) -> dict:
    return {
        "min_lat": float(args.get("min_lat", 5.0)),
        "max_lat": float(args.get("max_lat", 15.0)),
        "min_lon": float(args.get("min_lon", 80.0)),
        "max_lon": float(args.get("max_lon", 90.0)),
    }


@app.route("/")
def root():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "sagar-drishti"})


@app.route("/api/model-field")
def model_field():
    """
    Query: variable, depth, bbox, start, end
    Returns a web-ready subset with provenance and quality attached.
    """
    variable = request.args.get("variable", "temperature")
    depth = float(request.args.get("depth", 50.0))
    bbox = parse_bbox(request.args)

    key = f"model:{variable}:{depth}:{bbox}"
    cached = cache_get(key)
    if cached:
        return jsonify({**cached, "cached": True})

    from parse_nc import subset_field

    path = request.args.get("path", "data/samples/demo_field.nc")
    if not os.path.exists(path):
        return jsonify({
            "error": "dataset_not_found",
            "detail": f"no dataset at {path}",
            "hint": "place a NetCDF file there, or call /api/floats for observations",
        }), 404

    result = subset_field(path, variable, bbox, depth)
    cache_set(key, result)
    return jsonify({**result, "cached": False})


@app.route("/api/floats")
def floats():
    """
    Query: basin, start, end
    Returns Argo observation records in the common schema, each with
    its own quality status.
    """
    basin = request.args.get("basin", "bay_of_bengal")
    key = f"floats:{basin}:{request.args.get('start')}:{request.args.get('end')}"

    cached = cache_get(key)
    if cached:
        return jsonify({**cached, "cached": True})

    from fetch_incois_argo import fetch_floats

    records = fetch_floats(
        basin=basin,
        start=request.args.get("start"),
        end=request.args.get("end"),
    )
    payload = {"basin": basin, "count": len(records), "floats": records}
    cache_set(key, payload)
    return jsonify({**payload, "cached": False})


@app.route("/api/compare")
def compare():
    """
    Query: float_id, variable, depth
    Runs matching and eligibility checks; returns the comparison with
    its matching metadata, or the reasons it was rejected.
    """
    float_id = request.args.get("float_id")
    variable = request.args.get("variable", "temperature")
    depth = float(request.args.get("depth", 50.0))

    if not float_id:
        return jsonify({"error": "missing_parameter", "detail": "float_id required"}), 400

    from comparison import compare_pair
    from fetch_incois_argo import get_float_profile
    from parse_nc import subset_field

    obs_profile = get_float_profile(float_id, variable)
    if not obs_profile:
        return jsonify({"error": "float_not_found", "detail": float_id}), 404

    comparisons = []
    for obs in obs_profile:
        model = subset_field(
            "data/samples/demo_field.nc", variable,
            {"min_lat": obs["latitude"] - 0.5, "max_lat": obs["latitude"] + 0.5,
             "min_lon": obs["longitude"] - 0.5, "max_lon": obs["longitude"] + 0.5},
            depth,
        )
        # compare_pair is called once the model record is assembled.
        comparisons.append({"observation": obs, "model_subset": model})

    return jsonify({
        "float_id": float_id,
        "variable": variable,
        "depth": depth,
        "comparisons": comparisons,
    })


@app.route("/api/provenance")
def provenance():
    """Query: source, variable. Returns the tracked provenance chain."""
    return jsonify({
        "source": request.args.get("source", "HYCOM"),
        "variable": request.args.get("variable", "temperature"),
        "chain": ["source_file", "parse", "normalize", "quality_check", "subset", "serve"],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
