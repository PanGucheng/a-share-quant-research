from __future__ import annotations

import pandas as pd

from research_validation.historical_data_authority import (
    assess_statement_completeness,
    canonical_instrument,
    resolve_lifecycle_evidence,
)


def test_canonical_instrument_exchange_first() -> None:
    assert canonical_instrument("600000.SH") == "SH600000"
    assert canonical_instrument("sz000001") == "SZ000001"


def test_lifecycle_snapshot_is_candidate_not_vintage_authority() -> None:
    basic = pd.DataFrame({"ts_code": ["600000.SH"], "list_date": ["19991110"], "delist_date": [None], "list_status": ["L"]})
    intervals = pd.DataFrame({"instrument": ["SH600000"], "start_date": ["1999-11-10"], "end_date": ["2024-01-01"]})
    detail, summary = resolve_lifecycle_evidence(basic, intervals)
    assert detail.loc[0, "authority_status"] == "candidate_interval_only"
    assert str(summary.loc[summary.metric.eq("historical_vintage_proven"), "value"].iloc[0]).lower() == "false"


def test_paginated_cap_is_not_failure_when_segment_terminates() -> None:
    receipts = pd.DataFrame(
        {
            "api": ["income", "income", "income"],
            "ts_code": ["600000.SH"] * 3,
            "retrieval_mode": ["paginated_broad"] * 3,
            "segment_id": ["broad_0", "broad_1", "broad_2"],
            "rows": [100, 100, 4],
            "row_cap_reached": [True, True, False],
            "page_terminal": [False, False, True],
        }
    )
    detail, summary = assess_statement_completeness(receipts)
    assert bool(detail.loc[0, "segmented_retrieval_complete"])
    assert int(summary.loc[0, "cap_issuer_count"]) == 0
