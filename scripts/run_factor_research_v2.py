from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.candidate import decide_candidates
from factor_research.diagnostics import (
    attach_tradability,
    bucket_ic,
    factor_correlation,
    group_monotonicity,
    information_coefficient,
    load_tradability_labels,
    summarize_factors,
    tradable_only,
)
from factor_research.evaluator import FactorResearchConfig, load_feature_frame
from factor_research.factor_library import LABEL_COLUMNS, add_basic_factors
from factor_research.registry import enabled_specs, registry_frame
from factor_research.report import markdown_table


DEFAULT_PROVIDER_URI = "E:/qlib_prj/qlib_data/cn_data_community_20260609_derived"
DEFAULT_MARKET = "all_stock_shsz_liquid2000"
DEFAULT_LABELS = "label_10d_t1,label_20d_t1"
DEFAULT_BUCKET_IC_LABELS = "label_20d_t1"
DEFAULT_LEGACY_TIME_SLICE_ROOT = Path("outputs/factor_time_slices")


@dataclass(frozen=True)
class ResearchWindow:
    name: str
    start: str
    end: str
    tradability_dir: Path | None = None


DEFAULT_WINDOWS = [
    ResearchWindow("historical_reference_2010_2016", "2010-01-01", "2016-12-31"),
    ResearchWindow("baseline_alignment_2017_2020", "2017-01-01", "2020-08-01"),
    ResearchWindow(
        "main_research_2021_2023",
        "2021-01-01",
        "2023-12-29",
        Path("outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29"),
    ),
    ResearchWindow(
        "recent_oos_2024_2026",
        "2024-01-01",
        "2026-06-09",
        Path("outputs/tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09"),
    ),
]


def parse_labels(value: str) -> list[str]:
    labels = [label.strip() for label in value.split(",") if label.strip()]
    unknown = [label for label in labels if label not in LABEL_COLUMNS]
    if unknown:
        raise ValueError(f"Unknown label columns: {unknown}. Known labels: {LABEL_COLUMNS}")
    if not labels:
        raise ValueError("At least one label is required.")
    return labels


def parse_optional_labels(value: str) -> list[str]:
    if not value.strip():
        return []
    return parse_labels(value)


def parse_window(value: str) -> ResearchWindow:
    parts = [part.strip() for part in value.split(",", 3)]
    if len(parts) < 3:
        raise argparse.ArgumentTypeError("--window must be name,start,end[,tradability_dir]")
    tradability_dir = Path(parts[3]) if len(parts) == 4 and parts[3] else None
    return ResearchWindow(parts[0], parts[1], parts[2], tradability_dir)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def concat_or_empty(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if frame is not None and not frame.empty]
    return pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()


def slice_window(frame: pd.DataFrame, window: ResearchWindow) -> pd.DataFrame:
    start = pd.Timestamp(window.start)
    end = pd.Timestamp(window.end)
    return frame[frame["datetime"].between(start, end)].copy()


