"""Compatibility facade for the active Forward Pipeline.

Phase 3B moved implementation into focused modules while preserving the public
symbols and call signatures historically imported from this module.
"""

from __future__ import annotations

from .forward_binding import (
    CandidateBundle,
    _default_predictor,
    finalize_prediction_commit,
    load_candidate_bundle,
)
from .forward_labels import _daily_metrics, update_mature_forward_labels
from .forward_prediction import (
    _normalize_features,
    _normalize_raw,
    run_single_day_prediction,
)
from .forward_state import (
    EVIDENCE_GRADE,
    KEY_COLUMNS,
    LABEL_COLUMN,
    RAW_COLUMNS,
    _atomic_csv,
    _atomic_json,
    _read_json,
    _record_date,
    derive_label_window,
    initial_forward_state,
    load_forward_state,
    load_trading_calendar,
    record_forward_failure,
)


__all__ = [
    "CandidateBundle",
    "EVIDENCE_GRADE",
    "KEY_COLUMNS",
    "LABEL_COLUMN",
    "RAW_COLUMNS",
    "derive_label_window",
    "finalize_prediction_commit",
    "initial_forward_state",
    "load_candidate_bundle",
    "load_forward_state",
    "load_trading_calendar",
    "record_forward_failure",
    "run_single_day_prediction",
    "update_mature_forward_labels",
]
