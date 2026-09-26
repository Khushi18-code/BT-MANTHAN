"""
Common internal representation for model and observation data.

Every record from every source — HYCOM, Copernicus Marine, Argo —
is normalized into one of these two shapes before it reaches any
other part of the system. This is what makes new instruments
extensions rather than rewrites.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Provenance:
    """Where a value came from and what happened to it."""
    source: str                      # "HYCOM", "Copernicus Marine", "Argo GDAC"
    dataset: Optional[str] = None    # dataset or product identifier
    platform: Optional[str] = None   # e.g. "APEX float", model run id
    provider: Optional[str] = None   # INCOIS, Copernicus, Ifremer
    retrieval_time: Optional[str] = None
    processing: List[str] = field(default_factory=list)  # ["vertical_interpolation"]

    def add_processing(self, step: str) -> None:
        self.processing.append(step)


@dataclass
class Quality:
    """Rule-based quality status. Never an arbitrary percentage."""
    status: str = "pass"             # "pass" | "flagged" | "reject"
    flags: List[str] = field(default_factory=list)
    source_qc: Optional[str] = None  # provider's own QC flag, propagated

    def flag(self, reason: str) -> None:
        self.flags.append(reason)
        if self.status == "pass":
            self.status = "flagged"

    def reject(self, reason: str) -> None:
        self.flags.append(reason)
        self.status = "reject"


@dataclass
class ModelRecord:
    """A model-derived value at a location, depth and time."""
    variable: str                    # canonical: "temperature"
    unit: str                        # canonical: "degrees_Celsius"
    timestamp: str                   # ISO 8601 UTC
    depth: float                     # metres, positive down
    latitude: float
    longitude: float
    value: float
    source_levels: List[float] = field(default_factory=list)
    method: str = "grid_point"       # "grid_point" | "vertical_interpolation" | "horizontal_interpolation"
    provenance: Provenance = None
    quality: Quality = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class ObservationRecord:
    """An instrument measurement along a platform track."""
    variable: str
    unit: str
    timestamp: str
    depth: float
    latitude: float
    longitude: float
    value: float
    platform: Optional[str] = None   # instrument class
    platform_id: Optional[str] = None  # WMO id for Argo
    provenance: Provenance = None
    quality: Quality = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


CANONICAL_UNITS = {
    "temperature": "degrees_Celsius",
    "salinity": "psu",
    "chlorophyll": "mg_m3",
    "oxygen": "micromol_kg",
    "u_current": "m_s-1",
    "v_current": "m_s-1",
}

# Physically plausible ranges — used by DQI, not to judge accuracy.
PLAUSIBLE_RANGES = {
    "degrees_Celsius": (-2.0, 40.0),
    "psu": (0.0, 42.0),
    "mg_m3": (0.0, 100.0),
    "micromol_kg": (0.0, 500.0),
    "m_s-1": (-5.0, 5.0),
}
