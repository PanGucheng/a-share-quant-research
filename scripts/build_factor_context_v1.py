from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.context.benchmark import load_benchmark_returns
from factor_research.context.listing import listing_age_as_of
from factor_research.context.universe import active_members, load_instrument_intervals, membership_counts


DEFAULT_CONFIG = Path("configs/factor_context_v1.yaml")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_calendar(provider: Path, start: str, end: str) -> pd.DatetimeIndex:
    calendar_path = provider / "calendars" / "day.txt"
    values = pd.to_datetime([line.strip() for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()])
    return pd.DatetimeIndex(values[(values >= pd.Timestamp(start)) & (values <= pd.Timestamp(end))])


def write_report(
    config: dict,
    benchmark: pd.DataFrame,
    counts: pd.DataFrame,
    membership_asof: pd.DataFrame,
    listing_age: pd.DataFrame,
    output: Path,
) -> None:
    benchmark_summary = benchmark.groupby("benchmark").agg(
        rows=("datetime", "count"),
        first_date=("datetime", "min"),
        last_date=("datetime", "max"),
        daily_return_coverage=("daily_return", lambda values: values.notna().mean()),
        forward_20d_coverage=("forward_20d_t1", lambda values: values.notna().mean()),
    ).reset_index()
    universe_summary = counts.groupby("universe")["member_count"].agg(["min", "mean", "max"]).reset_index()
    listing_summary = (
        listing_age.groupby("listing_age_bucket", dropna=False, observed=False)
        .size()
        .reset_index(name="instrument_count")
    )

    def table(frame: pd.DataFrame) -> str:
        view = frame.fillna("").astype(str)
        lines = [
            "| " + " | ".join(view.columns) + " |",
            "| " + " | ".join("---" for _ in view.columns) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in view.itertuples(index=False, name=None))
        return "\n".join(lines)

    lines = [
        "# Factor Context V1 Report",
        "",
        f"- Provider: `{config['provider_uri']}`",
        f"- Window: `{config['start']}` to `{config['end']}`",
        "- Membership uses Qlib point-in-time start/end intervals.",
        "- Listing age uses the earliest interval available in the provider as a proxy.",
        "",
        "## Benchmark Coverage",
        "",
        table(benchmark_summary),
        "",
        "## Universe Member Counts",
        "",
        table(universe_summary),
        "",
        "## Membership At End Date",
        "",
        table(membership_asof.groupby("universe").size().reset_index(name="member_count")),
        "",
        "## Listing Age At End Date",
        "",
        table(listing_summary),
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> Path:
    config = yaml.safe_load(resolve_path(config_path).read_text(encoding="utf-8"))
    provider = Path(config["provider_uri"])
    output_dir = resolve_path(Path(config["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    calendar = load_calendar(provider, str(config["start"]), str(config["end"]))

    benchmark = load_benchmark_returns(
        str(provider),
        {str(name): str(code) for name, code in config["benchmarks"].items()},
        str(config["start"]),
        str(config["end"]),
    )
    benchmark.to_csv(output_dir / "benchmark_returns.csv", index=False, encoding="utf-8-sig")

    count_frames = []
    asof_frames = []
    for universe in config["universes"]:
        intervals = load_instrument_intervals(provider / "instruments" / f"{universe}.txt")
        count_frames.append(membership_counts(intervals, calendar, str(universe)))
        active = active_members(intervals, str(config["end"]))[["instrument", "start", "end"]]
        active.insert(0, "universe", str(universe))
        asof_frames.append(active)
    counts = pd.concat(count_frames, ignore_index=True)
    membership_asof = pd.concat(asof_frames, ignore_index=True)
    counts.to_csv(output_dir / "universe_membership_counts.csv", index=False, encoding="utf-8-sig")
    membership_asof.to_csv(output_dir / "universe_membership_asof.csv", index=False, encoding="utf-8-sig")

    listing_intervals = load_instrument_intervals(provider / "instruments" / f"{config['listing_source']}.txt")
    listing_age = listing_age_as_of(listing_intervals, str(config["listing_age_as_of"]))
    listing_age.to_csv(output_dir / "listing_age_asof.csv", index=False, encoding="utf-8-sig")

    write_report(config, benchmark, counts, membership_asof, listing_age, output_dir / "factor_context_v1_report.md")
    (output_dir / "context_run.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    print(f"Factor context V1 written to {output_dir}")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build point-in-time factor evaluation context from the Qlib provider.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
