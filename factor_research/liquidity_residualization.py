"""Liquidity residualization helpers for V3.39.

Reusable functions for:
- loading factor frames and merging tradability labels
- daily cross-sectional liquidity/tradability OLS residualization
- per-factor summary
- daily diagnostics
- raw-vs-residualized comparison
- candidate action decisions
- contract status

Uses suffix ``__resid_liquidity``; never overwrites raw factor columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from factor_research.preprocess import (
    cross_sectional_zscore,
    numeric_series,
    winsorize_mad,
)
from factor_research.diagnostics import (
    attach_tradability,
    load_tradability_labels,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_PROXIES = ["liquidity_value", "liquidity_bucket", "tradability_score"]
DEFAULT_SUFFIX = "__resid_liquidity"
DEFAULT_MIN_COUNT = 50
DEFAULT_LABELS = ["label_10d_t1", "label_20d_t1"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def read_attribution_board(path: Path) -> pd.DataFrame:
    """Read the tradability exposure attribution board CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Missing attribution board: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("Attribution board is empty")
    if "factor" not in df.columns:
        raise ValueError("Attribution board missing 'factor' column")
    return df


def load_factor_frame(path: Path) -> pd.DataFrame:
    """Load a single factor frame pickle or CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Missing factor frame: {path}")
    if path.suffix.lower() in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    return pd.read_csv(path, parse_dates=["datetime"])


def merge_factor_frames(
    *frame_paths: Path,
    factor_list: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Merge multiple factor frames on (datetime, instrument).

    If *factor_list* is provided only those factor columns are kept;
    otherwise all non-key columns from every frame are kept.
    """
    parts: list[pd.DataFrame] = []
    key_cols = {"datetime", "instrument"}

    for path in frame_paths:
        if not path.exists():
            continue
        frame = load_factor_frame(path)
        # Convert instrument to upper string for consistent merging
        if "instrument" in frame.columns:
            frame["instrument"] = frame["instrument"].astype(str).str.upper()

        if factor_list:
            keep = [c for c in factor_list if c in frame.columns]
            if not keep:
                continue
            cols = [c for c in ["datetime", "instrument"] + keep if c in frame.columns]
            # Also keep label columns if present
            for label_col in DEFAULT_LABELS:
                if label_col in frame.columns and label_col not in cols:
                    cols.append(label_col)
            parts.append(frame[cols].copy())
        else:
            parts.append(frame.copy())

    if not parts:
        raise ValueError("No factor frames contain any requested factors")

    # Merge sequentially on datetime+instrument
    result = parts[0]
    for part in parts[1:]:
        result = result.merge(part, on=["datetime", "instrument"], how="outer")
    return result


def find_label_frame(cache_dir: Path) -> Optional[pd.DataFrame]:
    """Scan feature cache directory for a frame containing label columns.

    Returns the first frame with any of DEFAULT_LABELS present, or None
    if no suitable file is found.  Handles both flat DataFrames and
    MultiIndex (datetime, instrument) Qlib-style feature frames.
    """
    if not cache_dir.exists():
        return None
    for pkl in sorted(cache_dir.glob("features_*.pkl")):
        try:
            df = pd.read_pickle(pkl)
        except Exception:
            continue

        # Check whether labels are in columns
        label_cols = [l for l in DEFAULT_LABELS if l in df.columns]
        if not label_cols:
            continue

        # If datetime / instrument are index levels, reset them to columns
        has_dt = "datetime" in df.columns
        has_instr = "instrument" in df.columns
        if not has_dt or not has_instr:
            index_names = df.index.names if hasattr(df.index, "names") else []
            if "datetime" in index_names or "instrument" in index_names:
                df = df.reset_index()

        cols = ["datetime", "instrument"] + label_cols
        available = [c for c in cols if c in df.columns]
        return df[available].copy()
    return None


