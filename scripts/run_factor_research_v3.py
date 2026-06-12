from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from multiprocessing import freeze_support
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.dataset import TradableFilterConfig, apply_tradable_filter, prepare_research_frame
from factor_research.diagnostics import factor_correlation, information_coefficient, summarize_factors
from factor_research.evaluator import FactorResearchConfig, finite_numeric_rows, load_feature_frame
from factor_research.factor_library import LABEL_COLUMNS, add_basic_factors
from factor_research.metrics import group_returns, summarize_group_returns
from factor_research.neutralization import add_neutralized_factors
from factor_research.registry import FactorSpec, enabled_specs, spec_map
from factor_research.report import markdown_table
from factor_research.slices import add_default_slices


DEFAULT_PROVIDER_URI = "E:/qlib_prj/qlib_data/cn_data_community_20260609_derived"
DEFAULT_MARKET = "all_stock_shsz_liquid2000"
DEFAULT_LABELS = "label_20d_t1"
DEFAULT_FACTORS = "amplitude_20,std_20,rev_5,ret_20,amount_mean_20"


@dataclass(frozen=True)
class ResearchWindow:
    name: str
    start: str
    end: str
    tradability_dir: Path
    data_quality_dir: Path


DEFAULT_WINDOWS = [
    ResearchWindow(
        "main_research_2021_2023",
        "2021-01-01",
        "2023-12-29",
        Path("outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29"),
        Path("outputs/data_quality_tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29"),
    ),
    ResearchWindow(
        "recent_oos_2024_2026",
        "2024-01-01",
        "2026-06-09",
        Path("outputs/tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09"),
        Path("outputs/data_quality_tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09"),
    ),
]


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_labels(value: str) -> list[str]:
    labels = parse_csv(value)
    unknown = [label for label in labels if label not in LABEL_COLUMNS]
    if unknown:
        raise ValueError(f"Unknown labels: {unknown}. Known labels: {LABEL_COLUMNS}")
    return labels


def parse_window(value: str) -> ResearchWindow:
    parts = [part.strip() for part in value.split(",", 4)]
    if len(parts) != 5:
        raise argparse.ArgumentTypeError("--window must be name,start,end,tradability_dir,data_quality_dir")
    return ResearchWindow(parts[0], parts[1], parts[2], Path(parts[3]), Path(parts[4]))


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def concat_or_empty(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if frame is not None and not frame.empty]
    return pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()


