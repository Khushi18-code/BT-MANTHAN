"""
Ensemble Optimal Interpolation.

Updates a background (raw) model state using matched observations and
covariance information.

IMPORTANT: EnOI does not automatically prove improvement. Every claim
that assimilation improves accuracy must rest on measured validation
results, reported with the metric, the sample and the period.
"""

import numpy as np
from typing import Dict, Any, List, Optional


def innovation(observation_value: float, model_value: float) -> float:
    """
    Innovation = Observation - Model.

    Note the sign: this matches the declared convention in comparison.py,
    where the *difference* is reported as Model - Observation. Keep these
    two consistent or the update will move the state the wrong way.
    """
    return float(observation_value - model_value)


def enoi_update(
    background: np.ndarray,
    innovations: np.ndarray,
    ensemble_anomalies: np.ndarray,
) -> np.ndarray:
    """
    Single EnOI analysis step.

    background          : model state vector, shape (n_state,)
    innovations         : observation minus model at obs locations, (n_obs,)
    ensemble_anomalies  : ensemble perturbations, (n_state, n_ens)

    Returns the analysed (assimilated) state, same shape as background.
    """
    n_state = background.size
    n_ens = ensemble_anomalies.shape[1]

    if n_ens < 2:
        raise ValueError("ensemble needs at least 2 members for covariance")

    # Background error covariance from the ensemble (B = A A^T / (N-1))
    # Computed implicitly — never materialize a (n_state, n_state) matrix.
    B_obs = ensemble_anomalies.T @ ensemble_anomalies / (n_ens - 1)
    B_obs += np.eye(B_obs.shape[0]) * 1e-8  # numerical guard

    # Observation error covariance, diagonal
    R = np.eye(innovations.size) * (0.5 ** 2)

    # Kalman gain, solved rather than inverted
    K = np.linalg.solve(B_obs + R, ensemble_anomalies.T).T  # (n_state, n_obs)

    analysis = background + K @ innovations
    return analysis


def validate(
    raw_values: List[float],
    assimilated_values: List[float],
    observed_values: List[float],
) -> Dict[str, Any]:
    """
    Compare raw and assimilated states against observations.

    This function produces the evidence. If RMSE does not fall, the correct
    statement is 'no improvement was measured for this sample' — not
    'EnOI improves accuracy'.
    """
    raw = np.asarray(raw_values, dtype=float)
    assim = np.asarray(assimilated_values, dtype=float)
    obs = np.asarray(observed_values, dtype=float)

    raw_diff = raw - obs
    assim_diff = assim - obs

    def _rmse(x):
        return float(np.sqrt(np.mean(x ** 2)))

    def _mae(x):
        return float(np.mean(np.abs(x)))

    raw_rmse, assim_rmse = _rmse(raw_diff), _rmse(assim_diff)

    return {
        "n_pairs": int(obs.size),
        "raw": {"rmse": raw_rmse, "mae": _mae(raw_diff), "bias": float(np.mean(raw_diff))},
        "assimilated": {
            "rmse": assim_rmse, "mae": _mae(assim_diff), "bias": float(np.mean(assim_diff))
        },
        "rmse_change": round(assim_rmse - raw_rmse, 4),
        "rmse_change_pct": (
            round((assim_rmse - raw_rmse) / raw_rmse * 100.0, 2) if raw_rmse else None
        ),
        "improved": bool(assim_rmse < raw_rmse),
        "caveat": (
            "Reported for this sample only. Improvement is not generalisable "
            "without a larger validation set and a stated period."
        ),
    }