# ---------------------------------------------------------------------------
# Tradability merge
# ---------------------------------------------------------------------------
def merge_tradability(
    frame: pd.DataFrame,
    tradability_dir: Path,
) -> pd.DataFrame:
    """Attach tradability labels (liquidity_value, liquidity_bucket, tradability_score, etc.) to *frame*.

    Normalises datetime to date-only before merging so that factor frames
    (which may carry a time-of-day component) can join against tradability
    labels (which are date-only).
    """
    # Normalise frame datetime to date-only
    if "datetime" in frame.columns:
        frame = frame.copy()
        frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.normalize()

    labels = load_tradability_labels(tradability_dir)

    # load_tradability_labels does not return liquidity_value, so load it
    # separately from the same CSV.
    labels_path = tradability_dir / "tradability_labels.csv"
    if "liquidity_value" not in labels.columns and labels_path.exists():
        lv = pd.read_csv(
            labels_path,
            usecols=["datetime", "instrument", "liquidity_value"],
            parse_dates=["datetime"],
        )
        lv["instrument"] = lv["instrument"].astype(str).str.upper()
        lv["liquidity_value"] = pd.to_numeric(lv["liquidity_value"], errors="coerce")
        labels = labels.merge(lv, on=["datetime", "instrument"], how="left")

    # Also normalise labels datetime to be safe
    if "datetime" in labels.columns:
        labels = labels.copy()
        labels["datetime"] = pd.to_datetime(labels["datetime"]).dt.normalize()

    result = attach_tradability(frame, labels)
    # Ensure proxy columns are numeric
    for proxy in DEFAULT_PROXIES:
        if proxy in result.columns:
            result[proxy] = numeric_series(result[proxy])
    return result


# ---------------------------------------------------------------------------
# Daily cross-sectional residualization
# ---------------------------------------------------------------------------
def residualize_daily(
    frame: pd.DataFrame,
    factor: str,
    proxies: Optional[list[str]] = None,
    min_count: int = DEFAULT_MIN_COUNT,
    suffix: str = DEFAULT_SUFFIX,
    zscore_clip: float = 3.0,
) -> pd.Series:
    """Daily cross-sectional OLS residualization of *factor* against liquidity *proxies*.

    1. For each trading day, winsorize (MAD, 4.5 sigma) and robust-zscore (clip +/-3) the factor and
       each proxy.
    2. Regress factor_z = intercept + sum(proxy_z) via numpy lstsq.
    3. Return the residual series named ``<factor><suffix>``.

    Days with fewer than *min_count* complete observations are set to NaN.
    """
    if proxies is None:
        proxies = DEFAULT_PROXIES
    resid_col = f"{factor}{suffix}"

    # Work on a minimal subset
    cols = [factor] + [p for p in proxies if p in frame.columns]
    if len(cols) <= 1:
        return pd.Series(np.nan, index=frame.index, name=resid_col)
    work = frame[cols].copy()
    for c in cols:
        work[c] = numeric_series(work[c])

    # Proxy columns actually present
    present_proxies = [p for p in proxies if p in work.columns]
    if not present_proxies:
        return pd.Series(np.nan, index=frame.index, name=resid_col)

    results: list[pd.Series] = []
    for _, group in work.groupby(level=0, sort=True):
        # Valid mask: factor and ALL present proxies non-NaN
        valid = group[factor].notna()
        for p in present_proxies:
            valid &= group[p].notna()
        if valid.sum() < min_count:
            results.append(pd.Series(np.nan, index=group.index, name=resid_col))
            continue

        gv = group.loc[valid].copy()

        # Winsorize + z-score factor
        factor_w = winsorize_mad(gv[factor])
        gv["__fz"] = cross_sectional_zscore(factor_w, robust=True, clip=zscore_clip)

        # Winsorize + z-score each present proxy; drop any that are constant
        # (all-NaN z-score) because a constant proxy contributes no information.
        z_cols: list[str] = []
        for p in present_proxies:
            pz = f"__{p}_z"
            pw = winsorize_mad(gv[p])
            zs = cross_sectional_zscore(pw, robust=True, clip=zscore_clip)
            if zs.notna().sum() == 0:
                continue   # constant proxy -- drop it
            gv[pz] = zs
            z_cols.append(pz)

        # Require at least one proxy with variance and a valid factor z-score
        if not z_cols or gv["__fz"].notna().sum() == 0:
            results.append(pd.Series(np.nan, index=group.index, name=resid_col))
            continue

        # Build design matrix X with intercept
        X = gv[z_cols].to_numpy(dtype=float)
        y = gv["__fz"].to_numpy(dtype=float)
        Xc = np.column_stack([np.ones(len(y)), X])

        # Guard against NaN/Inf in design matrix (from scale=0 z-scores)
        if not np.all(np.isfinite(Xc)) or not np.all(np.isfinite(y)):
            results.append(pd.Series(np.nan, index=group.index, name=resid_col))
            continue

        try:
            beta = np.linalg.lstsq(Xc, y, rcond=None)[0]
            fitted = Xc @ beta
            residuals = y - fitted
        except np.linalg.LinAlgError:
            results.append(pd.Series(np.nan, index=group.index, name=resid_col))
            continue

        res = pd.Series(np.nan, index=group.index, name=resid_col)
        res.loc[valid] = residuals
        results.append(res)

    if not results:
        return pd.Series(np.nan, index=frame.index, name=resid_col)
    return pd.concat(results).sort_index()


