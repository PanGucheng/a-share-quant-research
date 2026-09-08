"""Primary-only descriptive boards and deterministic application of frozen rules."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from factor_research.long_history_screening import END, LABEL, START, sha256_file
from qlib_baseline.io import atomic_write_json
from research_validation.canonical_dataset import canonical_hash
from research_validation.multiple_testing import apply_fdr

METRICS = ["alphalens_ic", "jqfactor_ic", "qlib_ic", "qlib_pearson", "jqfactor_returns",
           "qlib_long_short", "qlib_cross_section_mean", *[f"alphalens_q{i}" for i in range(1, 6)],
           "alphalens_q5_minus_q1"]
STATS = ["mean", "median", "std", "mean_std_ratio", "positive_ratio", "valid_dates"]
ECONOMIC_COLUMNS = ["factor", "primary_family", "economic_subfamily", "mechanism", "evidence_level", "definition"]


def seal(directory: Path, metadata: dict) -> dict:
    payload = {**metadata, "file_hashes": {p.name: sha256_file(p) for p in sorted(directory.iterdir())
                                         if p.is_file() and p.name != "receipt.json"}}
    payload["content_id"] = canonical_hash(payload)
    atomic_write_json(directory / "receipt.json", payload)
    return payload


def verify_seal(directory: Path) -> dict:
    receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
    identifier = receipt.pop("content_id")
    if identifier != canonical_hash(receipt):
        raise ValueError("board receipt corrupted")
    if any(sha256_file(directory / n) != h for n, h in receipt["file_hashes"].items()):
        raise ValueError("board evidence corrupted")
    return {**receipt, "content_id": identifier}


def descriptive_board(inventory, metrics, quality, fdr, economic):
    """Explicit column allowlists exclude historical outcomes and optional horizons."""
    names = inventory.loc[inventory.research_usable, "factor"].sort_values().tolist()
    if metrics.duplicated(["factor", "metric", "period_id"]).any():
        raise ValueError("duplicate primary period metric")
    if set(metrics.factor) != set(names) or set(metrics.metric) != set(METRICS):
        raise ValueError("primary metric inventory mismatch")
    if not metrics.label.eq(LABEL).all() or not metrics.universe.eq("canonical_practical_raw").all():
        raise ValueError("non-primary evidence")
    for column, upper in (("actual_signal_start", pd.Timestamp("2023-11-30")),
                          ("actual_signal_end", pd.Timestamp("2023-11-30")),
                          ("max_label_exit_date", END)):
        dates = pd.to_datetime(metrics[column]).dropna()
        if not dates.between(START, upper).all():
            raise ValueError("evidence outside mature development dates")
    if not metrics.groupby(["factor", "metric"]).size().eq(19).all():
        raise ValueError("missing required period views")
    board = inventory.loc[inventory.factor.isin(names), ["factor", "canonical_factor_id", "source",
                            "economic_family", "authoritative_semantics", "lineage_hash"]].copy().set_index("factor")
    quality_columns = ["factor", "rows", "finite_count", "missing_count", "infinite_count", "coverage",
                       "first_finite_date", "last_finite_date", "min_count_variable_dates"]
    board = board.join(quality[quality_columns].set_index("factor"), validate="one_to_one")
    board = board.join(economic[ECONOMIC_COLUMNS].set_index("factor"), validate="one_to_one")
    fdr_columns = ["factor", "status", "raw_p_value", "fdr_bh_q_value", "fdr_by_q_value",
                   "observation_count", "eligible_segment_count", "contiguous_segment_count", "eligible_block_count"]
    board = board.join(fdr[fdr_columns].rename(columns={"status": "fdr_status"}).set_index("factor"), validate="one_to_one")
    full = metrics.loc[metrics.period_type.eq("full")]
    for metric in METRICS:
        subset = full.loc[full.metric.eq(metric)].set_index("factor")
        for stat in STATS:
            board[f"{metric}__{stat}"] = subset[stat]
    rows = []
    for factor in names:
        part = metrics.loc[metrics.factor.eq(factor)]
        ic = part.loc[part.metric.eq("qlib_ic")]
        annual = ic.loc[ic.period_type.eq("annual")].sort_values("period_id")
        eras = ic.loc[ic.period_type.eq("signal_era")].sort_values("period_id")
        raw_mean = board.loc[factor, "qlib_ic__mean"]
        direction = np.sign(raw_mean) if pd.notna(raw_mean) else np.nan
        qualified_years = annual.loc[annual.valid_dates.ge(126)]
        qmeans = pd.Series([board.loc[factor, f"alphalens_q{i}__mean"] for i in range(1, 6)])
        monotonicity = qmeans.corr(pd.Series(range(1, 6)), method="spearman") if qmeans.notna().all() and qmeans.nunique() > 1 else np.nan
        total_n = eras.valid_dates.sum()
        contributions = eras["mean"] * eras.valid_dates
        abs_total = contributions.abs().sum()
        loo = (contributions.sum() - contributions) / (total_n - eras.valid_dates).replace(0, np.nan)
        row = {"factor": factor, "alphalens_quantile_monotonicity_raw": monotonicity,
               "annual_qualified_years": len(qualified_years),
               "annual_direction_agreement": (qualified_years["mean"].mul(direction).gt(0).mean()
                                               if len(qualified_years) and direction != 0 else np.nan),
               "annual_ic_sequence_raw": json.dumps(dict(zip(annual.period_id, annual["mean"])), allow_nan=True),
               "era_ic_sequence_raw": json.dumps(dict(zip(eras.period_id, eras["mean"])), allow_nan=True),
               "era_count_available": int(eras.valid_dates.gt(0).sum()),
               "max_absolute_era_contribution_share": contributions.abs().max() / abs_total if abs_total > 0 else np.nan,
               "worst_directional_era_mean": eras["mean"].mul(direction).min(),
               "worst_leave_one_era_out_directional_mean": loo.mul(direction).min()}
        for _, era in eras.iterrows():
            row[f"era_{era.period_id}_mean_raw"] = era["mean"]
            row[f"era_{era.period_id}_valid_dates"] = era.valid_dates
            row[f"era_{era.period_id}_ic_sum_raw"] = era["mean"] * era.valid_dates
        returns = part.loc[part.metric.eq("jqfactor_returns") & part.period_type.eq("annual") & part.valid_dates.ge(126)]
        row["jqfactor_return_qualified_years"] = len(returns)
        row["jqfactor_return_annual_direction_agreement"] = (returns["mean"].mul(direction).gt(0).mean()
                                                                             if len(returns) and direction != 0 else np.nan)
        rows.append(row)
    board = board.join(pd.DataFrame(rows).set_index("factor"), validate="one_to_one").reset_index()
    board["evidence_scope"] = "primary_20d"
    board["direction_origin_preview"] = "sign_of_development_full_qlib_rank_ic_data_derived"
    board["parity_status"] = "pass"
    board["native_profile_limited"] = "correlated_frameworks_not_independent_votes"
    for backend in ("alphalens", "jqfactor", "qlib"):
        board[f"{backend}_candidate_status"] = "not_evaluated"
    board["native_disagreement"] = "not_evaluated"
    for field in ("secondary_universe", "microcap_exposure", "turnover", "numeric_duplicate_clustering", "auxiliary_10d"):
        board[f"{field}_status"] = "not_run"
    return board.sort_values("factor").reset_index(drop=True)


def build_evidence(root: Path, run: Path) -> dict:
    from scripts.run_long_history_primary_full import completed_chunk
    contract = json.loads((run / "contract.json").read_text(encoding="utf-8"))
    digest = canonical_hash(contract)
    aggregate = completed_chunk(run / "aggregate", digest)
    if aggregate is None or aggregate["completed_chunks"] != 10710:
        raise ValueError("full primary computation incomplete")
    inventory = pd.read_csv(run / "aggregate/factor_inventory.csv")
    names = sorted(inventory.loc[inventory.research_usable, "factor"])
    if len(names) != 765 or inventory.factor.nunique() != 774:
        raise ValueError("incorrect canonical inventory")
    fdr = pd.read_csv(run / "aggregate/primary_fdr.csv")
    if sorted(fdr.factor) != names or not fdr.planned_family_count.eq(765).all():
        raise ValueError("incorrect FDR family")
    checked = apply_fdr(fdr, alpha=0.05)
    for column in ("fdr_bh_q_value", "fdr_by_q_value"):
        np.testing.assert_allclose(checked[column], fdr[column], rtol=0, atol=1e-14)
    for column, value in (("bootstrap_samples", 1000), ("block_length", 20), ("random_seed", 20260907)):
        if not fdr.loc[fdr.status.eq("available"), column].eq(value).all():
            raise ValueError("bootstrap contract drift")
    rows, masks, max_difference = [], [], 0.
    for year in range(2010, 2024):
        print(f"Verifying all native chunks and sample counts: {year}", flush=True)
        for factor in names:
            folder = run / "chunks" / str(year) / factor
            receipt = completed_chunk(folder, digest)
            if receipt is None or receipt["factor"] != factor or receipt["year"] != year:
                raise ValueError("missing/misidentified native chunk")
            if receipt["parity_status"] not in ("pass", "unavailable") or any(v.startswith("failed") for v in receipt["native_status"].values()):
                raise ValueError("native failure blocks Board")
            max_difference = max(max_difference, max(receipt.get("max_abs_difference", {"none": 0}).values()))
            access = json.loads((folder / "access.json").read_text(encoding="utf-8"))
            for item in [*access["factor"], access["price"]]:
                if not START <= pd.Timestamp(item["requested_start"]) <= pd.Timestamp(item["requested_end"]) <= END:
                    raise ValueError("access audit escaped development")
            samples = pd.read_csv(folder / "daily_sample_status.csv", parse_dates=["datetime"])
            if samples.datetime.duplicated().any() or not samples.datetime.between(START, pd.Timestamp("2023-11-30")).all():
                raise ValueError("invalid sample dates")
            if not samples.ic_available.isin([True, False]).all() or not samples.quantile_available.isin([True, False]).all():
                raise ValueError("invalid sample masks")
            masks.append({"factor": factor, "year": year, "canonical_signal_rows": int(samples.canonical_rows.sum()),
                          "finite_pairs": int(samples.finite_pairs.sum()),
                          "ic_samples": int(samples.loc[samples.ic_available, "finite_pairs"].sum()),
                          "quantile_samples": int(samples.loc[samples.quantile_available, "finite_pairs"].sum()),
                          "ic_dates": int(samples.ic_available.sum()), "quantile_dates": int(samples.quantile_available.sum())})
            rows.append({"factor": factor, "year": year, "parity_status": receipt["parity_status"],
                         "raw_path": str(folder.relative_to(root)), "native_status": json.dumps(receipt["native_status"], sort_keys=True)})
    if max_difference > contract["config"]["parity_atol"]:
        raise ValueError("parity tolerance exceeded")
    metrics = pd.read_parquet(run / "aggregate/period_metrics.parquet")
    means = metrics.loc[metrics.metric.eq("qlib_ic") & metrics.period_type.eq("full")].set_index("factor")
    np.testing.assert_allclose(means.loc[fdr.factor, "mean"], fdr.raw_statistic, rtol=0, atol=1e-15)
    count_frame = pd.DataFrame(masks)
    np.testing.assert_array_equal(count_frame.groupby("factor").ic_dates.sum().reindex(fdr.factor), fdr.observation_count)
    quality_path = root / "reports/long_history_multi_evaluator_screening_v1/FEATURE_QUALITY_FULL.csv"
    if sha256_file(quality_path) != contract["qualification_hashes"][quality_path.name]:
        raise ValueError("quality evidence changed")
    quality = pd.read_csv(quality_path)
    economic_path = root / "reports/economic_multi_factor_research_v1/economic_map.csv"
    economic = pd.read_csv(economic_path, usecols=ECONOMIC_COLUMNS)
    board = descriptive_board(inventory, metrics, quality, fdr, economic)
    totals = count_frame.groupby("factor").sum(numeric_only=True).drop(columns="year")
    board = board.merge(totals, on="factor", validate="one_to_one")
    board["ic_sample_coverage"] = board.ic_samples / board.canonical_signal_rows
    board["quantile_sample_coverage"] = board.quantile_samples / board.canonical_signal_rows
    board["raw_path_template"] = str(run.relative_to(root) / "chunks/{year}/{factor}")
    board["period_metrics_path"] = str(run.relative_to(root) / "aggregate/period_metrics.parquet")
    duplicates = pd.read_csv(root / "reports/factor_universe_v2/duplicate_equivalence_audit.csv",
                             usecols=["factor_a", "factor_b", "relationship"])
    board["legacy_duplicate_relations"] = [json.dumps(duplicates.loc[duplicates.factor_a.eq(f) | duplicates.factor_b.eq(f)].to_dict("records"))
                                             for f in board.factor]
    out = run / "primary/evidence_v0"
    out.mkdir(parents=True, exist_ok=False)
    board.to_csv(out / "factor_evidence_board.csv", index=False)
    board.to_parquet(out / "factor_evidence_board.parquet", index=False)
    inventory.to_csv(out / "factor_inventory.csv", index=False)
    count_frame.to_csv(out / "daily_sample_counts_by_year.csv", index=False)
    pd.DataFrame(rows).to_csv(out / "batch_status.csv", index=False)
    fdr.to_csv(out / "multiple_testing.csv", index=False)
    metrics.to_parquet(out / "factor_period_metrics.parquet", index=False)
    distributions = board.select_dtypes(include="number").describe(percentiles=[.1, .25, .5, .75, .9, .95]).T
    distributions.to_csv(out / "primary_metric_distributions.csv", index_label="metric")
    annual_quality = root / "outputs/long_history_multi_evaluator_screening_v1/quality_765_20260907/phase0/quality/feature_quality_annual.csv"
    pd.read_csv(annual_quality).to_csv(out / "data_quality_by_year.csv", index=False)
    atomic_write_json(out / "metric_definitions.json", {
        "source": "native daily metrics, original raw direction; overlapping 20D labels, not strategy returns",
        "monotonicity": "Spearman correlation of five full-period native quantile means with [1,2,3,4,5]; derived summary, not upstream native function",
        "annual_agreement": "years with >=126 valid dates; fraction whose mean has full-development Qlib Rank IC sign",
        "era_contribution": "mean IC times valid dates; maximum absolute sum share across four signal-date eras",
        "leave_one_era_out": "sum of remaining daily IC / remaining valid dates; no equal-year weighting",
        "missing": "unavailable remains missing, never zero; optional not_run is not absence of risk",
        "native_profile_limited": "common samples, correlated metrics and frameworks; not independent statistical votes",
    })
    return seal(out, {"stage": "evidence_before_candidate_rules", "run_id": run.name, "contract_hash": digest,
                      "input_aggregate_receipt_sha256": sha256_file(run / "aggregate/receipt.json"),
                      "economic_description_sha256": sha256_file(economic_path),
                      "board_code_sha256": sha256_file(Path(__file__)), "factors": len(board), "verified_chunks": len(rows),
                      "unavailable_annual_chunks": sum(r["parity_status"] == "unavailable" for r in rows),
                      "max_rank_ic_difference": max_difference, "held_aside_recent_diagnostic_accessed": False})