def padded_dates(window: ResearchWindow) -> tuple[str, str]:
    start = (pd.Timestamp(window.start) - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
    end = (pd.Timestamp(window.end) + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    return start, end


def cache_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def basic_factor_cache_path(args: argparse.Namespace, window: ResearchWindow) -> Path | None:
    if args.no_factor_cache:
        return None
    load_start, load_end = padded_dates(window)
    payload = {
        "provider_uri": str(args.provider_uri).replace("\\", "/"),
        "market": args.market,
        "start_time": load_start,
        "end_time": load_end,
        "basic_factor_version": 1,
    }
    return resolve_path(args.factor_cache_dir) / f"basic_factors_{cache_digest(payload)}.pkl"


def slice_window(frame: pd.DataFrame, window: ResearchWindow) -> pd.DataFrame:
    start = pd.Timestamp(window.start)
    end = pd.Timestamp(window.end)
    return frame[frame["datetime"].between(start, end)].copy()


def load_window_frame(args: argparse.Namespace, window: ResearchWindow, output_dir: Path) -> pd.DataFrame:
    load_start, load_end = padded_dates(window)
    print(f"Loading V3 features: {window.name} {load_start} to {load_end}", flush=True)
    factor_cache = basic_factor_cache_path(args, window)
    if factor_cache is not None and factor_cache.exists() and not args.refresh_factor_cache:
        print(f"Loading cached basic factors: {factor_cache}", flush=True)
        raw_with_factors = pd.read_pickle(factor_cache)
    else:
        config = FactorResearchConfig(
            provider_uri=args.provider_uri,
            market=args.market,
            start_time=load_start,
            end_time=load_end,
            output_dir=output_dir,
            label=args.labels[0],
            quantiles=args.quantiles,
            min_count=args.min_count,
            feature_cache_dir=None if args.no_feature_cache else resolve_path(args.feature_cache_dir),
            refresh_feature_cache=args.refresh_feature_cache,
        )
        raw_with_factors = add_basic_factors(load_feature_frame(config))
        if factor_cache is not None:
            factor_cache.parent.mkdir(parents=True, exist_ok=True)
            raw_with_factors.to_pickle(factor_cache)
            print(f"Cached basic factors: {factor_cache}", flush=True)
    raw = slice_window(raw_with_factors, window)
    with_context = prepare_research_frame(raw, resolve_path(window.tradability_dir), resolve_path(window.data_quality_dir))
    tradable = apply_tradable_filter(
        with_context,
        TradableFilterConfig(
            min_liquidity_bucket=args.min_liquidity_bucket,
            min_tradability_score=args.min_tradability_score,
        ),
    )
    print(f"Window {window.name}: {len(raw):,} raw rows, {len(tradable):,} tradable rows", flush=True)
    return tradable


def build_neutralized_specs(base_specs: list[FactorSpec], mapping: pd.DataFrame) -> list[FactorSpec]:
    base_by_name = spec_map(base_specs)
    specs = []
    for row in mapping.itertuples(index=False):
        base = base_by_name[row.factor]
        specs.append(
            FactorSpec(
                name=row.neutralized_factor,
                category=base.category,
                expected_direction=base.expected_direction,
                dependencies=(base.name,),
                description=f"{base.description} Neutralization: {row.neutralization}.",
                labels=base.labels,
                enabled=True,
            )
        )
    return specs


def summarize_by_slice(
    frame: pd.DataFrame,
    specs: list[FactorSpec],
    labels: list[str],
    window_name: str,
    quantiles: int,
    min_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_frames = []
    group_frames = []
    for slice_type in ["year_slice", "liquidity_bucket", "volatility_bucket", "market_state"]:
        if slice_type not in frame.columns:
            continue
        for slice_value, slice_frame in frame.dropna(subset=[slice_type]).groupby(slice_type, sort=True):
            sample_name = f"{slice_type}={slice_value}"
            for label in labels:
                ic = information_coefficient(slice_frame, specs, label, min_count)
                summary = summarize_factors(slice_frame, ic, specs, label, window_name, sample_name)
                if not summary.empty:
                    summary.insert(2, "slice_type", slice_type)
                    summary.insert(3, "slice_value", str(slice_value))
                    summary_frames.append(summary)
                groups = group_returns(slice_frame, specs, [label], window_name, sample_name, quantiles, min_count)
                if not groups.empty:
                    groups.insert(2, "slice_type", slice_type)
                    groups.insert(3, "slice_value", str(slice_value))
                    group_frames.append(groups)
    return concat_or_empty(summary_frames), concat_or_empty(group_frames)


def factor_exposure_correlation(
    frame: pd.DataFrame,
    base_specs: list[FactorSpec],
    window_name: str,
    exposures: list[str],
    min_count: int,
) -> pd.DataFrame:
    rows = []
    for spec in base_specs:
        if spec.name not in frame.columns:
            continue
        for exposure in exposures:
            if exposure == spec.name:
                continue
            if exposure not in frame.columns:
                continue
            daily = []
            for dt, group in frame.groupby("datetime", sort=True):
                values = finite_numeric_rows(group, [spec.name, exposure])
                if len(values) < min_count:
                    continue
                daily.append(values[spec.name].corr(values[exposure], method="spearman"))
            series = pd.Series(daily, dtype=float).dropna()
            rows.append(
                {
                    "window": window_name,
                    "factor": spec.name,
                    "exposure": exposure,
                    "mean_spearman_corr": series.mean() if not series.empty else np.nan,
                    "abs_mean_spearman_corr": series.abs().mean() if not series.empty else np.nan,
                    "corr_dates": int(len(series)),
                }
            )
    return pd.DataFrame(rows)


def candidate_changelog(summary: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    if summary.empty or mapping.empty:
        return pd.DataFrame()
    base_rows = mapping[["factor", "neutralized_factor", "neutralization"]].drop_duplicates().copy()
    merged = summary.merge(base_rows, left_on="factor", right_on="neutralized_factor", how="inner")
    merged["base_factor"] = merged["factor_y"]
    merged["neutralized_factor_name"] = merged["factor_x"]
    raw = merged[merged["neutralization"] == "raw"][
        ["window", "label", "base_factor", "directional_mean_rank_ic", "ic_win_rate"]
    ].rename(
        columns={
            "directional_mean_rank_ic": "raw_directional_rank_ic",
            "ic_win_rate": "raw_ic_win_rate",
        }
    )
    compared = merged.merge(raw, on=["window", "label", "base_factor"], how="left")
    compared["delta_directional_rank_ic"] = (
        compared["directional_mean_rank_ic"] - compared["raw_directional_rank_ic"]
    )
    compared["effect"] = np.select(
        [
            compared["neutralization"] == "raw",
            compared["delta_directional_rank_ic"] >= 0.01,
            compared["delta_directional_rank_ic"] <= -0.01,
        ],
        ["baseline", "improved", "weakened"],
        default="similar",
    )
    return compared[
        [
            "window",
            "label",
            "base_factor",
            "neutralization",
            "neutralized_factor_name",
            "raw_directional_rank_ic",
            "directional_mean_rank_ic",
            "delta_directional_rank_ic",
            "raw_ic_win_rate",
            "ic_win_rate",
            "effect",
        ]
    ].rename(columns={"neutralized_factor_name": "neutralized_factor"})


def exposure_interpretation(summary: pd.DataFrame, exposure_corr: pd.DataFrame, changelog: pd.DataFrame, label: str) -> pd.DataFrame:
    if summary.empty or changelog.empty:
        return pd.DataFrame()
    main_summary = summary[
        (summary["window"] == "main_research_2021_2023")
        & (summary["label"] == label)
        & summary["factor"].str.endswith("__raw")
    ].copy()
    if main_summary.empty:
        return pd.DataFrame()
    main_summary["base_factor"] = main_summary["factor"].str.replace("__raw", "", regex=False)

    joint = changelog[
        (changelog["window"] == "main_research_2021_2023")
        & (changelog["label"] == label)
        & (changelog["neutralization"] == "liquidity_volatility_residual")
    ][["base_factor", "directional_mean_rank_ic", "delta_directional_rank_ic"]].rename(
        columns={
            "directional_mean_rank_ic": "joint_residual_directional_rank_ic",
            "delta_directional_rank_ic": "joint_residual_delta",
        }
    )
    exposure = (
        exposure_corr[exposure_corr["window"] == "main_research_2021_2023"]
        .sort_values("abs_mean_spearman_corr", ascending=False)
        .drop_duplicates("factor")
        [["factor", "exposure", "mean_spearman_corr", "abs_mean_spearman_corr"]]
        .rename(
            columns={
                "factor": "base_factor",
                "exposure": "dominant_exposure",
                "mean_spearman_corr": "dominant_exposure_corr",
                "abs_mean_spearman_corr": "dominant_abs_exposure_corr",
            }
        )
        if not exposure_corr.empty
        else pd.DataFrame()
    )
    result = main_summary[
        ["base_factor", "expected_direction", "directional_mean_rank_ic", "directional_rank_icir", "ic_win_rate"]
    ].rename(columns={"directional_mean_rank_ic": "raw_directional_rank_ic"})
    result = result.merge(joint, on="base_factor", how="left")
    if not exposure.empty:
        result = result.merge(exposure, on="base_factor", how="left")
    else:
        result["dominant_exposure"] = pd.NA
        result["dominant_exposure_corr"] = np.nan
        result["dominant_abs_exposure_corr"] = np.nan

    result["interpretation"] = np.select(
        [
            result["joint_residual_directional_rank_ic"].ge(0.03),
            result["dominant_abs_exposure_corr"].ge(0.8)
            & (
                result["joint_residual_directional_rank_ic"].le(0.01)
                | result["joint_residual_delta"].le(-0.05)
            ),
            result["raw_directional_rank_ic"].ge(0.02),
        ],
        ["residual_alpha_candidate", "exposure_dominated", "watch_after_controls"],
        default="watch",
    )
    return result.sort_values("raw_directional_rank_ic", ascending=False)


def write_exposure_report(
    args: argparse.Namespace,
    summary: pd.DataFrame,
    exposure_corr: pd.DataFrame,
    changelog: pd.DataFrame,
    output: Path,
) -> None:
    exposure = (
        exposure_corr.sort_values("abs_mean_spearman_corr", ascending=False).head(40)
        if not exposure_corr.empty
        else pd.DataFrame()
    )
    changes = (
        changelog[
            (changelog["window"] == "main_research_2021_2023")
            & (changelog["label"] == args.labels[0])
            & (changelog["neutralization"] != "raw")
        ]
        .sort_values(["base_factor", "delta_directional_rank_ic"], ascending=[True, False])
        if not changelog.empty
        else pd.DataFrame()
    )
    interpretation = exposure_interpretation(summary, exposure_corr, changelog, args.labels[0])
    lines = [
        "# Factor Exposure Report",
        "",
        "This report explains whether a factor's apparent signal is mostly standalone residual signal or exposure to liquidity, volatility, and amount proxies.",
        "",
        "## Interpretation",
        "",
        markdown_table(
            interpretation[
                [
                    "base_factor",
                    "expected_direction",
                    "raw_directional_rank_ic",
                    "directional_rank_icir",
                    "joint_residual_directional_rank_ic",
                    "joint_residual_delta",
                    "dominant_exposure",
                    "dominant_exposure_corr",
                    "interpretation",
                ]
            ]
            if not interpretation.empty
            else pd.DataFrame()
        ),
        "",
        "## Strongest Exposure Correlations",
        "",
        markdown_table(exposure),
        "",
        "## Neutralization Change Log",
        "",
        markdown_table(
            changes[
                [
                    "base_factor",
                    "neutralization",
                    "raw_directional_rank_ic",
                    "directional_mean_rank_ic",
                    "delta_directional_rank_ic",
                    "effect",
                ]
            ].head(80)
            if not changes.empty
            else pd.DataFrame()
        ),
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    args: argparse.Namespace,
    summary: pd.DataFrame,
    slice_summary: pd.DataFrame,
    exposure_corr: pd.DataFrame,
    changelog: pd.DataFrame,
    output: Path,
) -> None:
    main = (
        summary[
            (summary["window"] == "main_research_2021_2023")
            & (summary["label"] == args.labels[0])
            & summary["factor"].str.contains("__")
        ]
        .sort_values("directional_mean_rank_ic", ascending=False)
        .head(30)
        if not summary.empty
        else pd.DataFrame()
    )
    exposure = (
        exposure_corr.sort_values("abs_mean_spearman_corr", ascending=False).head(30)
        if not exposure_corr.empty
        else pd.DataFrame()
    )
    changes = (
        changelog[
            (changelog["window"] == "main_research_2021_2023")
            & (changelog["label"] == args.labels[0])
            & (changelog["neutralization"] != "raw")
        ]
        .sort_values(["base_factor", "delta_directional_rank_ic"], ascending=[True, False])
        .head(50)
        if not changelog.empty
        else pd.DataFrame()
    )
    slice_view = (
        slice_summary[
            (slice_summary["window"] == "main_research_2021_2023")
            & (slice_summary["label"] == args.labels[0])
            & slice_summary["factor"].str.endswith("__raw")
        ]
        .sort_values(["factor", "slice_type", "slice_value"])
        .head(80)
        if not slice_summary.empty
        else pd.DataFrame()
    )

    lines = [
        "# Factor Research V3 Report",
        "",
        f"- Provider URI: `{args.provider_uri}`",
        f"- Market: `{args.market}`",
        f"- Labels: `{','.join(args.labels)}`",
        f"- Base factors: `{','.join(args.factors)}`",
        f"- Tradable filter: `can_buy == true`, `liquidity_bucket >= {args.min_liquidity_bucket}`, "
        f"`tradability_score >= {args.min_tradability_score}`",
        "",
        "## Main Neutralized Summary",
        "",
        markdown_table(
            main[
                [
                    "window",
                    "label",
                    "factor",
                    "expected_direction",
                    "coverage",
                    "directional_mean_rank_ic",
                    "directional_rank_icir",
                    "ic_win_rate",
                    "ic_dates",
                ]
            ]
            if not main.empty
            else pd.DataFrame()
        ),
        "",
        "## Neutralization Change Log",
        "",
        markdown_table(
            changes[
                [
                    "base_factor",
                    "neutralization",
                    "raw_directional_rank_ic",
                    "directional_mean_rank_ic",
                    "delta_directional_rank_ic",
                    "effect",
                ]
            ]
            if not changes.empty
            else pd.DataFrame()
        ),
        "",
        "## Exposure Correlation",
        "",
        markdown_table(exposure if not exposure.empty else pd.DataFrame()),
        "",
        "## Raw Factor Slice Summary",
        "",
        markdown_table(
            slice_view[
                [
                    "factor",
                    "slice_type",
                    "slice_value",
                    "coverage",
                    "directional_mean_rank_ic",
                    "directional_rank_icir",
                    "ic_win_rate",
                    "ic_dates",
                ]
            ]
            if not slice_view.empty
            else pd.DataFrame()
        ),
        "",
        "## Output Files",
        "",
        "- `factor_preprocess_summary.csv`",
        "- `factor_neutralized_summary.csv`",
        "- `factor_neutralized_group_return_summary.csv`",
        "- `factor_neutralized_correlation.csv`",
        "- `factor_slice_ic.csv`",
        "- `factor_slice_group_return_summary.csv`",
        "- `factor_exposure_correlation.csv`",
        "- `factor_exposure_report.md`",
        "- `factor_candidate_changelog.csv`",
    ]
    if args.write_detail:
        lines.extend(
            [
                "- `factor_neutralized_group_return.csv`",
                "- `factor_slice_group_return.csv`",
            ]
        )
    else:
        lines.append("- Detail group-return CSVs are skipped by default. Use `--write-detail` to write them.")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_specs = [spec for spec in enabled_specs(args.labels) if spec.name in set(args.factors)]
    windows = args.window or DEFAULT_WINDOWS

    preprocess_frames = []
    summary_frames = []
    group_frames = []
    slice_summary_frames = []
    slice_group_frames = []
    correlation_frames = []
    exposure_frames = []
    changelog_frames = []

    for window in windows:
        frame = load_window_frame(args, window, output_dir)
        frame = add_default_slices(frame, label=args.labels[0], quantiles=args.quantiles)
        neutralized, preprocess = add_neutralized_factors(frame, base_specs, min_count=args.min_count)
        preprocess.insert(0, "window", window.name)
        preprocess_frames.append(preprocess)
        neutralized_specs = build_neutralized_specs(base_specs, preprocess)
        raw_neutralized_specs = [spec for spec in neutralized_specs if spec.name.endswith("__raw")]

        for label in args.labels:
            print(f"Window {window.name} label {label}: neutralized IC/summary", flush=True)
            ic = information_coefficient(neutralized, neutralized_specs, label, args.min_count)
            summary = summarize_factors(neutralized, ic, neutralized_specs, label, window.name, "tradable_only")
            groups = group_returns(neutralized, neutralized_specs, [label], window.name, "tradable_only", args.quantiles, args.min_count)
            corr = factor_correlation(neutralized, neutralized_specs, window.name, "tradable_only", label)
            summary_frames.append(summary)
            group_frames.append(groups)
            correlation_frames.append(corr)

        print(f"Window {window.name}: slice diagnostics", flush=True)
        slice_summary, slice_groups = summarize_by_slice(
            neutralized,
            raw_neutralized_specs,
            args.labels,
            window.name,
            args.quantiles,
            args.min_count,
        )
        slice_summary_frames.append(slice_summary)
        slice_group_frames.append(slice_groups)
        exposure_frames.append(
            factor_exposure_correlation(
                neutralized,
                base_specs,
                window.name,
                ["liquidity_bucket", "volatility_bucket", "log_amount_mean_20", "std_20", "amplitude_20"],
                args.min_count,
            )
        )

    preprocess = concat_or_empty(preprocess_frames)
    summary = concat_or_empty(summary_frames)
    groups = concat_or_empty(group_frames)
    group_summary = summarize_group_returns(groups)
    slice_summary = concat_or_empty(slice_summary_frames)
    slice_groups = concat_or_empty(slice_group_frames)
    slice_group_summary = summarize_group_returns(slice_groups)
    correlation = concat_or_empty(correlation_frames)
    exposure_corr = concat_or_empty(exposure_frames)
    changelog = candidate_changelog(summary, preprocess)

    preprocess.to_csv(output_dir / "factor_preprocess_summary.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "factor_neutralized_summary.csv", index=False, encoding="utf-8-sig")
    if args.write_detail:
        groups.to_csv(output_dir / "factor_neutralized_group_return.csv", index=False, encoding="utf-8-sig")
    else:
        stale_path = output_dir / "factor_neutralized_group_return.csv"
        if stale_path.exists():
            stale_path.unlink()
    group_summary.to_csv(output_dir / "factor_neutralized_group_return_summary.csv", index=False, encoding="utf-8-sig")
    correlation.to_csv(output_dir / "factor_neutralized_correlation.csv", index=False, encoding="utf-8-sig")
    slice_summary.to_csv(output_dir / "factor_slice_ic.csv", index=False, encoding="utf-8-sig")
    if args.write_detail:
        slice_groups.to_csv(output_dir / "factor_slice_group_return.csv", index=False, encoding="utf-8-sig")
    else:
        stale_path = output_dir / "factor_slice_group_return.csv"
        if stale_path.exists():
            stale_path.unlink()
    slice_group_summary.to_csv(output_dir / "factor_slice_group_return_summary.csv", index=False, encoding="utf-8-sig")
    exposure_corr.to_csv(output_dir / "factor_exposure_correlation.csv", index=False, encoding="utf-8-sig")
    changelog.to_csv(output_dir / "factor_candidate_changelog.csv", index=False, encoding="utf-8-sig")
    write_report(args, summary, slice_summary, exposure_corr, changelog, output_dir / "factor_research_v3_report.md")
    write_exposure_report(args, summary, exposure_corr, changelog, output_dir / "factor_exposure_report.md")
    print(f"Factor research V3 outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run factor research V3 neutralization and slice diagnostics.")
    parser.add_argument("--provider-uri", default=DEFAULT_PROVIDER_URI)
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--labels", type=parse_labels, default=parse_labels(DEFAULT_LABELS))
    parser.add_argument("--factors", type=parse_csv, default=parse_csv(DEFAULT_FACTORS))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_research_v3/liquid2000_core"))
    parser.add_argument("--quantiles", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=50)
    parser.add_argument("--min-liquidity-bucket", type=int, default=3)
    parser.add_argument("--min-tradability-score", type=float, default=75.0)
    parser.add_argument(
        "--feature-cache-dir",
        type=Path,
        default=Path("tmp/factor_feature_cache"),
        help="Local cache for raw Qlib feature frames.",
    )
    parser.add_argument(
        "--no-feature-cache",
        action="store_true",
        help="Disable raw Qlib feature-frame cache.",
    )
    parser.add_argument(
        "--refresh-feature-cache",
        action="store_true",
        help="Ignore existing cached feature frames and rewrite them from Qlib data.",
    )
    parser.add_argument(
        "--factor-cache-dir",
        type=Path,
        default=Path("tmp/factor_frame_cache"),
        help="Local cache for frames after basic factor and label calculation.",
    )
    parser.add_argument(
        "--no-factor-cache",
        action="store_true",
        help="Disable cache for frames after basic factor and label calculation.",
    )
    parser.add_argument(
        "--refresh-factor-cache",
        action="store_true",
        help="Ignore existing cached basic-factor frames and rewrite them.",
    )
    parser.add_argument(
        "--write-detail",
        action="store_true",
        help="Write large per-date/per-quantile group-return detail CSVs. Summary CSVs are always written.",
    )
    parser.add_argument(
        "--window",
        type=parse_window,
        action="append",
        help="Optional research window: name,start,end,tradability_dir,data_quality_dir. Can be repeated.",
    )
    return parser


def main() -> None:
    freeze_support()
    args = build_parser().parse_args()
    run(args)


if __name__ == "__main__":
    main()