def padded_dates(window: ResearchWindow) -> tuple[str, str]:
    start = (pd.Timestamp(window.start) - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
    end = (pd.Timestamp(window.end) + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    return start, end


def load_window_factor_frame(args: argparse.Namespace, window: ResearchWindow, output_dir: Path) -> pd.DataFrame:
    load_start, load_end = padded_dates(window)
    if args.start_time:
        load_start = min(pd.Timestamp(args.start_time), pd.Timestamp(load_start)).strftime("%Y-%m-%d")
    if args.end_time:
        load_end = max(pd.Timestamp(args.end_time), pd.Timestamp(load_end)).strftime("%Y-%m-%d")
    print(f"Loading window features: {window.name} {load_start} to {load_end}", flush=True)
    config = FactorResearchConfig(
        provider_uri=args.provider_uri,
        market=args.market,
        start_time=load_start,
        end_time=load_end,
        output_dir=output_dir,
        label=args.labels[0],
        quantiles=args.quantiles,
        min_count=args.min_count,
    )
    return slice_window(add_basic_factors(load_feature_frame(config)), window)


def build_window_samples(
    frame: pd.DataFrame,
    window: ResearchWindow,
    min_liquidity_bucket: int,
    min_tradability_score: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if window.tradability_dir is None:
        return frame, frame.iloc[0:0].copy()

    labels = load_tradability_labels(resolve_path(window.tradability_dir))
    with_labels = attach_tradability(frame, labels)
    return frame, tradable_only(with_labels, min_liquidity_bucket, min_tradability_score)


def legacy_time_slice_dir(root: Path, market: str, label: str, window: ResearchWindow) -> Path:
    return root / f"{market}_{label}_{window.name}"


def load_legacy_raw_summary(args: argparse.Namespace, windows: list[ResearchWindow]) -> pd.DataFrame:
    if args.no_reuse_legacy_time_slices:
        return pd.DataFrame()
    root = resolve_path(args.legacy_time_slice_root)
    frames = []
    for window in windows:
        for label in args.labels:
            path = legacy_time_slice_dir(root, args.market, label, window) / "factor_summary.csv"
            if not path.exists():
                continue
            frame = pd.read_csv(path)
            frame.insert(0, "sample", "raw")
            frame.insert(0, "window", window.name)
            frame.insert(2, "label", label)
            if "ic_dates" not in frame.columns:
                frame["ic_dates"] = pd.NA
            frames.append(frame)
    return concat_or_empty(frames)


def has_legacy_raw(summary: pd.DataFrame, window: ResearchWindow, label: str) -> bool:
    if summary.empty:
        return False
    rows = summary[
        (summary["window"] == window.name)
        & (summary["sample"] == "raw")
        & (summary["label"] == label)
    ]
    return not rows.empty


def write_report(
    args: argparse.Namespace,
    windows: list[ResearchWindow],
    summary: pd.DataFrame,
    monotonicity: pd.DataFrame,
    bucket_result: pd.DataFrame,
    correlation: pd.DataFrame,
    decisions: pd.DataFrame,
    output: Path,
) -> None:
    decision_counts = (
        decisions.groupby(["label", "decision"]).size().reset_index(name="count") if not decisions.empty else pd.DataFrame()
    )
    promoted = decisions[decisions["decision"] == "promote"] if not decisions.empty else pd.DataFrame()
    watch = decisions[decisions["decision"] == "watch"] if not decisions.empty else pd.DataFrame()
    main_summary = (
        summary[
            (summary["window"] == "main_research_2021_2023")
            & (summary["sample"] == "tradable_only")
            & (summary["label"] == "label_20d_t1")
        ]
        .sort_values("directional_mean_rank_ic", ascending=False)
        .head(20)
        if not summary.empty
        else pd.DataFrame()
    )
    mono_view = (
        monotonicity[
            (monotonicity["window"] == "main_research_2021_2023")
            & (monotonicity["sample"] == "tradable_only")
            & (monotonicity["label"] == "label_20d_t1")
        ]
        .sort_values("directional_spread", ascending=False)
        .head(20)
        if not monotonicity.empty
        else pd.DataFrame()
    )

    window_lines = [
        f"- `{window.name}`: `{window.start}` to `{window.end}`"
        + (f", tradability `{window.tradability_dir}`" if window.tradability_dir else ", raw only")
        for window in windows
    ]
    lines = [
        "# Factor Research V2 Report",
        "",
        f"- Provider URI: `{args.provider_uri}`",
        f"- Market: `{args.market}`",
        f"- Labels: `{','.join(args.labels)}`",
        f"- Quantiles: `{args.quantiles}`",
        f"- Min count per daily IC bucket: `{args.min_count}`",
        f"- Tradable filter: `can_buy == true`, `liquidity_bucket >= {args.min_liquidity_bucket}`, "
        f"`tradability_score >= {args.min_tradability_score}`",
        "",
        "## Windows",
        "",
        *window_lines,
        "",
        "## Candidate Decisions",
        "",
        markdown_table(
            decisions[
                [
                    "label",
                    "factor",
                    "category",
                    "expected_direction",
                    "decision",
                    "reason",
                    "main_directional_rank_ic",
                    "oos_directional_rank_ic",
                    "stability_score",
                    "monotonicity_score",
                    "directional_spread",
                    "redundancy_group",
                ]
            ].head(80)
            if not decisions.empty
            else pd.DataFrame()
        ),
        "",
        "## Decision Counts",
        "",
        markdown_table(decision_counts),
        "",
        "## Promoted Factors",
        "",
        markdown_table(
            promoted[
                [
                    "label",
                    "factor",
                    "category",
                    "main_directional_rank_ic",
                    "oos_directional_rank_ic",
                    "stability_score",
                    "monotonicity_score",
                    "directional_spread",
                ]
            ]
            if not promoted.empty
            else pd.DataFrame()
        ),
        "",
        "## Watch Factors",
        "",
        markdown_table(
            watch[["label", "factor", "category", "reason", "main_directional_rank_ic", "oos_directional_rank_ic"]]
            if not watch.empty
            else pd.DataFrame()
        ),
        "",
        "## Main Research Summary",
        "",
        markdown_table(
            main_summary[
                [
                    "factor",
                    "category",
                    "expected_direction",
                    "coverage",
                    "mean_rank_ic",
                    "directional_mean_rank_ic",
                    "rank_icir",
                    "ic_dates",
                ]
            ]
            if not main_summary.empty
            else pd.DataFrame()
        ),
        "",
        "## Main Research Monotonicity",
        "",
        markdown_table(
            mono_view[
                [
                    "factor",
                    "expected_direction",
                    "bottom_mean_label",
                    "top_mean_label",
                    "directional_spread",
                    "monotonicity_score",
                ]
            ]
            if not mono_view.empty
            else pd.DataFrame()
        ),
        "",
        "## Output Files",
        "",
        "- `factor_registry.csv`",
        "- `factor_summary.csv`",
        "- `factor_time_slice.csv`",
        "- `factor_bucket_ic.csv`",
        "- `factor_group_monotonicity.csv`",
        "- `factor_correlation.csv`",
        "- `factor_candidate_decision.csv`",
        "- `factor_research_v2_report.md`",
        "",
        "## Notes",
        "",
        "- `promote` means the factor is ready for model feature-pool experiments, not ready for live trading.",
        "- `watch` means the factor needs a clearer direction, richer neutralization, or more out-of-sample evidence.",
        "- `reject` means the current evidence is weak or redundant under these rules.",
        f"- Diagnostic rows: summary `{len(summary)}`, monotonicity `{len(monotonicity)}`, "
        f"bucket IC `{len(bucket_result)}`, correlation `{len(correlation)}`.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = enabled_specs(args.labels)
    windows = args.window or DEFAULT_WINDOWS

    legacy_summary = load_legacy_raw_summary(args, windows)
    if not legacy_summary.empty:
        print(f"Loaded legacy raw time-slice summaries: {len(legacy_summary):,} rows", flush=True)
    summaries: list[pd.DataFrame] = []
    time_slices: list[pd.DataFrame] = [legacy_summary] if not legacy_summary.empty else []
    monotonicity_frames: list[pd.DataFrame] = []
    bucket_frames: list[pd.DataFrame] = []
    correlation_frames: list[pd.DataFrame] = []

    for window in windows:
        missing_raw_labels = [label for label in args.labels if not has_legacy_raw(legacy_summary, window, label)]
        needs_tradable = window.tradability_dir is not None
        if not missing_raw_labels and not needs_tradable:
            continue

        window_frame = load_window_factor_frame(args, window, output_dir)
        print(f"Window {window.name}: {len(window_frame):,} raw rows", flush=True)
        raw_frame, tradable_frame = build_window_samples(
            window_frame,
            window,
            args.min_liquidity_bucket,
            args.min_tradability_score,
        )
        samples: list[tuple[str, pd.DataFrame, list[str]]] = []
        if missing_raw_labels:
            samples.append(("raw", raw_frame, missing_raw_labels))
        if needs_tradable:
            samples.append(("tradable_only", tradable_frame, args.labels))
        for sample_name, sample_frame, sample_labels in samples:
            print(f"  Sample {sample_name}: {len(sample_frame):,} rows", flush=True)
            for label in sample_labels:
                print(f"    Label {label}: IC/summary", flush=True)
                ic = information_coefficient(sample_frame, specs, label, args.min_count)
                summary = summarize_factors(sample_frame, ic, specs, label, window.name, sample_name)
                print(f"    Label {label}: monotonicity", flush=True)
                mono = group_monotonicity(
                    sample_frame,
                    specs,
                    label,
                    window.name,
                    sample_name,
                    args.quantiles,
                    args.min_count,
                )
                if label in args.bucket_ic_labels:
                    print(f"    Label {label}: bucket IC", flush=True)
                    bucket = bucket_ic(
                        sample_frame,
                        specs,
                        label,
                        window.name,
                        sample_name,
                        args.quantiles,
                        args.min_count,
                    )
                else:
                    bucket = pd.DataFrame()
                print(f"    Label {label}: correlation", flush=True)
                corr = factor_correlation(sample_frame, specs, window.name, sample_name, label)
                summaries.append(summary)
                time_slices.append(summary)
                monotonicity_frames.append(mono)
                bucket_frames.append(bucket)
                correlation_frames.append(corr)

    registry = registry_frame(specs)
    summary = concat_or_empty(([legacy_summary] if not legacy_summary.empty else []) + summaries)
    time_slice = concat_or_empty(time_slices)
    monotonicity = concat_or_empty(monotonicity_frames)
    bucket_result = concat_or_empty(bucket_frames)
    correlation = concat_or_empty(correlation_frames)
    decisions = decide_candidates(summary, monotonicity, correlation, specs)

    registry.to_csv(output_dir / "factor_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "factor_summary.csv", index=False, encoding="utf-8-sig")
    time_slice.to_csv(output_dir / "factor_time_slice.csv", index=False, encoding="utf-8-sig")
    bucket_result.to_csv(output_dir / "factor_bucket_ic.csv", index=False, encoding="utf-8-sig")
    monotonicity.to_csv(output_dir / "factor_group_monotonicity.csv", index=False, encoding="utf-8-sig")
    correlation.to_csv(output_dir / "factor_correlation.csv", index=False, encoding="utf-8-sig")
    decisions.to_csv(output_dir / "factor_candidate_decision.csv", index=False, encoding="utf-8-sig")
    write_report(
        args,
        windows,
        summary,
        monotonicity,
        bucket_result,
        correlation,
        decisions,
        output_dir / "factor_research_v2_report.md",
    )
    print(f"Factor research V2 outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run factor research V2 diagnostics and candidate selection.")
    parser.add_argument("--provider-uri", default=DEFAULT_PROVIDER_URI)
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--labels", type=parse_labels, default=parse_labels(DEFAULT_LABELS))
    parser.add_argument("--bucket-ic-labels", type=parse_optional_labels, default=parse_optional_labels(DEFAULT_BUCKET_IC_LABELS))
    parser.add_argument("--start-time", default=None, help="Optional override for feature loading start date.")
    parser.add_argument("--end-time", default=None, help="Optional override for feature loading end date.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_research_v2/liquid2000_default"))
    parser.add_argument("--legacy-time-slice-root", type=Path, default=DEFAULT_LEGACY_TIME_SLICE_ROOT)
    parser.add_argument("--no-reuse-legacy-time-slices", action="store_true")
    parser.add_argument("--quantiles", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=50)
    parser.add_argument("--min-liquidity-bucket", type=int, default=3)
    parser.add_argument("--min-tradability-score", type=float, default=75.0)
    parser.add_argument(
        "--window",
        type=parse_window,
        action="append",
        help="Optional research window: name,start,end[,tradability_dir]. Can be repeated.",
    )
    return parser


def main() -> None:
    freeze_support()
    args = build_parser().parse_args()
    run(args)


if __name__ == "__main__":
    main()
