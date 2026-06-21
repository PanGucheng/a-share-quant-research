from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("outputs/factor_evaluation_v4/context_smoke_rev5")
SYSTEMS = ("alphalens_reloaded", "jqfactor_analyzer")
RETURN_MODES = ("raw_return", "benchmark_excess_return")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def normalize_ic(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).rename(columns={"period_10": "10D", "period_20": "20D"})
    required = {"date", "group", "10D", "20D"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing IC columns: {sorted(missing)}")
    return frame.sort_values(["date", "group"]).reset_index(drop=True)[["date", "group", "10D", "20D"]]


def assert_same_ic(left: pd.DataFrame, right: pd.DataFrame, message: str) -> None:
    if not left[["date", "group"]].equals(right[["date", "group"]]):
        raise ValueError(f"{message}: date/group keys differ")
    for column in ["10D", "20D"]:
        left_values = pd.to_numeric(left[column], errors="coerce")
        right_values = pd.to_numeric(right[column], errors="coerce")
        if not np.array_equal(left_values.isna(), right_values.isna()):
            raise ValueError(f"{message}: {column} missing-value masks differ")
        mask = left_values.notna()
        if not np.allclose(left_values[mask], right_values[mask], rtol=1e-12, atol=1e-12):
            raise ValueError(f"{message}: {column} values differ")


def validate_metric_completeness(context_dir: Path, factors: list[str]) -> None:
    for system in SYSTEMS:
        for factor in factors:
            for return_mode in RETURN_MODES:
                target = context_dir / system / factor / return_mode / "index_segment"
                returns_path = target / "mean_return_by_quantile_by_group.csv"
                if not returns_path.exists():
                    raise FileNotFoundError(returns_path)
                returns = pd.read_csv(returns_path)
                value_columns = [column for column in returns.columns if column not in {"factor_quantile", "group"}]
                if not value_columns or returns[value_columns].apply(pd.to_numeric, errors="coerce").isna().any().any():
                    raise ValueError(f"Incomplete grouped return output: {returns_path}")


def validate(output_dir: Path) -> None:
    output_dir = resolve_path(output_dir)
    context_dir = output_dir / "context"
    coverage_path = context_dir / "context_coverage.csv"
    status_path = context_dir / "context_evaluator_status.csv"
    metric_index_path = context_dir / "context_metric_index.csv"
    if not coverage_path.exists() or not status_path.exists() or not metric_index_path.exists():
        raise FileNotFoundError(f"Missing context coverage, status, or metric index under {context_dir}")

    coverage = pd.read_csv(coverage_path)
    integrity = coverage[coverage["dimension"].eq("integrity")]
    if not integrity.empty and integrity["row_count"].ne(0).any():
        raise ValueError(f"Context integrity checks failed:\n{integrity.to_string(index=False)}")
    segments = coverage[coverage["dimension"].eq("index_segment") & coverage["row_count"].gt(0)]
    if len(segments) < 2:
        raise ValueError("index_segment must contain at least two populated groups")

    status = pd.read_csv(status_path)
    failed = status[status["status"].eq("failed")]
    if not failed.empty:
        raise ValueError(f"Context evaluator contains failed steps:\n{failed.to_string(index=False)}")
    factors = sorted(status["factor"].dropna().unique().tolist())
    validate_metric_completeness(context_dir, factors)
    metric_index = pd.read_csv(metric_index_path)
    if metric_index.empty or metric_index["value"].isna().any():
        raise ValueError("context_metric_index.csv is empty or contains missing metric values")
    expected_systems = set(SYSTEMS)
    if set(metric_index["system"].unique()) != expected_systems:
        raise ValueError("context metric index does not contain both source systems")

    for factor in factors:
        alpha_raw = normalize_ic(
            context_dir
            / "alphalens_reloaded"
            / factor
            / "raw_return"
            / "index_segment"
            / "information_coefficient_by_group.csv"
        )
        jq_raw = normalize_ic(
            context_dir
            / "jqfactor_analyzer"
            / factor
            / "raw_return"
            / "index_segment"
            / "information_coefficient_by_group.csv"
        )
        assert_same_ic(alpha_raw, jq_raw, f"{factor} cross-system raw Rank IC")

        for system in SYSTEMS:
            raw = normalize_ic(
                context_dir / system / factor / "raw_return" / "index_segment" / "information_coefficient_by_group.csv"
            )
            excess = normalize_ic(
                context_dir
                / system
                / factor
                / "benchmark_excess_return"
                / "index_segment"
                / "information_coefficient_by_group.csv"
            )
            assert_same_ic(raw, excess, f"{factor} {system} raw/excess Rank IC invariance")

    print(
        f"Validated factor evaluation context: {len(factors)} factors, "
        f"{len(segments)} index segments, no failed context steps"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate grouped open-source factor context outputs.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    validate(args.output_dir)


if __name__ == "__main__":
    main()
