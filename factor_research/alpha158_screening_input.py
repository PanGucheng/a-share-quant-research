from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd

from factor_research.catalog import FactorCatalogEntry, catalog_frame, load_factor_catalog
from factor_research.report import markdown_table


HORIZON_LABEL_RE = re.compile(r"label_(\d+)d", re.IGNORECASE)
PERIOD_RE = re.compile(r"period_(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Alpha158ScreeningInputConfig:
    first20_output_dir: Path
    first20_metric_index: Path
    remaining138_batch_root: Path
    remaining138_metric_index: Path
    all_catalog: Path
    runnable_catalog: Path
    holdout_catalog: Path
    promotion_audit: Path
    expression_summary: Path
    expression_validation_coverage: Path
    factor_frame: Path
    output_dir: Path
    correlation_enabled: bool = True
    correlation_max_dates: int | None = 120
    correlation_min_instruments: int = 100
    correlation_top_pairs: int = 100


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
        return f"{match.group(1)}D"
    match = HORIZON_LABEL_RE.search(text)
    if match:
        return f"{match.group(1)}D"
    if text.endswith("D"):
        return text
    return text


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def safe_float(value: object) -> float:
    result = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(result) if pd.notna(result) else np.nan


def batch_dirs(batch_root: Path) -> list[Path]:
    runs = batch_root / "runs"
    return sorted(path for path in runs.glob("batch_*") if path.is_dir())


def concat_from_batches(batch_root: Path, relative_path: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for batch_dir in batch_dirs(batch_root):
        frame = read_csv_or_empty(batch_dir / relative_path)
        if not frame.empty:
            frame.insert(0, "batch_id", batch_dir.name)
            frame.insert(1, "source_stage", "remaining138")
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_metric_index(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for source_stage, path in [
        ("first20", config.first20_metric_index),
        ("remaining138", config.remaining138_metric_index),
    ]:
        frame = read_csv_or_empty(path)
        if frame.empty:
            continue
        if "batch_id" not in frame.columns:
            frame.insert(0, "batch_id", f"{source_stage}_v4")
        frame.insert(0, "source_stage", source_stage)
        frame["raw_horizon"] = frame["horizon"]
        frame["horizon"] = frame["horizon"].map(normalize_horizon)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_evaluator_status(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    first20 = read_csv_or_empty(config.first20_output_dir / "evaluator_status.csv")
    if not first20.empty:
        first20.insert(0, "batch_id", "first20_v4")
        first20.insert(1, "source_stage", "first20")
    remaining = concat_from_batches(config.remaining138_batch_root, "evaluator_status.csv")
    frames = [frame for frame in [first20, remaining] if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_failure_reasons(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    first20 = read_csv_or_empty(config.first20_output_dir / "factor_failure_reasons.csv")
    if not first20.empty:
        first20.insert(0, "batch_id", "first20_v4")
        first20.insert(1, "source_stage", "first20")
    remaining = concat_from_batches(config.remaining138_batch_root, "factor_failure_reasons.csv")
    frames = [frame for frame in [first20, remaining] if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_context_status(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    first20 = read_csv_or_empty(config.first20_output_dir / "context" / "context_evaluator_status.csv")
    if not first20.empty:
        first20.insert(0, "batch_id", "first20_v4")
        first20.insert(1, "source_stage", "first20")
    remaining = concat_from_batches(config.remaining138_batch_root, "context/context_evaluator_status.csv")
    frames = [frame for frame in [first20, remaining] if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_catalog_metadata(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    all_entries = load_factor_catalog(config.all_catalog)
    runnable = {entry.name for entry in load_factor_catalog(config.runnable_catalog)}
    holdout = {entry.name for entry in load_factor_catalog(config.holdout_catalog)}
    frame = catalog_frame(all_entries)
    frame["strict_runnable"] = frame["name"].isin(runnable)
    frame["holdout"] = frame["name"].isin(holdout)
    frame["catalog_status"] = np.where(frame["strict_runnable"], "strict_runnable", "holdout_or_pending")
    return frame


def load_promotion_audit(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    audit = read_csv_or_empty(config.promotion_audit)
    if audit.empty:
        return audit
    audit = audit.rename(columns={"factor": "name"})
    return audit


def load_expression_coverage(config: Alpha158ScreeningInputConfig) -> pd.DataFrame:
    summary = read_csv_or_empty(config.expression_summary)
    validation = read_csv_or_empty(config.expression_validation_coverage)
    if summary.empty and validation.empty:
        return pd.DataFrame()
    if summary.empty:
        result = validation.copy()
        result["missing_rate"] = 1.0 - numeric_series(result, "coverage")
        return result
    result = summary.copy()
    if "missing_rate" not in result.columns:
        result["missing_rate"] = 1.0 - numeric_series(result, "coverage")
    if not validation.empty and "status" in validation.columns:
        result = result.merge(validation[["factor", "status"]], on="factor", how="left", suffixes=("", "_validation"))
        result = result.rename(columns={"status": "expression_validation_status"})
    return result


def status_rank(status: str) -> int:
    order = {
        "failed": 0,
        "not_run": 1,
        "partial_pass": 2,
        "skipped_non_informative": 3,
        "pass": 4,
    }
    return order.get(str(status), 1)


def aggregate_status(statuses: pd.DataFrame) -> pd.DataFrame:
    if statuses.empty:
        return pd.DataFrame()
    rows = []
    for (factor, system), group in statuses.groupby(["factor", "system"], dropna=False):
        values = [str(item) for item in group["status"].dropna().tolist()]
        worst = min(values, key=status_rank) if values else "not_run"
        rows.append(
            {
                "factor": factor,
                "system": system,
                "status": worst,
                "status_values": "|".join(sorted(set(values))),
                "failure_count": int(pd.to_numeric(group.get("failure_count", 0), errors="coerce").fillna(0).sum()),
                "output_file_count": int(pd.to_numeric(group.get("output_file_count", 0), errors="coerce").fillna(0).sum()),
            }
        )
    result = pd.DataFrame(rows)
    return result.pivot(index="factor", columns="system", values="status").reset_index().rename(
        columns={
            "alphalens_reloaded": "alphalens_status",
            "jqfactor_analyzer": "jqfactor_status",
            "qlib_eval": "qlib_status",
        }
    )


def aggregate_failures(failures: pd.DataFrame) -> pd.DataFrame:
    if failures.empty:
        return pd.DataFrame(columns=["factor", "failure_steps", "failure_systems"])
    rows = []
    for factor, group in failures.groupby("factor", dropna=False):
        rows.append(
            {
                "factor": factor,
                "failure_steps": ",".join(sorted(set(str(item) for item in group["step"].dropna()))),
                "failure_systems": ",".join(sorted(set(str(item) for item in group["system"].dropna()))),
            }
        )
    return pd.DataFrame(rows)


def aggregate_context_status(context_status: pd.DataFrame) -> pd.DataFrame:
    if context_status.empty:
        return pd.DataFrame(columns=["factor", "context_failed_count", "context_pass_count"])
    rows = []
    for factor, group in context_status.groupby("factor", dropna=False):
        statuses = group["status"].astype(str)
        rows.append(
            {
                "factor": factor,
                "context_failed_count": int((statuses == "failed").sum()),
                "context_pass_count": int((statuses == "pass").sum()),
                "context_skipped_non_informative_count": int((statuses == "skipped_non_informative").sum()),
            }
        )
    return pd.DataFrame(rows)


def status_output_dirs(statuses: pd.DataFrame, system: str) -> pd.DataFrame:
    if statuses.empty:
        return pd.DataFrame(columns=["factor", "output_dir"])
    rows = statuses[statuses["system"].eq(system)][["factor", "output_dir"]].dropna().drop_duplicates()
    return rows


def read_indexed_metric_file(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, index_col=0)


def summarize_information_coefficient(statuses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in statuses.itertuples(index=False):
        system = str(row.system)
        factor = str(row.factor)
        output_dir = Path(str(row.output_dir))
        if system in {"alphalens_reloaded", "jqfactor_analyzer"}:
            path = output_dir / "information_coefficient.csv"
            frame = read_csv_or_empty(path)
            if frame.empty:
                continue
            for column in frame.columns:
                if column == "date":
                    continue
                values = pd.to_numeric(frame[column], errors="coerce").dropna()
                if values.empty:
                    continue
                mean = float(values.mean())
                std = float(values.std(ddof=1))
                rows.append(
                    {
                        "system": system,
                        "factor": factor,
                        "horizon": normalize_horizon(column),
                        "rank_ic_mean": mean,
                        "rank_ic_std": std,
                        "rank_icir": mean / std if std else np.nan,
                        "rank_ic_win_rate": float((values > 0).mean()),
                        "rank_ic_count": int(len(values)),
                        "source_file": path.as_posix(),
                        "source_note": "Open-source factor_information_coefficient time series.",
                    }
                )
        elif system == "qlib_eval":
            for path in sorted(output_dir.glob("*_daily_rank_ic.csv")):
                frame = read_csv_or_empty(path)
                if frame.empty or "daily_rank_ic" not in frame.columns:
                    continue
                values = pd.to_numeric(frame["daily_rank_ic"], errors="coerce").dropna()
                if values.empty:
                    continue
                horizon = normalize_horizon(path.name.replace("_daily_rank_ic.csv", ""))
                mean = float(values.mean())
                std = float(values.std(ddof=1))
                rows.append(
                    {
                        "system": system,
                        "factor": factor,
                        "horizon": horizon,
                        "rank_ic_mean": mean,
                        "rank_ic_std": std,
                        "rank_icir": mean / std if std else np.nan,
                        "rank_ic_win_rate": float((values > 0).mean()),
                        "rank_ic_count": int(len(values)),
                        "source_file": path.as_posix(),
                        "source_note": "Qlib daily_rank_ic time series.",
                    }
                )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["system", "factor", "horizon"]).reset_index(drop=True)


def summarize_quantile_returns(statuses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in statuses.itertuples(index=False):
        system = str(row.system)
        if system not in {"alphalens_reloaded", "jqfactor_analyzer"}:
            continue
        factor = str(row.factor)
        output_dir = Path(str(row.output_dir))
        path = output_dir / "mean_return_by_quantile.csv"
        frame = read_csv_or_empty(path)
        if frame.empty or "factor_quantile" not in frame.columns:
            continue
        quantiles = pd.to_numeric(frame["factor_quantile"], errors="coerce")
        for column in frame.columns:
            if column == "factor_quantile":
                continue
            values = pd.to_numeric(frame[column], errors="coerce")
            valid = pd.DataFrame({"quantile": quantiles, "value": values}).dropna()
            if valid.empty:
                continue
            valid = valid.sort_values("quantile")
            q_low = float(valid.iloc[0]["value"])
            q_high = float(valid.iloc[-1]["value"])
            monotonicity = valid["quantile"].corr(valid["value"], method="spearman") if len(valid) >= 3 else np.nan
            rows.append(
                {
                    "system": system,
                    "factor": factor,
                    "horizon": normalize_horizon(column),
                    "quantile_count": int(len(valid)),
                    "bottom_quantile_return": q_low,
                    "top_quantile_return": q_high,
                    "top_bottom_spread": q_high - q_low,
                    "quantile_monotonicity_spearman": safe_float(monotonicity),
                    "source_file": path.as_posix(),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["system", "factor", "horizon"]).reset_index(drop=True)


def summarize_turnover(statuses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in statuses.itertuples(index=False):
        system = str(row.system)
        if system not in {"alphalens_reloaded", "jqfactor_analyzer"}:
            continue
        factor = str(row.factor)
        output_dir = Path(str(row.output_dir))
        path = output_dir / "quantile_turnover.csv"
        frame = read_csv_or_empty(path)
        if frame.empty:
            continue
        for column in frame.columns:
            if column == "date":
                continue
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if values.empty:
                continue
            rows.append(
                {
                    "system": system,
                    "factor": factor,
                    "turnover_window": str(column),
                    "turnover_mean": float(values.mean()),
                    "turnover_median": float(values.median()),
                    "turnover_count": int(len(values)),
                    "source_file": path.as_posix(),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["system", "factor", "turnover_window"]).reset_index(drop=True)


def summarize_rank_autocorrelation(statuses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in statuses.itertuples(index=False):
        system = str(row.system)
        if system not in {"alphalens_reloaded", "jqfactor_analyzer"}:
            continue
        factor = str(row.factor)
        output_dir = Path(str(row.output_dir))
        path = output_dir / "rank_autocorrelation.csv"
        frame = read_csv_or_empty(path)
        if frame.empty:
            continue
        for column in frame.columns:
            if column == "date":
                continue
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if values.empty:
                continue
            rows.append(
                {
                    "system": system,
                    "factor": factor,
                    "autocorr_window": str(column),
                    "rank_autocorr_mean": float(values.mean()),
                    "rank_autocorr_median": float(values.median()),
                    "rank_autocorr_count": int(len(values)),
                    "source_file": path.as_posix(),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["system", "factor", "autocorr_window"]).reset_index(drop=True)


def summarize_context_group_metrics(metric_index: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    context = metric_index[metric_index["scope"].eq("context")].copy()
    if context.empty:
        return pd.DataFrame(), pd.DataFrame()
    context["value"] = pd.to_numeric(context["value"], errors="coerce")
    ic_rows = context[context["metric"].eq("mean_information_coefficient_by_group")].dropna(subset=["value"])
    return_rows = context[context["metric"].eq("mean_return_by_quantile_by_group")].dropna(subset=["value"])

    ic_summary = pd.DataFrame()
    if not ic_rows.empty:
        rows = []
        for key, group in ic_rows.groupby(["system", "factor", "return_mode", "group_dimension", "horizon"], dropna=False):
            group = group.copy()
            min_row = group.loc[group["value"].idxmin()]
            max_row = group.loc[group["value"].idxmax()]
            rows.append(
                {
                    "system": key[0],
                    "factor": key[1],
                    "return_mode": key[2],
                    "group_dimension": key[3],
                    "horizon": key[4],
                    "group_count": int(group["group"].nunique()),
                    "mean_group_rank_ic": float(group["value"].mean()),
                    "min_group_rank_ic": float(min_row["value"]),
                    "min_group": min_row["group"],
                    "max_group_rank_ic": float(max_row["value"]),
                    "max_group": max_row["group"],
                }
            )
        ic_summary = pd.DataFrame(rows)

    return_summary = pd.DataFrame()
    if not return_rows.empty:
        rows = []
        group_cols = ["system", "factor", "return_mode", "group_dimension", "group", "horizon"]
        for key, group in return_rows.groupby(group_cols, dropna=False):
            values = group.copy()
            values["quantile"] = pd.to_numeric(values["quantile"], errors="coerce")
            values = values.dropna(subset=["quantile", "value"]).sort_values("quantile")
            if values.empty:
                continue
            monotonicity = values["quantile"].corr(values["value"], method="spearman") if len(values) >= 3 else np.nan
            rows.append(
                {
                    "system": key[0],
                    "factor": key[1],
                    "return_mode": key[2],
                    "group_dimension": key[3],
                    "group": key[4],
                    "horizon": key[5],
                    "quantile_count": int(len(values)),
                    "bottom_quantile_return": float(values.iloc[0]["value"]),
                    "top_quantile_return": float(values.iloc[-1]["value"]),
                    "top_bottom_spread": float(values.iloc[-1]["value"] - values.iloc[0]["value"]),
                    "quantile_monotonicity_spearman": safe_float(monotonicity),
                }
            )
        return_summary = pd.DataFrame(rows)
    return ic_summary, return_summary


def select_dates(dates: list[pd.Timestamp], max_dates: int | None) -> list[pd.Timestamp]:
    if max_dates is None or max_dates <= 0 or len(dates) <= max_dates:
        return dates
    indexes = np.linspace(0, len(dates) - 1, max_dates).round().astype(int)
    return [dates[index] for index in sorted(set(indexes.tolist()))]


def daily_cross_section_spearman(
    factor_frame_path: Path,
    factors: list[str],
    *,
    max_dates: int | None,
    min_instruments: int,
    top_pairs: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if not factor_frame_path.exists():
        return pd.DataFrame(), pd.DataFrame(), {"enabled": False, "reason": "missing_factor_frame"}
    frame = pd.read_pickle(factor_frame_path)
    if "datetime" not in frame.columns:
        return pd.DataFrame(), pd.DataFrame(), {"enabled": False, "reason": "missing_datetime"}
    available = [factor for factor in factors if factor in frame.columns]
    if len(available) < 2:
        return pd.DataFrame(), pd.DataFrame(), {"enabled": False, "reason": "not_enough_factors"}
    frame = frame[["datetime", *available]].copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    dates = select_dates(sorted(frame["datetime"].dropna().unique().tolist()), max_dates)
    if not dates:
        return pd.DataFrame(), pd.DataFrame(), {"enabled": False, "reason": "no_dates"}
    frame = frame[frame["datetime"].isin(dates)]

    n = len(available)
    corr_sum = np.zeros((n, n), dtype="float64")
    corr_count = np.zeros((n, n), dtype="int32")
    used_dates = 0
    for _, group in frame.groupby("datetime", sort=True):
        if len(group) < min_instruments:
            continue
        corr = group[available].corr(method="spearman", min_periods=min_instruments)
        arr = corr.to_numpy(dtype="float64")
        mask = ~np.isnan(arr)
        corr_sum[mask] += arr[mask]
        corr_count[mask] += 1
        used_dates += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_corr = corr_sum / corr_count
    np.fill_diagonal(mean_corr, np.nan)

    factor_rows = []
    pair_rows = []
    for i, factor in enumerate(available):
        row = mean_corr[i, :]
        valid = np.where(~np.isnan(row))[0]
        if len(valid) == 0:
            factor_rows.append({"factor": factor, "strongest_corr_factor": "", "strongest_corr": np.nan, "strongest_abs_corr": np.nan})
            continue
        strongest_index = valid[np.argmax(np.abs(row[valid]))]
        factor_rows.append(
            {
                "factor": factor,
                "strongest_corr_factor": available[strongest_index],
                "strongest_corr": float(row[strongest_index]),
                "strongest_abs_corr": float(abs(row[strongest_index])),
            }
        )
    for i in range(n):
        for j in range(i + 1, n):
            value = mean_corr[i, j]
            if np.isnan(value):
                continue
            pair_rows.append(
                {
                    "factor_a": available[i],
                    "factor_b": available[j],
                    "mean_daily_spearman_corr": float(value),
                    "abs_mean_daily_spearman_corr": float(abs(value)),
                    "date_count": int(corr_count[i, j]),
                }
            )
    factor_summary = pd.DataFrame(factor_rows)
    pair_summary = pd.DataFrame(pair_rows)
    if not pair_summary.empty:
        pair_summary = pair_summary.sort_values("abs_mean_daily_spearman_corr", ascending=False).head(top_pairs)
    meta = {
        "enabled": True,
        "method": "daily_cross_section_spearman_mean",
        "available_factor_count": len(available),
        "candidate_date_count": len(dates),
        "used_date_count": used_dates,
        "min_instruments": min_instruments,
    }
    return factor_summary, pair_summary, meta


def pivot_metric(
    board: pd.DataFrame,
    source: pd.DataFrame,
    *,
    system: str,
    value_column: str,
    output_prefix: str,
    index_column: str = "horizon",
) -> pd.DataFrame:
    if source.empty:
        return board
    subset = source[source["system"].eq(system)].copy()
    if subset.empty:
        return board
    pivot = subset.pivot_table(index="factor", columns=index_column, values=value_column, aggfunc="first")
    pivot = pivot.rename(columns={column: f"{output_prefix}_{str(column).lower()}" for column in pivot.columns})
    return board.merge(pivot.reset_index(), on="factor", how="left")


def build_factor_board(
    catalog: pd.DataFrame,
    audit: pd.DataFrame,
    coverage: pd.DataFrame,
    statuses: pd.DataFrame,
    failures: pd.DataFrame,
    context_status: pd.DataFrame,
    ic_summary: pd.DataFrame,
    quantile_summary: pd.DataFrame,
    turnover: pd.DataFrame,
    rank_autocorr: pd.DataFrame,
    context_ic: pd.DataFrame,
    correlation_summary: pd.DataFrame,
) -> pd.DataFrame:
    board = catalog.rename(columns={"name": "factor"})[
        [
            "factor",
            "registry_name",
            "category",
            "stage",
            "enabled",
            "runnable",
            "strict_runnable",
            "holdout",
            "catalog_status",
            "expected_direction",
            "source_project",
            "license",
            "compute_adapter",
        ]
    ].copy()
    if not audit.empty:
        board = board.merge(
            audit[["name", "promotable", "holdout_reason"]].rename(columns={"name": "factor"}),
            on="factor",
            how="left",
        )
    if not coverage.empty:
        keep = ["factor", "valid_rows", "total_rows", "coverage", "missing_rate"]
        if "expression_validation_status" in coverage.columns:
            keep.append("expression_validation_status")
        board = board.merge(coverage[keep], on="factor", how="left")
    board = board.merge(aggregate_status(statuses), on="factor", how="left")
    board = board.merge(aggregate_failures(failures), on="factor", how="left")
    board = board.merge(aggregate_context_status(context_status), on="factor", how="left")

    for system, prefix in [
        ("alphalens_reloaded", "alphalens_rank_ic"),
        ("jqfactor_analyzer", "jqfactor_rank_ic"),
        ("qlib_eval", "qlib_rank_ic"),
    ]:
        board = pivot_metric(board, ic_summary, system=system, value_column="rank_ic_mean", output_prefix=prefix)
        board = pivot_metric(board, ic_summary, system=system, value_column="rank_icir", output_prefix=f"{prefix}ir")
        board = pivot_metric(board, ic_summary, system=system, value_column="rank_ic_win_rate", output_prefix=f"{prefix}_win_rate")

    for system, prefix in [
        ("alphalens_reloaded", "alphalens"),
        ("jqfactor_analyzer", "jqfactor"),
    ]:
        board = pivot_metric(
            board,
            quantile_summary,
            system=system,
            value_column="top_bottom_spread",
            output_prefix=f"{prefix}_quantile_spread",
        )
        board = pivot_metric(
            board,
            quantile_summary,
            system=system,
            value_column="quantile_monotonicity_spearman",
            output_prefix=f"{prefix}_monotonicity",
        )
        board = pivot_metric(
            board,
            turnover,
            system=system,
            value_column="turnover_mean",
            output_prefix=f"{prefix}_turnover_mean",
            index_column="turnover_window",
        )
        board = pivot_metric(
            board,
            rank_autocorr,
            system=system,
            value_column="rank_autocorr_mean",
            output_prefix=f"{prefix}_rank_autocorr_mean",
            index_column="autocorr_window",
        )

    qlib_metrics = extract_qlib_metrics_from_ic_source(statuses)
    if not qlib_metrics.empty:
        for metric_name in ["mean", "std", "annualized_return", "information_ratio", "max_drawdown"]:
            subset = qlib_metrics[qlib_metrics["metric"].eq(metric_name)]
            board = pivot_metric(
                board,
                subset,
                system="qlib_eval",
                value_column="value",
                output_prefix=f"qlib_{metric_name}",
            )

    if not context_ic.empty:
        context_key = context_ic[
            (context_ic["system"].eq("alphalens_reloaded"))
            & (context_ic["return_mode"].eq("raw_return"))
            & (context_ic["group_dimension"].eq("index_segment"))
        ].copy()
        if not context_key.empty:
            board = pivot_metric(
                board,
                context_key,
                system="alphalens_reloaded",
                value_column="min_group_rank_ic",
                output_prefix="context_raw_index_segment_min_rank_ic",
            )
            board = pivot_metric(
                board,
                context_key,
                system="alphalens_reloaded",
                value_column="mean_group_rank_ic",
                output_prefix="context_raw_index_segment_mean_rank_ic",
            )

    if not correlation_summary.empty:
        board = board.merge(correlation_summary, on="factor", how="left")

    board["alphalens_status"] = board.get("alphalens_status", pd.Series(index=board.index, dtype=object)).fillna("not_run")
    board["jqfactor_status"] = board.get("jqfactor_status", pd.Series(index=board.index, dtype=object)).fillna("not_run")
    board["qlib_status"] = board.get("qlib_status", pd.Series(index=board.index, dtype=object)).fillna("not_run")
    board["context_failed_count"] = pd.to_numeric(board.get("context_failed_count", 0), errors="coerce").fillna(0).astype(int)
    board["evaluation_gate"] = board.apply(evaluation_gate, axis=1)
    board["metric_judgement_policy"] = "raw_open_source_metrics_coexist_no_combined_score"
    return board.sort_values(["evaluation_gate", "category", "factor"]).reset_index(drop=True)


def extract_qlib_metrics_from_ic_source(statuses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    qlib_rows = statuses[statuses["system"].eq("qlib_eval")]
    for row in qlib_rows.itertuples(index=False):
        factor = str(row.factor)
        output_dir = Path(str(row.output_dir))
        for path in sorted(output_dir.glob("*_risk_analysis.csv")):
            horizon = normalize_horizon(path.name.replace("_risk_analysis.csv", ""))
            frame = read_indexed_metric_file(path)
            if frame.empty:
                continue
            for metric_name, values in frame.iterrows():
                value = pd.to_numeric(values.iloc[0], errors="coerce")
                if pd.isna(value):
                    continue
                rows.append(
                    {
                        "system": "qlib_eval",
                        "factor": factor,
                        "horizon": horizon,
                        "metric": str(metric_name),
                        "value": float(value),
                        "source_file": path.as_posix(),
                    }
                )
    return pd.DataFrame(rows)


def evaluation_gate(row: pd.Series) -> str:
    if bool(row.get("holdout", False)):
        return "holdout"
    if (
        str(row.get("alphalens_status")) == "pass"
        and str(row.get("qlib_status")) == "pass"
        and str(row.get("jqfactor_status")) in {"pass", "partial_pass"}
        and int(row.get("context_failed_count", 0)) == 0
        and bool(row.get("strict_runnable", False))
    ):
        return "strict_screening_input"
    return "review"


def write_screening_report(
    output_dir: Path,
    board: pd.DataFrame,
    metric_index: pd.DataFrame,
    ic_summary: pd.DataFrame,
    quantile_summary: pd.DataFrame,
    turnover: pd.DataFrame,
    rank_autocorr: pd.DataFrame,
    context_ic: pd.DataFrame,
    context_returns: pd.DataFrame,
    correlation_pairs: pd.DataFrame,
    correlation_meta: dict,
) -> None:
    gate_counts = board.groupby("evaluation_gate").size().reset_index(name="count") if not board.empty else pd.DataFrame()
    status_counts = (
        board.groupby(["alphalens_status", "jqfactor_status", "qlib_status"]).size().reset_index(name="count")
        if not board.empty
        else pd.DataFrame()
    )
    holdouts = (
        board[board["evaluation_gate"].eq("holdout")][["factor", "category", "holdout_reason", "failure_steps"]]
        if not board.empty
        else pd.DataFrame()
    )
    top_ic = top_abs_ic_view(board)
    top_corr = correlation_pairs.head(20) if not correlation_pairs.empty else pd.DataFrame()
    lines = [
        "# Alpha158 Full Screening Input V1",
        "",
        "This report builds a screening input layer from existing Alpha158 evaluation outputs.",
        "It does not create a custom combined score and does not train a model.",
        "",
        "## Output Rows",
        "",
        f"- Metric index rows: `{len(metric_index)}`",
        f"- Factor board rows: `{len(board)}`",
        f"- IC summary rows: `{len(ic_summary)}`",
        f"- Quantile return summary rows: `{len(quantile_summary)}`",
        f"- Turnover summary rows: `{len(turnover)}`",
        f"- Rank autocorrelation summary rows: `{len(rank_autocorr)}`",
        f"- Context IC summary rows: `{len(context_ic)}`",
        f"- Context return summary rows: `{len(context_returns)}`",
        "",
        "## Evaluation Gate",
        "",
        markdown_table(gate_counts),
        "",
        "## Evaluator Status Combinations",
        "",
        markdown_table(status_counts),
        "",
        "## Holdouts",
        "",
        markdown_table(holdouts),
        "",
        "## Top Absolute Rank IC Snapshot",
        "",
        markdown_table(top_ic),
        "",
        "## Top Correlation Pairs",
        "",
        markdown_table(top_corr),
        "",
        "## Correlation Metadata",
        "",
        markdown_table(pd.DataFrame([correlation_meta])),
        "",
        "## Output Files",
        "",
        "- `alpha158_full_metric_index.csv`",
        "- `alpha158_factor_screening_input.csv`",
        "- `alpha158_ic_timeseries_summary.csv`",
        "- `alpha158_quantile_return_summary.csv`",
        "- `alpha158_turnover_summary.csv`",
        "- `alpha158_rank_autocorrelation_summary.csv`",
        "- `alpha158_context_group_ic_summary.csv`",
        "- `alpha158_context_group_return_summary.csv`",
        "- `alpha158_factor_correlation_summary.csv`",
        "- `alpha158_factor_correlation_top_pairs.csv`",
        "",
        "## Notes",
        "",
        "- Alphalens `factor_information_coefficient` is treated as Rank IC because Alphalens uses Spearman rank correlation for this metric.",
        "- ICIR is derived from the evaluator time series as mean divided by sample standard deviation.",
        "- jqfactor_analyzer partial-pass is preserved as source status instead of being rewritten.",
        "- Context metrics reuse the existing factor context/tradability-aware outputs.",
        "- The factor board is a screening input, not an investment recommendation.",
    ]
    (output_dir / "alpha158_full_screening_input_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def top_abs_ic_view(board: pd.DataFrame) -> pd.DataFrame:
    if board.empty:
        return pd.DataFrame()
    rank_ic_column = re.compile(r"^(alphalens|jqfactor|qlib)_rank_ic_\d+d$")
    candidate_columns = [
        column
        for column in board.columns
        if rank_ic_column.match(column)
    ]
    rows = []
    for column in candidate_columns:
        temp = board[["factor", "category", "evaluation_gate", column]].copy()
        temp = temp.rename(columns={column: "rank_ic"})
        temp["metric"] = column
        temp["abs_rank_ic"] = pd.to_numeric(temp["rank_ic"], errors="coerce").abs()
        rows.append(temp)
    if not rows:
        return pd.DataFrame()
    result = pd.concat(rows, ignore_index=True).dropna(subset=["abs_rank_ic"])
    return result.sort_values("abs_rank_ic", ascending=False)[
        ["factor", "category", "evaluation_gate", "metric", "rank_ic"]
    ].head(30)


def run_screening_input(config: Alpha158ScreeningInputConfig) -> dict[str, pd.DataFrame | dict]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    metric_index = load_metric_index(config)
    statuses = load_evaluator_status(config)
    failures = load_failure_reasons(config)
    context_status = load_context_status(config)
    catalog = load_catalog_metadata(config)
    audit = load_promotion_audit(config)
    coverage = load_expression_coverage(config)

    ic_summary = summarize_information_coefficient(statuses)
    quantile_summary = summarize_quantile_returns(statuses)
    turnover = summarize_turnover(statuses)
    rank_autocorr = summarize_rank_autocorrelation(statuses)
    context_ic, context_returns = summarize_context_group_metrics(metric_index)

    if config.correlation_enabled:
        factors = catalog["name"].tolist()
        corr_summary, corr_pairs, corr_meta = daily_cross_section_spearman(
            config.factor_frame,
            factors,
            max_dates=config.correlation_max_dates,
            min_instruments=config.correlation_min_instruments,
            top_pairs=config.correlation_top_pairs,
        )
    else:
        corr_summary, corr_pairs, corr_meta = pd.DataFrame(), pd.DataFrame(), {"enabled": False}

    board = build_factor_board(
        catalog,
        audit,
        coverage,
        statuses,
        failures,
        context_status,
        ic_summary,
        quantile_summary,
        turnover,
        rank_autocorr,
        context_ic,
        corr_summary,
    )

    outputs: dict[str, pd.DataFrame | dict] = {
        "metric_index": metric_index,
        "statuses": statuses,
        "failures": failures,
        "ic_summary": ic_summary,
        "quantile_summary": quantile_summary,
        "turnover": turnover,
        "rank_autocorr": rank_autocorr,
        "context_ic": context_ic,
        "context_returns": context_returns,
        "correlation_summary": corr_summary,
        "correlation_pairs": corr_pairs,
        "correlation_meta": corr_meta,
        "board": board,
    }
    write_outputs(config.output_dir, outputs)
    write_screening_report(
        config.output_dir,
        board,
        metric_index,
        ic_summary,
        quantile_summary,
        turnover,
        rank_autocorr,
        context_ic,
        context_returns,
        corr_pairs,
        corr_meta,
    )
    return outputs


def write_outputs(output_dir: Path, outputs: dict[str, pd.DataFrame | dict]) -> None:
    file_map = {
        "metric_index": "alpha158_full_metric_index.csv",
        "statuses": "alpha158_evaluator_status.csv",
        "failures": "alpha158_failure_reasons.csv",
        "ic_summary": "alpha158_ic_timeseries_summary.csv",
        "quantile_summary": "alpha158_quantile_return_summary.csv",
        "turnover": "alpha158_turnover_summary.csv",
        "rank_autocorr": "alpha158_rank_autocorrelation_summary.csv",
        "context_ic": "alpha158_context_group_ic_summary.csv",
        "context_returns": "alpha158_context_group_return_summary.csv",
        "correlation_summary": "alpha158_factor_correlation_summary.csv",
        "correlation_pairs": "alpha158_factor_correlation_top_pairs.csv",
        "board": "alpha158_factor_screening_input.csv",
    }
    for key, filename in file_map.items():
        value = outputs.get(key)
        if isinstance(value, pd.DataFrame):
            value.to_csv(output_dir / filename, index=False, encoding="utf-8-sig")
    meta = outputs.get("correlation_meta")
    if isinstance(meta, dict):
        pd.DataFrame([meta]).to_csv(output_dir / "alpha158_factor_correlation_meta.csv", index=False, encoding="utf-8-sig")
