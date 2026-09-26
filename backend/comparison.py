"""
Model–observation matching and comparison.

A comparison is only produced when every eligibility check passes.
Every returned comparison carries its matching metadata, because a
difference without context is a number, not evidence.

Sign convention: Model − Observation, declared in the output.
"""

import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime

from schema import ModelRecord, ObservationRecord, Provenance

SIGN_CONVENTION = "Model - Observation"
MAX_TIME_TOLERANCE_HOURS = 24.0
MAX_SPATIAL_DISTANCE_KM = 50.0


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arcsin(np.sqrt(a)))


def check_compatibility(
    obs: ObservationRecord, model: ModelRecord
) -> Dict[str, Any]:
    """Eligibility checks. Returns {eligible: bool, reasons: [...]}."""
    reasons = []

    if obs.quality and obs.quality.status == "reject":
        reasons.append("observation_failed_quality_check")

    if obs.variable != model.variable:
        reasons.append(f"variable_mismatch:{obs.variable}!={model.variable}")

    if obs.unit != model.unit:
        reasons.append(f"unit_mismatch:{obs.unit}!={model.unit}")

    dt = abs(
        datetime.fromisoformat(obs.timestamp.replace("Z", "+00:00"))
        - datetime.fromisoformat(model.timestamp.replace("Z", "+00:00"))
    ).total_seconds() / 3600.0
    if dt > MAX_TIME_TOLERANCE_HOURS:
        reasons.append(f"time_offset_exceeds_tolerance:{dt:.1f}h")

    dist = haversine_km(obs.latitude, obs.longitude, model.latitude, model.longitude)
    if dist > MAX_SPATIAL_DISTANCE_KM:
        reasons.append(f"spatial_distance_exceeds_tolerance:{dist:.1f}km")

    if abs(obs.depth - model.depth) > 1.0:
        reasons.append(f"depth_mismatch:{abs(obs.depth - model.depth):.1f}m")

    return {"eligible": len(reasons) == 0, "reasons": reasons}


def vertical_interpolate(
    profile_depths: List[float], profile_values: List[float], target_depth: float
) -> Optional[float]:
    """
    Linear interpolation in the vertical, with an explicit indicator that
    interpolation occurred. Below the deepest sample, no extrapolation is
    attempted — the layer is simply unavailable.
    """
    pairs = sorted(zip(profile_depths, profile_values))
    d = [p[0] for p in pairs]
    v = [p[1] for p in pairs]

    if not d:
        return None
    if target_depth < d[0] or target_depth > d[-1]:
        return None
    if target_depth in d:
        return v[d.index(target_depth)]

    for i in range(1, len(d)):
        if d[i - 1] <= target_depth <= d[i]:
            frac = (target_depth - d[i - 1]) / (d[i] - d[i - 1])
            return float(v[i - 1] + frac * (v[i] - v[i - 1]))
    return None


def compare_pair(obs: ObservationRecord, model: ModelRecord) -> Dict[str, Any]:
    """Single matched pair, with all matching metadata attached."""
    eligibility = check_compatibility(obs, model)
    if not eligibility["eligible"]:
        return {"eligible": False, "reasons": eligibility["reasons"]}

    difference = model.value - obs.value
    return {
        "eligible": True,
        "sign_convention": SIGN_CONVENTION,
        "variable": obs.variable,
        "unit": obs.unit,
        "model_value": model.value,
        "observation_value": obs.value,
        "difference": difference,
        "matching_metadata": {
            "time_offset_hours": round(_hours_between(obs.timestamp, model.timestamp), 2),
            "spatial_distance_km": round(
                haversine_km(obs.latitude, obs.longitude, model.latitude, model.longitude), 2
            ),
            "requested_depth_m": model.depth,
            "source_levels_m": model.source_levels,
            "interpolation_method": model.method,
            "interpolated": model.method != "grid_point",
        },
        "quality": {
            "observation_status": obs.quality.status if obs.quality else "pass",
            "observation_flags": obs.quality.flags if obs.quality else [],
        },
        "provenance": {
            "model": model.provenance.__dict__ if model.provenance else None,
            "observation": obs.provenance.__dict__ if obs.provenance else None,
        },
    }


def _hours_between(t1: str, t2: str) -> float:
    a = datetime.fromisoformat(t1.replace("Z", "+00:00"))
    b = datetime.fromisoformat(t2.replace("Z", "+00:00"))
    return abs((b - a).total_seconds()) / 3600.0


def profile_statistics(differences: List[float]) -> Dict[str, float]:
    """Statistics across a matched set. Reported, never over-interpreted."""
    if not differences:
        return {}
    arr = np.asarray(differences, dtype=float)
    return {
        "bias": float(np.mean(arr)),
        "mae": float(np.mean(np.abs(arr))),
        "rmse": float(np.sqrt(np.mean(arr ** 2))),
        "n_pairs": int(arr.size),
    }
