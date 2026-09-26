"""
NetCDF ingestion via xarray.

Opens a NetCDF dataset, identifies dimensions and variables, subsets by
region/depth/time, normalizes into the common schema, and runs quality
checks. Never loads a full dataset into memory.
"""

import numpy as np
import xarray as xr
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from schema import (
    ModelRecord, Provenance, Quality,
    CANONICAL_UNITS, PLAUSIBLE_RANGES,
)

# Maps source variable names onto canonical names across HYCOM / Copernicus.
VARIABLE_ALIASES = {
    "water_temp": "temperature", "temp": "temperature", "thetao": "temperature",
    "TEMP": "temperature",
    "salinity": "salinity", "sal": "salinity", "so": "salinity", "SALINITY": "salinity",
    "chl": "chlorophyll", "CHL": "chlorophyll",
    "uo": "u_current", "water_u": "u_current",
    "vo": "v_current", "water_v": "v_current",
}

DEPTH_ALIASES = ["depth", "deptht", "lev", "level", "z"]
LAT_ALIASES = ["lat", "latitude", "nav_lat"]
LON_ALIASES = ["lon", "longitude", "nav_lon"]


def _find_coord(ds: xr.Dataset, candidates: List[str]) -> Optional[str]:
    """Return the first coordinate name present in the dataset."""
    for name in candidates:
        if name in ds.coords or name in ds.variables:
            return name
    return None


def open_dataset(path: str) -> xr.Dataset:
    """Open lazily — no data is read until a slice is requested."""
    return xr.open_dataset(path, chunks={})


def identify_variables(ds: xr.Dataset) -> Dict[str, str]:
    """Map canonical variable names present in this dataset to source names."""
    found = {}
    for source_name in ds.data_vars:
        canonical = VARIABLE_ALIASES.get(source_name, VARIABLE_ALIASES.get(source_name.lower()))
        if canonical:
            found[canonical] = source_name
    return found


def run_quality_checks(record: ModelRecord) -> Quality:
    """
    Structural checks only. A QC failure never implies the value is wrong —
    only that the record is not usable for comparison.
    """
    q = Quality()

    if record.latitude is None or record.longitude is None:
        q.reject("missing_coordinates")
    elif not (-90 <= record.latitude <= 90) or not (-180 <= record.longitude <= 180):
        q.reject("invalid_coordinates")

    if record.timestamp is None:
        q.reject("missing_timestamp")
    else:
        try:
            datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
        except ValueError:
            q.reject("unparseable_timestamp")

    if record.depth is None or record.depth < 0:
        q.reject("invalid_depth")

    if record.value is None or np.isnan(record.value):
        q.reject("missing_value")

    rng = PLAUSIBLE_RANGES.get(record.unit)
    if rng and record.value is not None and not np.isnan(record.value):
        lo, hi = rng
        if not (lo <= record.value <= hi):
            q.flag(f"outside_plausible_range:{record.value}")

    return q


def subset_field(
    path: str,
    variable: str,
    bbox: Dict[str, float],
    depth: float,
    time_range: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Extract a web-ready slice. This is the function the API calls.

    bbox = {"min_lat":, "max_lat":, "min_lon":, "max_lon":}
    Returns JSON-serializable dict, never an xarray object.
    """
    ds = open_dataset(path)
    available = identify_variables(ds)

    if variable not in available:
        raise ValueError(f"variable '{variable}' not present in dataset")

    source_var = available[variable]
    lat_name = _find_coord(ds, LAT_ALIASES)
    lon_name = _find_coord(ds, LON_ALIASES)
    depth_name = _find_coord(ds, DEPTH_ALIASES)

    da = ds[source_var]

    # Spatial subset
    da = da.sel({
        lat_name: slice(bbox["min_lat"], bbox["max_lat"]),
        lon_name: slice(bbox["min_lon"], bbox["max_lon"]),
    })

    # Vertical: exact level if available, otherwise interpolate
    method = "grid_point"
    source_levels = [float(depth)]
    if depth_name and depth_name in da.dims:
        levels = np.asarray(ds[depth_name].values, dtype=float)
        if np.any(np.isclose(levels, depth)):
            da = da.sel({depth_name: float(levels[np.argmin(np.abs(levels - depth))])})
        else:
            da = da.interp({depth_name: depth})
            method = "vertical_interpolation"
        source_levels = levels.tolist()

    # Temporal
    time_name = "time" if "time" in da.dims else None
    if time_name and time_range:
        da = da.sel({time_name: slice(time_range["start"], time_range["end"])})

    da = da.load()  # materialize only the subset

    lats = np.asarray(ds[lat_name].values, dtype=float).tolist()
    lons = np.asarray(ds[lon_name].values, dtype=float).tolist()

    prov = Provenance(
        source="HYCOM" if "hycom" in path.lower() else "Copernicus Marine",
        dataset=path,
        retrieval_time=datetime.now(timezone.utc).isoformat(),
    )
    if method != "grid_point":
        prov.add_processing(method)

    return {
        "variable": variable,
        "unit": CANONICAL_UNITS.get(variable, "unknown"),
        "depth": depth,
        "method": method,
        "latitude": lats,
        "longitude": lons,
        "values": np.nan_to_num(da.values, nan=-999.0).tolist(),
        "timestamps": (
            [str(t) for t in np.asarray(ds[time_name].values).astype("datetime64[s]").tolist()]
            if time_name else []
        ),
        "source_levels": source_levels,
        "provenance": prov.__dict__,
    }
