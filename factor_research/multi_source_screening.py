from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any

import numpy as np
import pandas as pd

from factor_research.catalog import catalog_frame, load_factor_catalog
from factor_research.report import markdown_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERIOD_RE = re.compile(r"period_(\d+)", re.IGNORECASE)
LABEL_RE = re.compile(r"label_(\d+)d", re.IGNORECASE)


@dataclass(frozen=True)
class MultiSourceScreeningConfig:
    alpha158_screening_input: Path
    alpha158_candidate_pool: Path
    alpha158_catalog: Path
    ta_catalog: Path
    ta_holdout_catalog: Path
    ta_factor_summary: Path
    ta_metric_indexes: tuple[Path, ...]
    ta_promotion_audits: tuple[Path, ...]
    ta_evaluator_statuses: tuple[Path, ...]
    alpha101_catalog: Path
    alpha101_holdout_catalog: Path
    alpha101_factor_summary: Path
    alpha101_metric_indexes: tuple[Path, ...]
    alpha101_promotion_audits: tuple[Path, ...]
    alpha101_evaluator_statuses: tuple[Path, ...]
    alpha360_catalog: Path
    alpha360_holdout_catalog: Path
    alpha360_factor_summary: Path
    alpha360_metric_indexes: tuple[Path, ...]
    alpha360_promotion_audits: tuple[Path, ...]
    alpha360_evaluator_statuses: tuple[Path, ...]
    output_dir: Path
    pool_name: str = "multi_source_v1"
    min_sources: int = 2
    min_total_rows: int = 200
    min_new_source_rows: int = 20


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def normalize_horizon(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    if not text:
        return ""
    match = PERIOD_RE.search(text)
    if match:
        return f"{match.group(1)}d"
    match = LABEL_RE.search(text)
    if match:
        return f"{match.group(1)}d"
    return text.lower()


def numeric(value: object) -> float:
    result = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(result) if pd.notna(result) else np.nan


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def metric_column(system: str, metric: str, horizon: str) -> str | None:
    horizon_key = normalize_horizon(horizon)
    if not horizon_key:
        return None
    system_key = str(system)
    metric_key = str(metric)
    if system_key == "alphalens_reloaded" and metric_key == "mean_information_coefficient":
        return f"alphalens_mean_ic_{horizon_key}"
    if system_key == "alphalens_reloaded" and metric_key == "factor_alpha_beta:Ann. alpha":
        return f"alphalens_ann_alpha_{horizon_key}"
    if system_key == "alphalens_reloaded" and metric_key == "factor_alpha_beta:beta":
        return f"alphalens_beta_{horizon_key}"
    if system_key == "jqfactor_analyzer" and metric_key == "mean_information_coefficient":
        return f"jqfactor_mean_ic_{horizon_key}"
    if system_key == "qlib_eval" and metric_key in {
        "mean",
        "std",
        "annualized_return",
        "information_ratio",
        "max_drawdown",
    }:
        return f"qlib_{metric_key}_{horizon_key}"
    return None


def load_metric_snapshot(paths: tuple[Path, ...]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = read_csv_or_empty(path)
        if frame.empty:
            continue
        frame["metric_source"] = portable_path(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["factor"])
    metrics = pd.concat(frames, ignore_index=True)
    if "scope" in metrics.columns:
        metrics = metrics[metrics["scope"].fillna("open_source").eq("open_source")]
    metrics["metric_key"] = [
        metric_column(row.system, row.metric, row.horizon)
        for row in metrics[["system", "metric", "horizon"]].itertuples(index=False)
    ]
    metrics = metrics[metrics["metric_key"].notna()].copy()
    if metrics.empty:
        return pd.DataFrame(columns=["factor"])
    metrics["value"] = pd.to_numeric(metrics["value"], errors="coerce")
    pivot = (
        metrics.dropna(subset=["value"])
        .pivot_table(index="factor", columns="metric_key", values="value", aggfunc="mean")
        .reset_index()
    )
    counts = (
        metrics.dropna(subset=["value"])
        .groupby("factor")
        .size()
        .reset_index(name="metric_value_count")
    )
    return pivot.merge(counts, on="factor", how="left")


def load_catalog(path: Path, catalog_id: str) -> pd.DataFrame:
    frame = catalog_frame(load_factor_catalog(path))
    frame["catalog_id"] = catalog_id
    return frame.rename(columns={"name": "factor"})


def status_rank(status: str) -> int:
    order = {"failed": 0, "not_run": 1, "partial_pass": 2, "skipped_non_informative": 3, "pass": 4}
    return order.get(str(status), 1)


def aggregate_evaluator_status(paths: tuple[Path, ...]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = read_csv_or_empty(path)
        if frame.empty:
            continue
        frame["status_source"] = portable_path(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["factor", "alphalens_status", "jqfactor_status", "qlib_status"])
    status = pd.concat(frames, ignore_index=True)
    rows = []
    for (factor, system), group in status.groupby(["factor", "system"], dropna=False):
        values = [str(value) for value in group["status"].dropna()]
        worst = min(values, key=status_rank) if values else "not_run"
        rows.append({"factor": factor, "system": system, "status": worst})
    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=["factor", "alphalens_status", "jqfactor_status", "qlib_status"])
    return result.pivot(index="factor", columns="system", values="status").reset_index().rename(
        columns={
            "alphalens_reloaded": "alphalens_status",
            "jqfactor_analyzer": "jqfactor_status",
            "qlib_eval": "qlib_status",
        }
    )


def load_ta_promotion_audit(paths: tuple[Path, ...]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = read_csv_or_empty(path)
        if frame.empty:
            continue
        if "decision" not in frame.columns and "promoted" in frame.columns:
            frame["decision"] = np.where(frame["promoted"].map(as_bool), "promoted", "holdout")
        if "reason" not in frame.columns:
            frame["reason"] = ""
        frame["promotion_source"] = portable_path(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["factor", "decision", "reason"])
    audit = pd.concat(frames, ignore_index=True, sort=False)
    rank = {"holdout": 0, "promoted": 1}
    audit["_rank"] = audit["decision"].map(rank).fillna(0)
    audit = audit.sort_values(["factor", "_rank"]).drop_duplicates("factor", keep="last")
    return audit.drop(columns=["_rank"])


def build_alpha158_rows(config: MultiSourceScreeningConfig) -> pd.DataFrame:
    source = read_csv_or_empty(config.alpha158_screening_input)
    if source.empty:
        raise FileNotFoundError(f"Missing Alpha158 screening input: {config.alpha158_screening_input}")
    catalog = load_catalog(config.alpha158_catalog, "alpha158_full_runnable_catalog")
    pool = read_csv_or_empty(config.alpha158_candidate_pool)
    pool_cols = [
        "factor",
        "role",
        "included",
        "pool_reason",
        "judgement_label",
        "consensus_direction",
        "primary_rank_ic",
        "primary_abs_rank_ic",
        "max_abs_rank_ic",
        "max_abs_rank_icir",
        "max_rank_ic_win_rate",
        "issue_tags",
    ]
    pool = pool[[col for col in pool_cols if col in pool.columns]].copy() if not pool.empty else pd.DataFrame(columns=pool_cols)
    rows = source.merge(
        catalog[
            [
                "factor",
                "registry_name",
                "category",
                "stage",
                "enabled",
                "runnable",
                "expected_direction",
                "source_project",
                "license",
                "compute_adapter",
            ]
        ],
        on="factor",
        how="left",
        suffixes=("", "_catalog"),
    )
    rows = rows.merge(pool, on="factor", how="left", suffixes=("", "_pool"))
    rows["source_family"] = "alpha158"
    rows["screening_gate"] = rows.get("evaluation_gate", "review")
    rows["promotion_decision"] = np.where(rows["screening_gate"].eq("strict_screening_input"), "promoted", "holdout")
    rows["promotion_reason"] = rows.get("holdout_reason", "")
    fallback_role = pd.Series(
        np.where(rows["screening_gate"].eq("holdout"), "holdout", "monitor"),
        index=rows.index,
    )
    rows["role"] = rows["role"].fillna(fallback_role)
    rows["included"] = rows["included"].fillna(False).map(as_bool)
    rows["pool_reason"] = rows["pool_reason"].fillna("alpha158_existing_screening_role")
    return rows


def build_ta_rows(config: MultiSourceScreeningConfig) -> pd.DataFrame:
    promoted = load_catalog(config.ta_catalog, "ta_promoted_catalog")
    holdout = load_catalog(config.ta_holdout_catalog, "ta_holdout_catalog")
    catalog = pd.concat([promoted, holdout], ignore_index=True).drop_duplicates("factor", keep="first")
    summary = read_csv_or_empty(config.ta_factor_summary)
    if not summary.empty:
        summary = summary.rename(columns={"factor": "factor"})[
            ["factor", "valid_rows", "total_rows", "coverage", "missing_rate"]
        ]
    metrics = load_metric_snapshot(config.ta_metric_indexes)
    audit = load_ta_promotion_audit(config.ta_promotion_audits)
    status = aggregate_evaluator_status(config.ta_evaluator_statuses)
    rows = catalog.merge(summary, on="factor", how="left")
    rows = rows.merge(metrics, on="factor", how="left")
    rows = rows.merge(audit, on="factor", how="left")
    rows = rows.merge(status, on="factor", how="left", suffixes=("", "_status"))
    for column in ["alphalens_status", "jqfactor_status", "qlib_status"]:
        audit_column = column
        status_column = f"{column}_status"
        if status_column in rows.columns:
            rows[audit_column] = rows[audit_column].fillna(rows[status_column])
    rows["source_family"] = "ta"
    fallback_decision = pd.Series(
        np.where(rows["catalog_id"].eq("ta_holdout_catalog"), "holdout", "promoted"),
        index=rows.index,
    )
    rows["decision"] = rows["decision"].fillna(fallback_decision)
    rows["screening_gate"] = np.where(rows["decision"].eq("promoted"), "strict_screening_input", "holdout")
    rows["promotion_decision"] = rows["decision"]
    rows["promotion_reason"] = rows["reason"].fillna("")
    rows["role"] = np.where(rows["screening_gate"].eq("holdout"), "holdout", "monitor")
    rows["included"] = False
    rows["pool_reason"] = np.where(
        rows["screening_gate"].eq("holdout"),
        "open_source_evaluator_holdout",
        "promoted_new_source_pending_judgement",
    )
    rows["evaluation_gate"] = rows["screening_gate"]
    rows["judgement_label"] = np.where(rows["screening_gate"].eq("holdout"), "holdout", "new_source_monitor")
    rows["consensus_direction"] = "watch"
    rows["issue_tags"] = ""
    return rows


def build_alpha101_rows(config: MultiSourceScreeningConfig) -> pd.DataFrame:
    promoted = load_catalog(config.alpha101_catalog, "alpha101_promoted_catalog")
    holdout = load_catalog(config.alpha101_holdout_catalog, "alpha101_holdout_catalog")
    catalog = pd.concat([promoted, holdout], ignore_index=True).drop_duplicates("factor", keep="first")
    summary = read_csv_or_empty(config.alpha101_factor_summary)
    if not summary.empty:
        summary = summary[["factor", "valid_rows", "total_rows", "coverage", "missing_rate"]]
    metrics = load_metric_snapshot(config.alpha101_metric_indexes)
    audit = load_ta_promotion_audit(config.alpha101_promotion_audits)
    status = aggregate_evaluator_status(config.alpha101_evaluator_statuses)
    rows = catalog.merge(summary, on="factor", how="left")
    rows = rows.merge(metrics, on="factor", how="left")
    rows = rows.merge(audit, on="factor", how="left")
    rows = rows.merge(status, on="factor", how="left", suffixes=("", "_status"))
    for column in ["alphalens_status", "jqfactor_status", "qlib_status"]:
        audit_column = column
        status_column = f"{column}_status"
        if status_column in rows.columns:
            rows[audit_column] = rows[audit_column].fillna(rows[status_column])
    rows["source_family"] = "alpha101"
    fallback_decision = pd.Series(
        np.where(rows["catalog_id"].eq("alpha101_holdout_catalog"), "holdout", "promoted"),
        index=rows.index,
    )
    rows["decision"] = rows["decision"].fillna(fallback_decision)
    rows["screening_gate"] = np.where(rows["decision"].eq("promoted"), "strict_screening_input", "holdout")
    rows["promotion_decision"] = rows["decision"]
    rows["promotion_reason"] = rows["reason"].fillna("")
    rows["role"] = np.where(rows["screening_gate"].eq("holdout"), "holdout", "monitor")
    rows["included"] = False
    rows["pool_reason"] = np.where(
        rows["screening_gate"].eq("holdout"),
        "open_source_evaluator_holdout",
        "promoted_new_source_pending_judgement",
    )
    rows["evaluation_gate"] = rows["screening_gate"]
    rows["judgement_label"] = np.where(rows["screening_gate"].eq("holdout"), "holdout", "new_source_monitor")
    rows["consensus_direction"] = "watch"
    rows["issue_tags"] = ""
    return rows


def build_alpha360_rows(config: MultiSourceScreeningConfig) -> pd.DataFrame:
    promoted = load_catalog(config.alpha360_catalog, "alpha360_promoted_catalog")
    holdout = load_catalog(config.alpha360_holdout_catalog, "alpha360_holdout_catalog")
    catalog = pd.concat([promoted, holdout], ignore_index=True).drop_duplicates("factor", keep="first")
    summary = read_csv_or_empty(config.alpha360_factor_summary)
    if not summary.empty:
        summary = summary[["factor", "valid_rows", "total_rows", "coverage", "missing_rate"]]
    metrics = load_metric_snapshot(config.alpha360_metric_indexes)
    audit = load_ta_promotion_audit(config.alpha360_promotion_audits)
    status = aggregate_evaluator_status(config.alpha360_evaluator_statuses)
    rows = catalog.merge(summary, on="factor", how="left")
    rows = rows.merge(metrics, on="factor", how="left")
    rows = rows.merge(audit, on="factor", how="left")
    rows = rows.merge(status, on="factor", how="left", suffixes=("", "_status"))
    for column in ["alphalens_status", "jqfactor_status", "qlib_status"]:
        status_column = f"{column}_status"
        if status_column in rows.columns:
            rows[column] = rows[column].fillna(rows[status_column])
    rows["source_family"] = "alpha360"
    fallback_decision = pd.Series(
        np.where(rows["catalog_id"].eq("alpha360_holdout_catalog"), "holdout", "promoted"),
        index=rows.index,
    )
    rows["decision"] = rows["decision"].fillna(fallback_decision)
    rows["screening_gate"] = np.where(rows["decision"].eq("promoted"), "strict_screening_input", "holdout")
    rows["promotion_decision"] = rows["decision"]
    rows["promotion_reason"] = rows["reason"].fillna("")
    rows["role"] = np.where(rows["screening_gate"].eq("holdout"), "holdout", "monitor")
    rows["included"] = False
    rows["pool_reason"] = np.where(
        rows["screening_gate"].eq("holdout"),
        "open_source_evaluator_holdout",
        "promoted_new_source_pending_judgement",
    )
    rows["evaluation_gate"] = rows["screening_gate"]
    rows["judgement_label"] = np.where(rows["screening_gate"].eq("holdout"), "holdout", "new_source_monitor")
    rows["consensus_direction"] = "watch"
    rows["issue_tags"] = ""
    return rows


STANDARD_COLUMNS = [
    "pool_name",
    "factor",
    "source_family",
    "source_project",
    "category",
    "stage",
    "screening_gate",
    "promotion_decision",
    "promotion_reason",
    "role",
    "included",
    "pool_reason",
    "judgement_label",
    "expected_direction",
    "consensus_direction",
    "coverage",
    "missing_rate",
    "valid_rows",
    "total_rows",
    "alphalens_status",
    "jqfactor_status",
    "qlib_status",
    "metric_value_count",
    "alphalens_mean_ic_10d",
    "alphalens_mean_ic_20d",
    "jqfactor_mean_ic_10d",
    "jqfactor_mean_ic_20d",
    "qlib_mean_10d",
    "qlib_mean_20d",
    "qlib_information_ratio_10d",
    "qlib_information_ratio_20d",
    "alphalens_ann_alpha_10d",
    "alphalens_ann_alpha_20d",
    "primary_rank_ic",
    "primary_abs_rank_ic",
    "max_abs_rank_ic",
    "max_abs_rank_icir",
    "max_rank_ic_win_rate",
    "issue_tags",
    "license",
    "compute_adapter",
]


def standardize_columns(frame: pd.DataFrame, pool_name: str) -> pd.DataFrame:
    rows = frame.copy()
    rows["pool_name"] = pool_name
    rename_map = {
        "alphalens_rank_ic_10d": "alphalens_mean_ic_10d",
        "alphalens_rank_ic_20d": "alphalens_mean_ic_20d",
        "jqfactor_rank_ic_10d": "jqfactor_mean_ic_10d",
        "jqfactor_rank_ic_20d": "jqfactor_mean_ic_20d",
    }
    for source, target in rename_map.items():
        if target not in rows.columns and source in rows.columns:
            rows[target] = rows[source]
    for column in STANDARD_COLUMNS:
        if column not in rows.columns:
            rows[column] = pd.NA
    result = rows[STANDARD_COLUMNS].copy()
    result["included"] = result["included"].map(as_bool)
    result["coverage"] = pd.to_numeric(result["coverage"], errors="coerce")
    result["missing_rate"] = pd.to_numeric(result["missing_rate"], errors="coerce")
    sort_role = {"alpha_candidate": 0, "monitor": 1, "holdout": 2}
    result["_role_order"] = result["role"].map(sort_role).fillna(10)
    result["_source_order"] = result["source_family"].map({"alpha158": 0, "ta": 1, "alpha101": 2, "alpha360": 3}).fillna(9)
    result = result.sort_values(["_role_order", "_source_order", "factor"]).drop(columns=["_role_order", "_source_order"])
    return result.reset_index(drop=True)


def build_candidate_board(screening_input: pd.DataFrame) -> pd.DataFrame:
    board = screening_input.copy()
    board["board_status"] = np.select(
        [
            board["role"].eq("alpha_candidate"),
            board["role"].eq("holdout"),
            board["screening_gate"].eq("strict_screening_input"),
        ],
        ["alpha_candidate", "holdout", "source_monitor"],
        default="review",
    )
    board["board_reason"] = np.select(
        [
            board["role"].eq("alpha_candidate"),
            board["role"].eq("holdout"),
            board["source_family"].ne("alpha158") & board["screening_gate"].eq("strict_screening_input"),
        ],
        [
            "accepted_by_existing_alpha158_candidate_pool",
            "kept_out_by_source_promotion_or_judgement_gate",
            "new_source_promoted_but_waiting_for_generic_judgement_rules",
        ],
        default=board["pool_reason"].fillna("review"),
    )
    return board


def build_contract_status(screening_input: pd.DataFrame, board: pd.DataFrame, pool: pd.DataFrame, config: MultiSourceScreeningConfig) -> pd.DataFrame:
    source_count = int(screening_input["source_family"].nunique())
    total_rows = int(len(screening_input))
    new_source_rows = int(screening_input[~screening_input["source_family"].eq("alpha158")]["screening_gate"].eq("strict_screening_input").sum())
    alpha_candidates = int(pool["role"].eq("alpha_candidate").sum())
    holdouts = int(pool["role"].eq("holdout").sum())
    required_columns_present = all(column in screening_input.columns for column in STANDARD_COLUMNS)
    rows = [
        {
            "check_id": "source_count",
            "status": "pass" if source_count >= config.min_sources else "blocked",
            "detail": f"sources={source_count}",
        },
        {
            "check_id": "total_screening_rows",
            "status": "pass" if total_rows >= config.min_total_rows else "blocked",
            "detail": f"rows={total_rows}",
        },
        {
            "check_id": "new_source_screening_rows",
            "status": "pass" if new_source_rows >= config.min_new_source_rows else "blocked",
            "detail": f"new_source_rows={new_source_rows}",
        },
        {
            "check_id": "standard_columns",
            "status": "pass" if required_columns_present else "blocked",
            "detail": f"columns={len(screening_input.columns)}",
        },
        {
            "check_id": "alpha_candidates_not_holdout",
            "status": "pass" if pool[pool["role"].eq("alpha_candidate")]["screening_gate"].eq("strict_screening_input").all() else "blocked",
            "detail": f"alpha_candidates={alpha_candidates}",
        },
        {
            "check_id": "holdout_visible",
            "status": "pass" if holdouts > 0 else "partial",
            "detail": f"holdouts={holdouts}",
        },
        {
            "check_id": "board_pool_alignment",
            "status": "pass" if set(board["factor"]) == set(pool["factor"]) else "blocked",
            "detail": f"board={len(board)}, pool={len(pool)}",
        },
    ]
    return pd.DataFrame(rows)


def write_report(
    output_dir: Path,
    screening_input: pd.DataFrame,
    board: pd.DataFrame,
    pool: pd.DataFrame,
    contract: pd.DataFrame,
    config: MultiSourceScreeningConfig,
) -> None:
    source_counts = (
        screening_input.groupby(["source_family", "screening_gate"]).size().reset_index(name="count")
        if not screening_input.empty
        else pd.DataFrame()
    )
    role_counts = pool.groupby(["source_family", "role"]).size().reset_index(name="count") if not pool.empty else pd.DataFrame()
    alpha = pool[pool["role"].eq("alpha_candidate")].copy()
    holdout = pool[pool["role"].eq("holdout")].copy()
    lines = [
        "# Multi-Source Screening V1",
        "",
        f"- Pool name: `{config.pool_name}`",
        "- Scope: screening contract only; no model training, no strategy optimization, no evaluator redefinition.",
        "- Sources: Alpha158 validated reference plus promoted TA, Alpha101, and Alpha360 catalogs.",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Source Counts",
        "",
        markdown_table(source_counts),
        "",
        "## Role Counts",
        "",
        markdown_table(role_counts),
        "",
        "## Alpha Candidates",
        "",
        markdown_table(alpha[["factor", "source_family", "role", "pool_reason", "primary_rank_ic"]].head(40) if not alpha.empty else pd.DataFrame()),
        "",
        "## Holdouts",
        "",
        markdown_table(holdout[["factor", "source_family", "promotion_reason", "alphalens_status", "jqfactor_status", "qlib_status"]].head(80) if not holdout.empty else pd.DataFrame()),
        "",
        "## Output Files",
        "",
        "- `multi_source_screening_input.csv`",
        "- `multi_source_candidate_board.csv`",
        "- `multi_source_candidate_pool.csv`",
        "- `multi_source_alpha_candidates.csv`",
        "- `multi_source_holdouts.csv`",
        "- `multi_source_contract_status.csv`",
        "- `multi_source_candidate_pool.json`",
    ]
    (output_dir / "multi_source_screening_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_multi_source_screening(config: MultiSourceScreeningConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    alpha_rows = build_alpha158_rows(config)
    ta_rows = build_ta_rows(config)
    alpha101_rows = build_alpha101_rows(config)
    alpha360_rows = build_alpha360_rows(config)
    screening_input = standardize_columns(
        pd.concat([alpha_rows, ta_rows, alpha101_rows, alpha360_rows], ignore_index=True, sort=False),
        config.pool_name,
    )
    board = build_candidate_board(screening_input)
    pool = board.copy()
    alpha = pool[pool["role"].eq("alpha_candidate")].copy()
    holdout = pool[pool["role"].eq("holdout")].copy()
    contract = build_contract_status(screening_input, board, pool, config)

    screening_input.to_csv(config.output_dir / "multi_source_screening_input.csv", index=False, encoding="utf-8-sig")
    board.to_csv(config.output_dir / "multi_source_candidate_board.csv", index=False, encoding="utf-8-sig")
    pool.to_csv(config.output_dir / "multi_source_candidate_pool.csv", index=False, encoding="utf-8-sig")
    alpha.to_csv(config.output_dir / "multi_source_alpha_candidates.csv", index=False, encoding="utf-8-sig")
    holdout.to_csv(config.output_dir / "multi_source_holdouts.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(config.output_dir / "multi_source_contract_status.csv", index=False, encoding="utf-8-sig")

    payload = {
        "pool_name": config.pool_name,
        "source_counts": screening_input.groupby("source_family").size().to_dict(),
        "role_counts": pool.groupby("role").size().to_dict(),
        "records": pool.where(pd.notna(pool), None).to_dict(orient="records"),
    }
    (config.output_dir / "multi_source_candidate_pool.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(config.output_dir, screening_input, board, pool, contract, config)
    return {
        "screening_input": screening_input,
        "candidate_board": board,
        "candidate_pool": pool,
        "alpha_candidates": alpha,
        "holdouts": holdout,
        "contract_status": contract,
    }
