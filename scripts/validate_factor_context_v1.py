from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.context.listing import attach_listing_age
from factor_research.context.universe import attach_membership


DEFAULT_OUTPUT = Path("outputs/factor_context_v1/main_research_2021_2023")
REQUIRED_FILES = {
    "benchmark_returns.csv",
    "context_run.json",
    "factor_context_v1_report.md",
    "listing_age_asof.csv",
    "universe_membership_asof.csv",
    "universe_membership_counts.csv",
}


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def validate_synthetic_boundaries() -> None:
    intervals = pd.DataFrame(
        {
            "instrument": ["SH600000", "SH600000"],
            "start": pd.to_datetime(["2021-01-02", "2021-01-06"]),
            "end": pd.to_datetime(["2021-01-04", "2021-01-07"]),
        }
    )
    frame = pd.DataFrame(
        {
            "datetime": pd.date_range("2021-01-01", "2021-01-08"),
            "instrument": "sh600000",
        }
    )
    attached = attach_membership(frame, intervals, "is_member")
    expected = [False, True, True, True, False, True, True, False]
    if attached["is_member"].tolist() != expected:
        raise ValueError("Point-in-time membership does not preserve inclusive interval boundaries")

    dates = pd.DataFrame(
        {
            "instrument": ["SH600000"],
            "listing_date_proxy": pd.to_datetime(["2021-01-02"]),
        }
    )
    age = attach_listing_age(frame.iloc[[0, 1, 7]], dates)
    actual = age["listing_age_days"].tolist()
    if not (np.isnan(actual[0]) and actual[1:] == [0.0, 6.0]):
        raise ValueError(f"Listing-age boundary result is unexpected: {actual}")


def validate_benchmarks(output_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(output_dir / "benchmark_returns.csv", parse_dates=["datetime"])
    required = {
        "datetime",
        "benchmark",
        "instrument",
        "close",
        "daily_return",
        "forward_10d_t1",
        "forward_20d_t1",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"benchmark_returns.csv is missing columns: {sorted(missing)}")
    if frame.empty or frame.duplicated(["benchmark", "datetime"]).any():
        raise ValueError("Benchmark output is empty or has duplicate benchmark/date rows")

    for benchmark, group in frame.groupby("benchmark"):
        group = group.sort_values("datetime").reset_index(drop=True)
        expected_daily = group["close"].pct_change(fill_method=None)
        comparable_daily = group["daily_return"].notna() & expected_daily.notna()
        if not np.allclose(
            group.loc[comparable_daily, "daily_return"],
            expected_daily.loc[comparable_daily],
            rtol=1e-6,
            atol=2e-7,
        ):
            raise ValueError(f"Daily return formula mismatch for {benchmark}")

        expected_forward = group["close"].shift(-11) / group["close"].shift(-1) - 1
        comparable_forward = expected_forward.notna()
        if not np.allclose(
            group.loc[comparable_forward, "forward_10d_t1"],
            expected_forward.loc[comparable_forward],
            rtol=1e-6,
            atol=2e-7,
        ):
            raise ValueError(f"T+1 forward return formula mismatch for {benchmark}")
    return frame


def validate_membership(output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = pd.read_csv(output_dir / "universe_membership_counts.csv", parse_dates=["datetime"])
    as_of = pd.read_csv(output_dir / "universe_membership_asof.csv", parse_dates=["start", "end"])
    if counts.empty or as_of.empty:
        raise ValueError("Universe membership outputs must not be empty")
    if counts.duplicated(["universe", "datetime"]).any():
        raise ValueError("universe_membership_counts.csv contains duplicate universe/date rows")
    if as_of.duplicated(["universe", "instrument"]).any():
        raise ValueError("universe_membership_asof.csv contains duplicate universe/instrument rows")

    end_counts = counts.loc[counts.groupby("universe")["datetime"].idxmax()].set_index("universe")["member_count"]
    snapshot_counts = as_of.groupby("universe").size()
    if not end_counts.sort_index().equals(snapshot_counts.sort_index()):
        raise ValueError("End-date membership counts disagree with the exported snapshot")
    return counts, as_of


def validate_listing_age(output_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        output_dir / "listing_age_asof.csv",
        parse_dates=["datetime", "listing_date_proxy"],
    )
    if frame.empty or frame["instrument"].duplicated().any():
        raise ValueError("listing_age_asof.csv is empty or contains duplicate instruments")
    expected = (frame["datetime"] - frame["listing_date_proxy"]).dt.days
    if not np.array_equal(frame["listing_age_days"].to_numpy(), expected.to_numpy()):
        raise ValueError("Listing age does not equal as-of date minus listing-date proxy")
    if frame["listing_age_days"].lt(0).any() or frame["listing_age_bucket"].isna().any():
        raise ValueError("Active instruments must have non-negative listing age and a bucket")
    return frame


def validate(output_dir: Path) -> None:
    output_dir = resolve_path(output_dir)
    missing = sorted(name for name in REQUIRED_FILES if not (output_dir / name).exists())
    if missing:
        raise FileNotFoundError(f"Missing factor context outputs in {output_dir}: {missing}")

    validate_synthetic_boundaries()
    benchmarks = validate_benchmarks(output_dir)
    counts, membership = validate_membership(output_dir)
    listing = validate_listing_age(output_dir)
    print(
        "Validated factor context V1: "
        f"{benchmarks['benchmark'].nunique()} benchmarks, "
        f"{counts['universe'].nunique()} universes, "
        f"{len(membership)} end-date memberships, "
        f"{len(listing)} listing-age rows"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate point-in-time factor context V1 outputs.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    validate(args.output_dir)


if __name__ == "__main__":
    main()
