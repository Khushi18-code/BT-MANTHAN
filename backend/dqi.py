"""
Data Quality Index.

Answers one question: is this record structurally and plausibly usable?
Not an accuracy score. Not an uncertainty estimate.

Status levels: pass | flagged | reject
If a numeric index is added later, its weights must be published here.
"""

from typing import List, Dict, Any
from schema import ModelRecord, ObservationRecord, Quality, PLAUSIBLE_RANGES


def check_observation(record: ObservationRecord) -> Quality:
    q = Quality()
    if record.latitude is None or record.longitude is None:
        q.reject("missing_coordinates")
    if record.timestamp is None:
        q.reject("missing_timestamp")
    if record.depth is None or record.depth < 0:
        q.reject("invalid_depth")
    if record.value is None:
        q.reject("missing_value")
    if record.source_qc is not None:
        q.source_qc = str(record.source_qc)
        if str(record.source_qc) not in ("1", "A", "Good"):
            q.flag(f"source_qc={record.source_qc}")
    return q


def deduplicate(records: List[ObservationRecord]) -> tuple:
    """Detect repeated platform + timestamp + depth triples."""
    seen, unique = set(), []
    duplicates = 0
    for r in records:
        key = (r.platform_id, r.timestamp, round(r.depth, 2))
        if key in seen:
            duplicates += 1
            if r.quality is None:
                r.quality = Quality()
            r.quality.flag("duplicate_record")
            continue
        seen.add(key)
        unique.append(r)
    return unique, duplicates


def summarise(records: List[ObservationRecord]) -> Dict[str, Any]:
    """Aggregate quality across a batch for the UI panel."""
    counts = {"pass": 0, "flagged": 0, "reject": 0}
    all_flags: Dict[str, int] = {}
    for r in records:
        status = r.quality.status if r.quality else "pass"
        counts[status] = counts.get(status, 0) + 1
        for f in (r.quality.flags if r.quality else []):
            all_flags[f] = all_flags.get(f, 0) + 1
    return {
        "total": len(records),
        "counts": counts,
        "flags": all_flags,
        # Deliberately no single combined percentage.
    }
