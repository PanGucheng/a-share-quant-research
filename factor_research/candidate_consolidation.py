"""Feature-only canonical adapters for Candidate Consolidation V0.5.

This module never accepts target returns or historical performance rankings.
Working-set construction is the one explicit boundary to frozen Primary metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.long_history_screening import (
    DATASET_ID, KEYS, development_range, frame_hash, normalize_keys, sha256_file,
)
from research_validation.canonical_dataset import (
    canonical_dataset_identity, canonical_hash, read_effective_partition,
    validate_partition_segments, validate_semantic_continuity,
)
from model_research.feature_eligibility import _content_hash
from factor_research.factor_clustering import hierarchical_clusters

BOARD_HASH = "edca91b2a8f3a5e54ffd9a8c1b69037f70832c1a8ec745a2dae02e2ceec7ca80"
PRIMARY = "reports/long_history_multi_evaluator_screening_v1"
ERAS = {"A": ("2010-01-29", "2014-12-31"), "B": ("2015-01-01", "2017-12-31"),
        "C": ("2018-01-01", "2020-12-31"), "D": ("2021-01-01", "2023-12-29")}


def verify_primary(root):
    manifest = json.loads((root / PRIMARY / "PRIMARY_V0_MANIFEST.json").read_text(encoding="utf-8"))
    for name, expected in manifest["file_hashes"].items():
        if sha256_file(root / name) != expected:
            raise ValueError(f"frozen Primary changed: {name}")
    if sha256_file(root / PRIMARY / "candidate_board.csv") != BOARD_HASH:
        raise ValueError("unexpected Primary board")
    return manifest["file_hashes"]


def select_working_set(board):
    """Only identity and pass-count authority cross this boundary."""
    columns = ["factor", "source", "agreement", "pass_count"]
    data = board[columns].copy()
    if data.factor.duplicated().any() or len(data) != 765:
        raise ValueError("expected 765 unique research factors")
    selected = data.loc[data.pass_count.ge(2)].sort_values("factor").reset_index(drop=True)
    if len(selected) != 494:
        raise ValueError("expected 494 frozen active factors")
    selected = selected.rename(columns={"agreement": "original_agreement"})
    selected["active_reason"] = "frozen_primary_pass_count_ge_2"
    selected["input_board_hash"] = BOARD_HASH
    return selected


def prepare_inputs(root: Path, config):
    if config["canonical_dataset_id"] != DATASET_ID:
        raise ValueError("wrong canonical identity")
    if config["development_start"] != "2010-01-29" or config["development_end"] != "2023-12-29":
        raise ValueError("fixed development scope required")
    frozen = verify_primary(root)
    base = root / config["canonical_root"]
    partitions = pd.read_csv(base / "partition_manifest.csv")
    lineage = pd.read_csv(base / "factor_lineage.csv")
    if canonical_dataset_identity(partitions, lineage) != DATASET_ID:
        raise ValueError("canonical identity mismatch")
    if len(lineage) != 774 or lineage.factor.nunique() != 774 or lineage.research_usable.sum() != 765:
        raise ValueError("canonical inventory mismatch")
    for result in (validate_partition_segments(partitions), validate_semantic_continuity(lineage)):
        if not result.status.eq("pass").all():
            raise ValueError("canonical continuity failed")
    working = select_working_set(pd.read_csv(root / PRIMARY / "candidate_board.csv",
                                           usecols=["factor", "source", "agreement", "pass_count"]))
    usable = set(lineage.loc[lineage.research_usable, "factor"])
    if not set(working.factor) <= usable or not set(config["controls"]) <= usable:
        raise ValueError("active/control contains blocked or absent factor")
    # Whitelist semantic descriptions, never old directions or global coverage.
    semantic = pd.read_csv(root / "reports/economic_multi_factor_research_v1/economic_map.csv",
                           usecols=["factor", "definition", "primary_family", "mechanism",
                                    "economic_subfamily", "intended_role", "data_horizon"])
    inventory = lineage[["factor", "source", "economic_family", "research_usable",
                         "block_reason", "authoritative_semantics"]].merge(
                             semantic, on="factor", how="left", validate="one_to_one")
    inventory["active"] = inventory.factor.isin(working.factor)
    inventory["review_status"] = np.where(inventory.research_usable, "inherited_requires_reconciliation", "blocked")
    beta = inventory.factor.str.startswith("alpha158_BETA")
    inventory.loc[beta, ["mechanism", "economic_subfamily", "review_status"]] = [
        "normalized_price_slope_not_market_beta", "PriceSlope", "formula_reconciled"]
    close = inventory.factor.str.startswith("alpha360_CLOSE")
    inventory.loc[close, ["mechanism", "economic_subfamily", "review_status"]] = [
        "historical_to_current_close_ratio", "LaggedPriceRatio", "formula_reconciled"]
    event = inventory.factor.isin(["ta_volatility_bbhi", "ta_volatility_kchi"])
    inventory.loc[event, ["economic_subfamily", "review_status"]] = ["TechnicalEventState", "state_mask_review_required"]
    inventory["numeric_verification"] = "not_yet_verified"
    hashes = {str(p.relative_to(root)).replace("\\", "/"): sha256_file(p) for p in (
        base / "partition_manifest.csv", base / "factor_lineage.csv",
        root / "reports/economic_multi_factor_research_v1/economic_map.csv")}
    return working, inventory.sort_values("factor"), partitions, {"primary_hashes": frozen, "input_hashes": hashes}


def read_panel(partitions, factors, start, end, *, access):
    """Intersect before parquet I/O; read columns together and require equal keys.

    No inner join, imputation, or recent-value read is allowed. Physical parquet
    row-group decompression can include boundary bytes; exposed rows are filtered.
    """
    left, right = development_range(start, end)
    names = sorted(factors)
    if not names or len(set(names)) != len(names):
        raise ValueError("nonempty unique factors required")
    pieces = {name: [] for name in names}
    for row in partitions.to_dict("records"):
        cols = sorted(set(str(row["factors"]).split(",")) & set(names))
        lo = max(left, pd.Timestamp(row["effective_start"]))
        hi = min(right, pd.Timestamp(row["effective_end"]))
        if not cols or lo > hi:
            continue
        frame = normalize_keys(read_effective_partition(
            {**row, "effective_start": lo, "effective_end": hi}, columns=cols))
        if frame.empty or not frame.datetime.between(lo, hi).all():
            raise ValueError("empty partition or date boundary violation")
        access.append({"path": str(row["partition_path"]), "columns": cols,
                       "start": str(lo.date()), "end": str(hi.date()), "rows": len(frame),
                       "slice_hash": frame_hash(frame), "parent_sha256": row["output_sha256"]})
        indexed = frame.set_index(KEYS)
        for col in cols:
            pieces[col].append(indexed[col])
    axis, values = None, {}
    for name in names:
        if not pieces[name]:
            raise ValueError(f"missing canonical partition: {name}")
        series = pd.concat(pieces[name]).sort_index(kind="stable")
        if series.index.has_duplicates:
            raise ValueError(f"overlapping canonical keys: {name}")
        if axis is None:
            axis = series.index
        elif not axis.equals(series.index):
            raise ValueError(f"canonical key axis mismatch: {name}")
        values[name] = pd.to_numeric(series, errors="raise").to_numpy(dtype=np.float64)
    return pd.DataFrame(values, index=axis).reset_index()


def canary_dates(calendar):
    result = []
    for lo, hi in ERAS.values():
        dates = calendar[(calendar >= lo) & (calendar <= hi)]
        if not len(dates):
            raise ValueError("missing Era calendar")
        result.extend([dates[0], dates[len(dates) // 2], dates[-1]])
    return pd.DatetimeIndex(result).sort_values().unique()


def exact_duplicate_groups(frame, factors):
    """Hash only locates candidates; equality and non-finite states are checked.

    Scope is the supplied dated axis, not universal algebraic equivalence.
    """
    data = normalize_keys(frame)
    axis_hash = frame_hash(data[KEYS])
    groups, result = {}, []
    for factor in sorted(factors):
        x = data[factor].to_numpy(dtype=float)
        # Match equality semantics for signed zero; keep +/-inf and NaN distinct.
        normalized = x.copy()
        normalized[normalized == 0] = 0
        digest = canonical_hash([axis_hash, _content_hash(normalized)])
        candidates = groups.setdefault(digest, [])
        representative = next((name for name in candidates if np.array_equal(
            x, data[name].to_numpy(dtype=float), equal_nan=True)), None)
        if representative is not None:
            result.append({"factor_a": representative, "factor_b": factor,
                           "relation_type": "exact_duplicate", "evidence_status": "empirically_verified",
                           "axis_hash": axis_hash, "scope_start": str(data.datetime.min()),
                           "scope_end": str(data.datetime.max()), "rows": len(data)})
        candidates.append(factor)
    return result


def cluster_distance(distance, threshold, *, method="complete", view="Full"):
    """Small V0.5 policy around the existing SciPy wrapper, not a new algorithm."""
    if method not in {"complete", "average"} or not 0 <= threshold <= .30:
        raise ValueError("unsupported diagnostic method/cut")
    if not distance.index.is_unique or not distance.index.equals(distance.columns):
        raise ValueError("unique aligned axes required")
    names = sorted(distance.index)
    d = distance.loc[names, names].astype(float)
    x = d.to_numpy()
    if not len(names) or not np.allclose(x, x.T, atol=0, rtol=0, equal_nan=True):
        raise ValueError("nonempty symmetric matrix required")
    if not np.all(np.diag(x) == 0) or np.isinf(x).any() or np.any(x[np.isfinite(x)] < 0) or np.any(x[np.isfinite(x)] > 1):
        raise ValueError("distance must be in [0,1] with zero diagonal")
    if method == "average" and d.isna().any().any():
        raise ValueError("average requires fully known local distances")
    if len(names) == 1:
        groups = [[names[0]]]
    else:
        membership = hierarchical_clusters(d.fillna(2), threshold, method)
        groups = [sorted(g.factor) for _, g in membership.groupby("cluster_id")]
    rows = []
    for group in groups:
        identity = canonical_hash([view, method, threshold, group])[:20]
        rows.extend({"factor": f, "cluster_id": identity, "view": view,
                     "linkage": method, "cut": threshold} for f in group)
    return pd.DataFrame(rows).sort_values("factor").reset_index(drop=True)