def build_residualized_factor_frame(
    frame: pd.DataFrame,
    factors: list[str],
    proxies: Optional[list[str]] = None,
    min_count: int = DEFAULT_MIN_COUNT,
    suffix: str = DEFAULT_SUFFIX,
) -> pd.DataFrame:
    """Add ``<factor>__resid_liquidity`` columns to *frame* for every *factor*.

    Uses datetime as index for fast groupby and positional column assignment
    (avoiding pandas duplicate-label index alignment issues), then restores a
    default RangeIndex.
    """
    result = frame.copy()
    if "datetime" not in result.columns:
        raise ValueError("frame must contain 'datetime' column")

    # Index by datetime so residualize_daily can groupby(level=0).
    # Sort by the datetime index so that residualize_daily's internal
    # sort_index produces the same row ordering, allowing safe positional
    # (values-based) assignment.
    result = result.set_index("datetime", drop=False)
    result.index.name = "dt"
    result = result.sort_index()

    for factor in factors:
        if factor not in result.columns:
            continue
        resid = residualize_daily(result, factor, proxies=proxies, min_count=min_count, suffix=suffix)
        # Positional assignment: both result and resid are sorted by datetime
        # index, so .values safely aligns without pandas duplicate-label issues.
        result[resid.name] = resid.values

    # Restore default integer index for downstream consumers
    result = result.reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# Daily diagnostics
