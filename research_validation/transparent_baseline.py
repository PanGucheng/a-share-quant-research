from __future__ import annotations

import pandas as pd

from portfolio.score_construction import capped_normalize
from research_validation.feature_matrix import canonical_hash


WEIGHT_COLUMNS = [
    "outer_split_id",
    "method",
    "factor",
    "factor_column",
    "feature_order",
    "cluster_id",
    "direction",
    "selection_frequency",
    "upstream_fdr_q_value",
    "raw_weight",
    "weight",
]


def weight_payload_hash(frame: pd.DataFrame) -> str:
    columns = [
        "factor",
        "factor_column",
        "feature_order",
        "cluster_id",
        "direction",
        "raw_weight",
        "weight",
    ]
    ordered = frame[columns].sort_values("feature_order", kind="stable")
    return canonical_hash(ordered.to_dict("records"))


def build_transparent_weights(
    allowlist: pd.DataFrame,
    *,
    methods: list[str],
    maximum_factor_weight: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "outer_split_id",
        "factor",
        "feature_order",
        "cluster_id",
        "frozen_direction",
        "selection_frequency",
        "upstream_fdr_q_value",
        "upstream_fdr_pass",
        "stability_role",
        "holdout_clean",
    }
    missing = required - set(allowlist.columns)
    if missing:
        raise ValueError(f"split allowlist missing transparent-weight fields: {sorted(missing)}")
    forbidden = [column for column in allowlist if str(column).startswith("test_") or "oos" in str(column).lower()]
    if forbidden:
        raise ValueError(f"transparent weights cannot consume test/OOS fields: {forbidden}")
    if allowlist.duplicated(["outer_split_id", "factor"]).any():
        raise ValueError("split allowlist contains duplicate outer_split_id/factor keys")
    invalid = allowlist.loc[
        ~allowlist["holdout_clean"].fillna(False).astype(bool)
        | ~allowlist["upstream_fdr_pass"].fillna(False).astype(bool)
        | ~allowlist["stability_role"].eq("stable_core")
        | ~allowlist["frozen_direction"].isin([-1, 1])
    ]
    if not invalid.empty:
        raise ValueError("transparent weights require holdout-clean stable-core FDR-pass factors")

    rows: list[pd.DataFrame] = []
    manifests: list[dict[str, object]] = []
    for outer_split_id, split_values in allowlist.groupby("outer_split_id", sort=True):
        split_values = split_values.sort_values("feature_order", kind="stable").copy()
        if split_values["feature_order"].tolist() != list(range(len(split_values))):
            raise ValueError(f"feature order is not contiguous for {outer_split_id}")
        if split_values["cluster_id"].duplicated().any():
            raise ValueError(f"duplicate cluster vote in {outer_split_id}")
        allowlist_sha256 = str(split_values["allowlist_sha256"].iloc[0])
        for method in methods:
            current = split_values.copy()
            if method == "equal_weight":
                current["raw_weight"] = 1.0
            elif method == "stability_weight":
                current["raw_weight"] = (
                    pd.to_numeric(current["selection_frequency"], errors="raise").clip(lower=0.05)
                    * (1.0 - pd.to_numeric(current["upstream_fdr_q_value"], errors="raise").clip(0.0, 1.0))
                )
            else:
                raise ValueError(f"unsupported transparent method: {method}")
            current["weight"] = capped_normalize(current["raw_weight"], maximum_factor_weight)
            current["method"] = method
            current["factor_column"] = current["factor"].astype(str)
            current["direction"] = current["frozen_direction"].astype(int)
            current = current.rename(columns={"outer_split_id": "outer_split_id"})
            rows.append(current[WEIGHT_COLUMNS])
            manifests.append(
                {
                    "outer_split_id": outer_split_id,
                    "method": method,
                    "factor_count": len(current),
                    "weight_sum": float(current["weight"].sum()),
                    "maximum_weight": float(current["weight"].max()),
                    "weights_sha256": weight_payload_hash(current),
                    "allowlist_sha256": allowlist_sha256,
                    "feature_order_sha256": canonical_hash(current.sort_values("feature_order")["factor"].tolist()),
                    "holdout_clean": True,
                }
            )
    return pd.concat(rows, ignore_index=True), pd.DataFrame(manifests)
