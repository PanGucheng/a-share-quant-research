"""Run liquidity residualized factor evaluation V1 (V3.39).

Loads the config, existing factor frames, and tradability labels; performs
daily cross-sectional OLS residualization of 19 watchlist probes against
liquidity proxies; produces residualized factor frame, summary, diagnostics,
raw-vs-residualized comparison, candidate actions, contract status, and a
Markdown report.

If cached feature frames with label columns are found they are used for IC
computation; otherwise only residualization diagnostics (R^2, coverage,
raw-residual correlation) populate the comparison table.  The minimum
deliverable always includes real computed numbers -- no dummy files.

Use::

    E:/anaconda_envs/qlib_env/python.exe scripts/run_liquidity_residualized_factor_evaluation_v1.py --config configs/liquidity_residualized_factor_evaluation_v1.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402
from factor_research.liquidity_residualization import (  # noqa: E402
    DEFAULT_LABELS,
    DEFAULT_PROXIES,
    DEFAULT_SUFFIX,
    build_contract_status,
    build_raw_vs_residualized_comparison,
    build_residualized_factor_frame,
    compute_daily_diagnostics,
    compute_residualized_factor_summary,
    decide_candidate_actions,
    find_label_frame,
    merge_factor_frames,
    merge_tradability,
    read_attribution_board,
)
from factor_research.preprocess import cross_sectional_zscore, winsorize_mad  # noqa: E402

DEFAULT_CONFIG = Path("configs/liquidity_residualized_factor_evaluation_v1.yaml")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _coverage(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.notna().sum() / len(series)) if len(series) else 0.0


def _coverage_min(frame: pd.DataFrame, factor_cols: list[str]) -> float:
    covs = []
    for c in factor_cols:
        if c in frame.columns:
            covs.append(_coverage(frame[c]))
    return min(covs) if covs else 0.0


# ---------------------------------------------------------------------------
# main pipeline
# ---------------------------------------------------------------------------
def run(config_path: Path) -> dict[str, pd.DataFrame]:
    """Execute the full pipeline and return output DataFrames."""
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    inputs = data.get("inputs", {})
    res_cfg = data.get("residualization", {})
    output_dir = _resolve(data.get("output_dir", "outputs/liquidity_residualized_factor_evaluation_v1/current"))
    output_dir.mkdir(parents=True, exist_ok=True)

    proxies = res_cfg.get("proxies", DEFAULT_PROXIES)
    suffix = res_cfg.get("suffix", DEFAULT_SUFFIX)
    min_count = int(res_cfg.get("min_count", 50))
    labels_cfg = data.get("labels", DEFAULT_LABELS)
    min_ic_count = int(data.get("min_ic_count", 50))

    # --- 1. read attribution board / watchlist ---
    board_path = _resolve(inputs["tradability_exposure_attribution_board"])
    board = read_attribution_board(board_path)
    watchlist = board["factor"].unique().tolist()
    print(f"Watchlist factors: {len(watchlist)}", flush=True)

    # --- 2. load factor frames ---
    ta_path = _resolve(inputs.get("ta_factor_frame", ""))
    a101_path = _resolve(inputs.get("alpha101_factor_frame", ""))

    frame = merge_factor_frames(ta_path, a101_path, factor_list=watchlist)
    print(f"Merged factor frame: {frame.shape}", flush=True)

    # Track which watchlist factors are actually present
    present_factors = [f for f in watchlist if f in frame.columns]
    missing_factors = [f for f in watchlist if f not in frame.columns]
    print(f"Factors present: {len(present_factors)}, missing: {len(missing_factors)}", flush=True)
    if missing_factors:
        print(f"  Missing: {missing_factors}", flush=True)

    # --- 3. merge tradability labels ---
    tradability_dir = _resolve(inputs["tradability_dir"])
    frame = merge_tradability(frame, tradability_dir)
    print(f"After tradability merge: {frame.shape}", flush=True)

    # Ensure proxy columns exist -- fail loudly if any required proxy is missing
    proxy_present = [p for p in proxies if p in frame.columns]
    missing_proxies = [p for p in proxies if p not in frame.columns]
    if missing_proxies:
        raise ValueError(
            f"Required proxy column(s) missing after tradability merge: {missing_proxies}. "
            f"Expected proxies: {proxies}. Present columns: {proxy_present}. "
            f"Check that tradability_labels.csv contains: {missing_proxies}"
        )
    print(f"Proxy columns present: {proxy_present}", flush=True)
    for p in proxy_present:
        nn = int(frame[p].notna().sum())
        print(f"  {p}: {nn}/{len(frame)} non-null", flush=True)

    # --- 4. attach labels if possible ---
    available_labels: list[str] = []
    label_frame = None

    # First check if factor frame already has labels
    for label in labels_cfg:
        if label in frame.columns:
            available_labels.append(label)

    if available_labels:
        print(f"Labels available in factor frame: {available_labels}", flush=True)
    else:
        # Try to find from feature cache
        cache_dir = _resolve(inputs.get("feature_cache_dir", ""))
        print(f"Scanning feature cache: {cache_dir}", flush=True)
        label_frame = find_label_frame(cache_dir)
        if label_frame is not None:
            # Merge labels into frame
            if "instrument" in label_frame.columns:
                label_frame["instrument"] = label_frame["instrument"].astype(str).str.upper()
            frame = frame.merge(label_frame, on=["datetime", "instrument"], how="left")
            for label in labels_cfg:
                if label in frame.columns:
                    available_labels.append(label)
            print(f"Labels attached from cache: {available_labels}  (frame now {frame.shape})", flush=True)
        else:
            print("No label columns found - residualization diagnostics only.", flush=True)
            print("raw-vs-residualized comparison will use diagnostic metrics (R^2, coverage).", flush=True)

    # --- 5. build residualized factor frame ---
    print("Residualizing...", flush=True)
    frame = build_residualized_factor_frame(
        frame,
        factors=present_factors,
        proxies=proxies,
        min_count=min_count,
        suffix=suffix,
    )
    resid_cols = [f"{f}{suffix}" for f in present_factors]
    resid_present = [c for c in resid_cols if c in frame.columns]
    print(f"Residualized columns produced: {len(resid_present)}", flush=True)

    # --- 6. daily diagnostics ---
    print("Computing daily diagnostics...", flush=True)
    daily_diag = compute_daily_diagnostics(frame, present_factors, proxies=proxies, suffix=suffix)
    print(f"Daily diagnostics rows: {len(daily_diag)}", flush=True)

    # --- 7. factor summary ---
    factor_summary = compute_residualized_factor_summary(frame, present_factors, suffix=suffix)
    min_coverage = float(factor_summary["residualized_coverage"].min()) if not factor_summary.empty else 0.0
    print(f"Factor summary rows: {len(factor_summary)}, min coverage: {min_coverage:.4f}", flush=True)

    # --- 8. raw-vs-residualized comparison ---
    comparison_labels = available_labels if available_labels else labels_cfg
    print(f"Building raw-vs-residualized comparison (labels: {comparison_labels})...", flush=True)
    comparison = build_raw_vs_residualized_comparison(
        frame,
        factors=present_factors,
        labels=comparison_labels,
        suffix=suffix,
        min_count=min_ic_count,
    )
    print(f"Comparison rows: {len(comparison)}", flush=True)

    # If no labels available, the comparison still has residualization diagnostics
    # (coverage, r2_mean) for each factor.  Ensure it is non-empty.
    if comparison.empty and available_labels:
        print("WARNING: Comparison is empty despite having labels - this is unexpected.")
    elif comparison.empty:
        # Build diagnostics-only comparison
        print("Building diagnostics-only comparison (no IC metrics)...", flush=True)
        diag_rows = []
        for factor in present_factors:
            resid_col = f"{factor}{suffix}"
            if resid_col not in frame.columns:
                continue
            cov = _coverage(frame[resid_col])
            r2_vals = []
            for _, group in frame.groupby("datetime", sort=True):
                valid_mask = group[[factor, resid_col]].notna().all(axis=1)
                if valid_mask.sum() < 2:
                    continue
                raw = group.loc[valid_mask, factor].astype(float)
                res = group.loc[valid_mask, resid_col].astype(float)
                raw_w = winsorize_mad(raw)
                raw_z = cross_sectional_zscore(raw_w, robust=True, clip=3.0)
                valid_z = raw_z.notna()
                if valid_z.sum() < 2:
                    continue
                vr = float(raw_z.loc[valid_z].var())
                vres = float(res.loc[valid_z].var())
                if vr > 1e-15:
                    r2_vals.append(1.0 - vres / vr)
            mean_r2 = float(np.mean(r2_vals)) if r2_vals else float("nan")
            diag_rows.append({
                "factor": factor,
                "label": "no_label",
                "raw_mean_rank_ic": float("nan"),
                "residualized_mean_rank_ic": float("nan"),
                "rank_ic_retention": float("nan"),
                "residualized_coverage": cov,
                "residualization_r2_mean": mean_r2,
            })
        comparison = pd.DataFrame(diag_rows)

    # --- 9. candidate actions ---
    print("Deciding candidate actions...", flush=True)
    actions = decide_candidate_actions(comparison, board)
    print(f"Candidate actions rows: {len(actions)}", flush=True)

    # --- 10. contract status ---
    contract = build_contract_status(
        watchlist_count=len(watchlist),
        residualized_factor_count=len(resid_present),
        min_coverage=min_coverage,
        daily_diag_rows=len(daily_diag),
        comparison_rows=len(comparison),
        downstream_default=0,
    )
    print(f"Contract status rows: {len(contract)}", flush=True)

    # --- 11. write outputs ---
    print(f"Writing outputs to {output_dir} ...", flush=True)

    # residualized_factor_frame.pkl (large, local cache only)
    pkl_path = output_dir / "residualized_factor_frame.pkl"
    frame.to_pickle(pkl_path)
    print(f"  {pkl_path.name}  ({frame.shape})", flush=True)

    _write_csv(factor_summary, output_dir / "residualized_factor_summary.csv")
    _write_csv(daily_diag, output_dir / "daily_residualization_diagnostics.csv")
    _write_csv(comparison, output_dir / "raw_vs_residualized_metric_comparison.csv")
    _write_csv(actions, output_dir / "residualized_candidate_actions.csv")
    _write_csv(contract, output_dir / "liquidity_residualized_contract_status.csv")

    # --- 12. markdown report ---
    lines = _build_report(
        watchlist_count=len(watchlist),
        present_count=len(present_factors),
        resid_count=len(resid_present),
        min_coverage=min_coverage,
        labels_available=available_labels,
        factor_summary=factor_summary,
        daily_diag=daily_diag,
        comparison=comparison,
        actions=actions,
        contract=contract,
    )
    (output_dir / "liquidity_residualized_factor_evaluation_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )

    print("Done.", flush=True)

    return {
        "factor_summary": factor_summary,
        "daily_diagnostics": daily_diag,
        "comparison": comparison,
        "actions": actions,
        "contract": contract,
    }


def _build_report(
    *,
    watchlist_count: int,
    present_count: int,
    resid_count: int,
    min_coverage: float,
    labels_available: list[str],
    factor_summary: pd.DataFrame,
    daily_diag: pd.DataFrame,
    comparison: pd.DataFrame,
    actions: pd.DataFrame,
    contract: pd.DataFrame,
) -> list[str]:
    lines = [
        "# Liquidity Residualized Factor Evaluation V1 Report",
        "",
        "V3.39 -- Residualized evaluation of 19 tradability-exposed probes.",
        "",
        "## Status",
        "",
        f"- Watchlist factors: {watchlist_count}",
        f"- Factors present in frames: {present_count}",
        f"- Residualized factors: {resid_count}",
        f"- Minimum residualized coverage: {min_coverage:.4f}",
        f"- Labels available: {labels_available if labels_available else 'none (diagnostics-only)'}",
        f"- Daily diagnostics rows: {len(daily_diag)}",
        f"- Comparison rows: {len(comparison)}",
        f"- Contract status rows: {len(contract)}",
        f"- Downstream default included: 0",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Factor Coverage Summary",
        "",
        markdown_table(factor_summary.head(40)),
        "",
        "## Daily Diagnostics (first 20 rows)",
        "",
        markdown_table(daily_diag.head(20)),
        "",
        "## Raw vs Residualized Comparison",
        "",
        markdown_table(comparison.head(40)),
        "",
        "## Candidate Actions",
        "",
        markdown_table(actions),
        "",
        "## Decision Summary",
        "",
    ]
    if not actions.empty and "decision" in actions.columns:
        summary = actions.groupby("decision").size().reset_index(name="count").sort_values("count", ascending=False)
        lines.append(markdown_table(summary))
    else:
        lines.append("No decisions available.")
    lines.extend([
        "",
        "## Notes",
        "",
        "- Residualization suffix: `__resid_liquidity`; raw factors never overwritten.",
        "- Proxies: `liquidity_value`, `liquidity_bucket`, `tradability_score` (constant proxies auto-excluded per day).",
        "- Each trading day is residualized independently via OLS after winsorized z-scoring.",
        "- R^2 is computed in z-score / regression space (var of residual vs var of z-scored factor).",
        "- `residual_signal_survives` -> signal remains positive after removing liquidity exposure.",
        "- `liquidity_proxy_confirmed` -> raw alpha largely explained by liquidity/tradability.",
        "- `holdout` -> no stable residual signal; hold back from training.",
        "- `needs_manual_review` -> insufficient data, low coverage, or unclear signal for automated decision.",
        "",
        "- Large `residualized_factor_frame.pkl` is a local re-generable cache; CSV artefacts are the canonical record.",
    ])
    if not labels_available:
        lines.extend([
            "",
            "## Fallback Notice",
            "",
            "No forward-return label columns were found in the factor frames or feature cache.",
            "IC-based metrics (mean_ic, mean_rank_ic, icir, rank_icir, ic_retention) are NaN.",
            "The comparison table still contains actual computed diagnostics:",
            "- `residualized_coverage` -- proportion of rows with a valid residualized value.",
            "- `residualization_r2_mean` -- mean daily R^2 in z-score space (var(residual_z) / var(factor_z)).",
            "Candidate decisions rely on coverage and R^2 instead of IC retention.",
        ])
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run liquidity residualized factor evaluation V1 (V3.39)."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
