from __future__ import annotations

import hashlib

import pandas as pd

from research_validation.bootstrap import (
    gap_aware_moving_block_mean_test,
    moving_block_mean_test,
)
from research_validation.multiple_testing import apply_fdr


def factor_seed(base_seed: int, outer_split_id: str, factor: str) -> int:
    digest = hashlib.sha256(f"{base_seed}|{outer_split_id}|{factor}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def compute_outer_split_fdr(
    projection: pd.DataFrame,
    *,
    metric: str,
    bootstrap_samples: int,
    block_length: int,
    random_seed: int,
    fdr_alpha: float,
    source_family: str,
    label_name: str,
    preprocessing_variant: str,
    bootstrap_method: str = "legacy_dropna_moving_block",
) -> pd.DataFrame:
    required = {"outer_split_id", "datetime", "factor", metric}
    missing = required - set(projection.columns)
    if missing:
        raise ValueError(f"outer-train projection missing columns: {sorted(missing)}")
    if projection.duplicated(["outer_split_id", "datetime", "factor"]).any():
        raise ValueError("outer-train projection has duplicate split/date/factor rows")
    bootstrap_functions = {
        "legacy_dropna_moving_block": moving_block_mean_test,
        "gap_aware_moving_block": gap_aware_moving_block_mean_test,
    }
    if bootstrap_method not in bootstrap_functions:
        raise ValueError(f"unsupported bootstrap method: {bootstrap_method}")
    bootstrap_test = bootstrap_functions[bootstrap_method]
    rows = []
    for (outer_split_id, factor), group in projection.groupby(["outer_split_id", "factor"], sort=True):
        values = group.sort_values("datetime", kind="stable")[metric]
        stats = bootstrap_test(
            values,
            samples=bootstrap_samples,
            block_length=block_length,
            seed=factor_seed(random_seed, str(outer_split_id), str(factor)),
        )
        rows.append(
            {
                "outer_split_id": str(outer_split_id),
                "factor": str(factor),
                "test_family": "|".join([source_family, label_name, str(outer_split_id), "train", preprocessing_variant]),
                "family_scope": "outer_split",
                "included_folds": "train",
                "metric": metric,
                "bootstrap_method": bootstrap_method,
                "input_row_count": len(group),
                "input_start_date": pd.to_datetime(group["datetime"]).min(),
                "input_end_date": pd.to_datetime(group["datetime"]).max(),
                **stats,
            }
        )
    return apply_fdr(pd.DataFrame(rows), fdr_alpha)