# ---------------------------------------------------------------------------
def compute_daily_diagnostics(
    frame: pd.DataFrame,
    factors: list[str],
    proxies: Optional[list[str]] = None,
    suffix: str = DEFAULT_SUFFIX,
) -> pd.DataFrame:
    """Compute per-day, per-factor residualization diagnostics.

    Columns: datetime, factor, n_total, n_valid, coverage, corr_raw_residual,
    r2_approx, var_factor_z, var_residual_z.

    R^2 is computed in z-score / regression space (var of z-scored residual
    vs var of z-scored factor), NOT from raw-factor original-unit variance.
    """
    if proxies is None:
        proxies = DEFAULT_PROXIES
    rows: list[dict] = []

    for factor in factors:
        resid_col = f"{factor}{suffix}"
        if factor not in frame.columns or resid_col not in frame.columns:
            continue
        for dt, group in frame.groupby("datetime", sort=True):
            valid = group[[factor, resid_col]].notna().all(axis=1)
            n_valid = int(valid.sum())
            if n_valid < 2:
                continue
            n_total = len(group)
            coverage = n_valid / n_total
            raw = numeric_series(group.loc[valid, factor])
            resid = numeric_series(group.loc[valid, resid_col])
            corr_raw_resid = float(raw.corr(resid)) if n_valid > 2 else float("nan")
            # R^2 in z-score space: winsorize + z-score the factor to match
            # the regression domain, then compare with residual variance.
            factor_w = winsorize_mad(raw)
            factor_z = cross_sectional_zscore(factor_w, robust=True, clip=3.0)
            valid_z = factor_z.notna()
            if valid_z.sum() < 2:
                r2 = float("nan")
                var_fz = float("nan")
                var_rz = float("nan")
            else:
                var_fz = float(factor_z.loc[valid_z].var())
                var_rz = float(resid.loc[valid_z].var())
                r2 = 1.0 - var_rz / var_fz if var_fz > 1e-15 else float("nan")
            rows.append({
                "datetime": dt,
                "factor": factor,
                "n_total": n_total,
                "n_valid": n_valid,
                "coverage": coverage,
                "corr_raw_residual": corr_raw_resid,
                "r2_approx": r2,
                "var_factor_z": var_fz,
                "var_residual_z": var_rz,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Factor-level summary
# ---------------------------------------------------------------------------
def compute_residualized_factor_summary(
    frame: pd.DataFrame,
    factors: list[str],
    suffix: str = DEFAULT_SUFFIX,
) -> pd.DataFrame:
    """Per-factor coverage and row-count summary."""
    rows: list[dict] = []
    total = len(frame)
    for factor in factors:
        resid_col = f"{factor}{suffix}"
        raw_valid = int(frame[factor].notna().sum()) if factor in frame.columns else 0
        resid_valid = int(frame[resid_col].notna().sum()) if resid_col in frame.columns else 0
        rows.append({
            "factor": factor,
            "residualized_factor": resid_col,
            "raw_coverage": raw_valid / total if total else 0.0,
            "residualized_coverage": resid_valid / total if total else 0.0,
            "n_raw_valid_rows": raw_valid,
            "n_residualized_valid_rows": resid_valid,
            "n_total_rows": total,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# IC computation (lightweight, no external evaluator required)
# ---------------------------------------------------------------------------
def _daily_ic(
    frame: pd.DataFrame,
    factor_col: str,
    label: str,
    min_count: int = DEFAULT_MIN_COUNT,
) -> pd.DataFrame:
    """Compute daily Pearson IC and Spearman Rank IC for one factor-label pair."""
    if factor_col not in frame.columns or label not in frame.columns:
        return pd.DataFrame()
    rows: list[dict] = []
    for dt, group in frame.groupby("datetime", sort=True):
        fv = numeric_series(group[factor_col])
        lv = numeric_series(group[label])
        valid = fv.notna() & lv.notna()
        n = int(valid.sum())
        if n < min_count:
            continue
        x = fv.loc[valid]
        y = lv.loc[valid]
        rows.append({
            "datetime": dt,
            "ic": float(x.corr(y, method="pearson")),
            "rank_ic": float(x.corr(y, method="spearman")),
            "count": n,
        })
    return pd.DataFrame(rows)


def _summarise_ic(ic_df: pd.DataFrame, prefix: str = "") -> dict[str, float]:
    """Reduce an IC series DataFrame to a summary dict."""
    if ic_df.empty:
        return {}
    ic = ic_df["ic"].dropna()
    rank_ic = ic_df["rank_ic"].dropna()
    result: dict[str, float] = {}
    if not ic.empty:
        result[f"{prefix}mean_ic"] = float(ic.mean())
        result[f"{prefix}icir"] = float(ic.mean() / ic.std()) if len(ic) > 1 and ic.std() > 1e-15 else float("nan")
    if not rank_ic.empty:
        result[f"{prefix}mean_rank_ic"] = float(rank_ic.mean())
        result[f"{prefix}rank_icir"] = float(rank_ic.mean() / rank_ic.std()) if len(rank_ic) > 1 and rank_ic.std() > 1e-15 else float("nan")
        result[f"{prefix}ic_dates"] = int(len(rank_ic))
        result[f"{prefix}ic_win_rate"] = float((rank_ic > 0).mean())
    return result


# ---------------------------------------------------------------------------
# Raw vs residualized comparison
# ---------------------------------------------------------------------------
def build_raw_vs_residualized_comparison(
    frame: pd.DataFrame,
    factors: list[str],
    labels: Optional[list[str]] = None,
    suffix: str = DEFAULT_SUFFIX,
    min_count: int = DEFAULT_MIN_COUNT,
) -> pd.DataFrame:
    """Compare raw and residualized IC metrics for every factor x label pair.

    Returns a DataFrame with columns:
    factor, label, raw_mean_ic, raw_icir, raw_mean_rank_ic, raw_rank_icir,
    residualized_mean_ic, residualized_icir, residualized_mean_rank_ic,
    residualized_rank_icir, ic_retention, rank_ic_retention,
    residualized_coverage, residualized_r2_mean
    """
    if labels is None:
        labels = [l for l in DEFAULT_LABELS if l in frame.columns]

    rows: list[dict] = []
    for factor in factors:
        if factor not in frame.columns:
            continue
        resid_col = f"{factor}{suffix}"
        if resid_col not in frame.columns:
            continue

        # Residualized coverage
        resid_valid = frame[resid_col].notna().sum()
        total = len(frame)
        coverage = resid_valid / total if total else 0.0

        # Mean R^2 from daily diagnostics (computed inline, in z-score space)
        r2_vals: list[float] = []
        for _, group in frame.groupby("datetime", sort=True):
            valid = group[[factor, resid_col]].notna().all(axis=1)
            if valid.sum() < 2:
                continue
            raw = numeric_series(group.loc[valid, factor])
            resid = numeric_series(group.loc[valid, resid_col])
            # R^2 in z-score space: winsorize+zscore factor to match regression domain
            factor_w = winsorize_mad(raw)
            factor_z = cross_sectional_zscore(factor_w, robust=True, clip=3.0)
            valid_z = factor_z.notna()
            if valid_z.sum() < 2:
                continue
            var_fz = float(factor_z.loc[valid_z].var())
            var_rz = float(resid.loc[valid_z].var())
            if var_fz > 1e-15:
                r2_vals.append(1.0 - var_rz / var_fz)
        mean_r2 = float(np.mean(r2_vals)) if r2_vals else float("nan")

        for label in labels:
            if label not in frame.columns:
                continue

            raw_ic = _daily_ic(frame, factor, label, min_count=min_count)
            resid_ic = _daily_ic(frame, resid_col, label, min_count=min_count)

            raw_s = _summarise_ic(raw_ic, prefix="raw_")
            resid_s = _summarise_ic(resid_ic, prefix="residualized_")

            raw_rank = raw_s.get("raw_mean_rank_ic", float("nan"))
            resid_rank = resid_s.get("residualized_mean_rank_ic", float("nan"))
            rank_retention = resid_rank / raw_rank if pd.notna(raw_rank) and raw_rank != 0 else float("nan")
            ic_retention = (
                resid_s.get("residualized_mean_ic", float("nan"))
                / raw_s.get("raw_mean_ic", float("nan"))
                if pd.notna(raw_s.get("raw_mean_ic", float("nan"))) and raw_s.get("raw_mean_ic", 0) != 0
                else float("nan")
            )

            rows.append({
                "factor": factor,
                "label": label,
                **raw_s,
                **resid_s,
                "ic_retention": ic_retention,
                "rank_ic_retention": rank_retention,
                "residualized_coverage": coverage,
                "residualization_r2_mean": mean_r2,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Candidate action decisions
# ---------------------------------------------------------------------------
def decide_candidate_actions(
    comparison: pd.DataFrame,
    attribution_board: pd.DataFrame,
) -> pd.DataFrame:
    """Generate candidate action rows from the raw-vs-residualized comparison.

    Decision logic:
    - residual_signal_survives:  coverage >= 0.80 and residualized Rank IC > 0 and rank retention > 0.30
    - liquidity_proxy_confirmed: raw Rank IC has magnitude > 0.02 but residualized is near-zero or sign-flipped or weak
    - holdout:                  residualized Rank IC near zero (|IC| < 0.01)
    - needs_manual_review:      coverage < 0.80, insufficient dates, or other uncertainty
    """
    rows: list[dict] = []
    for _, row in comparison.iterrows():
        factor = row["factor"]
        label = row.get("label", "")
        coverage = float(row.get("residualized_coverage", float("nan")))
        raw_rank = float(row.get("raw_mean_rank_ic", float("nan")))
        resid_rank = float(row.get("residualized_mean_rank_ic", float("nan")))
        rank_ret = float(row.get("rank_ic_retention", float("nan")))
        resid_rank_icir = float(row.get("residualized_rank_icir", float("nan")))
        r2_mean = float(row.get("residualization_r2_mean", float("nan")))

        # Attribution metadata
        attr = attribution_board[attribution_board["factor"] == factor]
        raw_act = str(attr["recommended_action"].iloc[0]) if not attr.empty else "unknown"
        src_fam = str(attr["source_family"].iloc[0]) if not attr.empty else "unknown"
        primary_proxy = str(attr["primary_exposure_proxy"].iloc[0]) if not attr.empty else "unknown"

        # --- decision ---
        if pd.isna(coverage) or coverage < 0.80:
            decision = "needs_manual_review"
            reason = f"coverage={coverage:.4f} below 0.80"
        elif (
            pd.notna(resid_rank)
            and resid_rank > 0
            and pd.notna(rank_ret)
            and rank_ret > 0.30
        ):
            decision = "residual_signal_survives"
            reason = (
                f"residualized Rank IC={resid_rank:.6f} remains positive, "
                f"rank_retention={rank_ret:.2f}, r2_mean={r2_mean:.4f}"
            )
        elif (
            pd.notna(raw_rank)
            and abs(raw_rank) > 0.02
            and (
                pd.isna(resid_rank)
                or (pd.notna(rank_ret) and abs(rank_ret) < 0.30)
                or (pd.notna(resid_rank) and resid_rank * raw_rank <= 0)
            )
        ):
            decision = "liquidity_proxy_confirmed"
            reason = (
                f"raw Rank IC={raw_rank:.6f} significant "
                f"but residualized Rank IC={resid_rank if pd.notna(resid_rank) else 'nan'}, "
                f"rank_retention={rank_ret:.2f} too low or sign flipped"
            )
        elif pd.notna(resid_rank) and abs(resid_rank) < 0.01:
            decision = "holdout"
            reason = f"residualized Rank IC={resid_rank:.6f} near zero, no stable residual signal"
        else:
            decision = "needs_manual_review"
            reason = "insufficient data for automated decision"

        rows.append({
            "factor": factor,
            "label": label,
            "source_family": src_fam,
            "raw_action": raw_act,
            "primary_exposure_proxy": primary_proxy,
            "raw_mean_rank_ic": raw_rank,
            "residualized_mean_rank_ic": resid_rank,
            "residualized_rank_icir": resid_rank_icir,
            "rank_ic_retention": rank_ret,
            "residualized_coverage": coverage,
            "residualization_r2_mean": r2_mean,
            "decision": decision,
            "decision_reason": reason,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Contract status
# ---------------------------------------------------------------------------
def build_contract_status(
    watchlist_count: int,
    residualized_factor_count: int,
    min_coverage: float,
    daily_diag_rows: int,
    comparison_rows: int,
    downstream_default: int = 0,
) -> pd.DataFrame:
    """Produce the contract-status CSV with at least 8 rows."""
    return pd.DataFrame([
        {
            "check_id": "watchlist_rows",
            "status": "pass" if watchlist_count >= 19 else "blocked",
            "detail": f"watchlist_rows={watchlist_count}",
        },
        {
            "check_id": "residualized_factor_count",
            "status": "pass" if residualized_factor_count >= 19 else "blocked",
            "detail": f"residualized_factor_count={residualized_factor_count}",
        },
        {
            "check_id": "residualized_coverage_min",
            "status": "pass" if min_coverage >= 0.80 else "blocked",
            "detail": f"residualized_coverage_min={min_coverage:.4f}",
        },
        {
            "check_id": "daily_diagnostics_rows",
            "status": "pass" if daily_diag_rows > 0 else "blocked",
            "detail": f"daily_diagnostics_rows={daily_diag_rows}",
        },
        {
            "check_id": "raw_vs_residualized_metric_rows",
            "status": "pass" if comparison_rows > 0 else "blocked",
            "detail": f"raw_vs_residualized_metric_rows={comparison_rows}",
        },
        {
            "check_id": "contract_status_rows",
            "status": "pass",
            "detail": "contract_status_rows=8 (target fulfilled)",
        },
        {
            "check_id": "downstream_default_included",
            "status": "pass" if downstream_default == 0 else "blocked",
            "detail": f"downstream_default_included={downstream_default}",
        },
        {
            "check_id": "residualized_factor_frame_produced",
            "status": "pass" if residualized_factor_count >= 19 else "blocked",
            "detail": f"residualized_columns_in_frame={residualized_factor_count}",
        },
    ])
