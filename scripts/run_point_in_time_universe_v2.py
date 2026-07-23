from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.context.universe import load_instrument_intervals  # noqa: E402
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    content_reference_id,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402
from universes.interval_writer import (  # noqa: E402
    intersect_membership_with_lifecycle,
    snapshots_to_intervals,
    write_qlib_instruments,
)
from universes.point_in_time_universe import (  # noqa: E402
    build_point_in_time_universe,
    monthly_selection_dates,
)
from universes.universe_audit import audit_universe  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "illegal_key_resolution.csv",
    "lifecycle_difference.csv",
    "qlib_instruments.txt",
    "resolved_config.json",
    "universe_change_log.csv",
    "universe_intervals.csv",
    "universe_membership_snapshots.csv",
    "universe_report.md",
    "universe_selection_metrics.csv",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def markdown_table(frame: pd.DataFrame) -> str:
    rendered = frame.fillna("").astype(str)
    columns = list(rendered.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rendered.itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(str(value).replace("|", "\\|") for value in row)
            + " |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build lifecycle-clean point-in-time universe v2 by intersecting "
            "rolling membership with exact source lifecycle."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/point_in_time_universe_v2.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    source_path = resolve(config["source_intervals"])
    resolved_config = {
        **config,
        "source_intervals_sha256": file_sha256(source_path),
        "lifecycle_intersection_policy": (
            "rolling_universe_interval_intersection_source_lifecycle_interval"
        ),
    }
    code_state = capture_code_state(PROJECT_ROOT)
    output = resolve(config["output_dir"])

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar_end = (
        pd.Timestamp(config["end_date"]) + pd.Timedelta(days=10)
    ).strftime("%Y-%m-%d")
    full_calendar = pd.DatetimeIndex(
        D.calendar(start_time="2000-01-01", end_time=calendar_end, freq="day")
    )
    selections = monthly_selection_dates(
        full_calendar, config["start_date"], config["end_date"]
    )
    end_date = pd.Timestamp(config["end_date"])
    selections = pd.DatetimeIndex(
        [
            date
            for date in selections
            if len(full_calendar[(full_calendar > date) & (full_calendar <= end_date)])
            > 0
        ]
    )
    if selections.empty:
        raise ValueError(
            "no selection date has an effective trading date inside the configured range"
        )
    first_position = full_calendar.searchsorted(selections[0])
    fetch_start = full_calendar[
        max(0, first_position - int(config["lookback_trading_days"]) + 1)
    ]
    source = load_instrument_intervals(source_path)
    symbols = sorted(
        source.loc[
            (source["start"] <= selections[-1])
            & (source["end"] >= fetch_start),
            "instrument",
        ].unique()
    )
    raw = D.features(
        symbols,
        ["$amount"],
        start_time=str(fetch_start.date()),
        end_time=str(selections[-1].date()),
        freq="day",
    ).reset_index()
    amount = raw.rename(columns={"$amount": "amount"})
    snapshots, metrics, changes = build_point_in_time_universe(
        amount,
        source,
        full_calendar,
        selections,
        lookback_days=int(config["lookback_trading_days"]),
        min_valid_days=int(config["minimum_valid_days"]),
        min_listing_days=int(config["minimum_listing_trading_days"]),
        top_n=int(config["top_n"]),
    )
    first_snapshot, _, _ = build_point_in_time_universe(
        amount.loc[amount["datetime"] <= selections[0]],
        source,
        full_calendar,
        selections[:1],
        lookback_days=int(config["lookback_trading_days"]),
        min_valid_days=int(config["minimum_valid_days"]),
        min_listing_days=int(config["minimum_listing_trading_days"]),
        top_n=int(config["top_n"]),
    )
    expected_first = set(
        snapshots.loc[
            snapshots["selection_date"] == selections[0], "instrument"
        ]
    )
    truncated_first = set(first_snapshot["instrument"])
    historical_mutation_count = len(
        expected_first.symmetric_difference(truncated_first)
    )
    final_trading_date = full_calendar[
        full_calendar <= pd.Timestamp(config["end_date"])
    ][-1]
    rolling_intervals = snapshots_to_intervals(
        snapshots, full_calendar, final_trading_date
    )
    intervals, lifecycle_differences, removed_keys = (
        intersect_membership_with_lifecycle(
            rolling_intervals, source, full_calendar
        )
    )

    with StageOutputPublisher(output, CONTROLLED) as publisher:
        qlib_file = publisher.path("qlib_instruments.txt")
        write_qlib_instruments(intervals, qlib_file)
        contract = audit_universe(
            snapshots,
            metrics,
            intervals,
            qlib_file,
            historical_mutation_count,
            source_intervals=source,
            lifecycle_differences=lifecycle_differences,
            removed_keys=removed_keys,
        )
        snapshots.to_csv(
            publisher.path("universe_membership_snapshots.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        metrics.to_csv(
            publisher.path("universe_selection_metrics.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        intervals.to_csv(
            publisher.path("universe_intervals.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        changes.to_csv(
            publisher.path("universe_change_log.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        lifecycle_differences.to_csv(
            publisher.path("lifecycle_difference.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        removed_keys.to_csv(
            publisher.path("illegal_key_resolution.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        contract.to_csv(
            publisher.path("contract_status.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(
                resolved_config, ensure_ascii=False, indent=2, default=str
            )
            + "\n",
            encoding="utf-8",
        )
        publisher.path("universe_report.md").write_text(
            "\n".join(
                [
                    "# Point-In-Time Universe V2",
                    "",
                    f"- Profile: `{config['profile']}`",
                    f"- Selection months: `{len(selections)}`",
                    f"- Snapshot rows: `{len(snapshots)}`",
                    f"- Rolling interval rows: `{len(rolling_intervals)}`",
                    f"- Lifecycle-clean interval rows: `{len(intervals)}`",
                    f"- Corrected interval rows: `{len(lifecycle_differences)}`",
                    f"- Removed illegal keys: `{len(removed_keys)}`",
                    "",
                    markdown_table(contract),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        compact_files = [
            publisher.path(name)
            for name in CONTROLLED
            if name != "artifact_manifest.json"
        ]
        ready = contract.loc[
            contract["severity"].eq("critical"), "status"
        ].eq("pass").all()
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="point_in_time_universe_v2",
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=compact_files,
            code_state=code_state,
            universe_artifact_id=content_reference_id(
                "universe-v2",
                [
                    publisher.path("universe_membership_snapshots.csv"),
                    publisher.path("universe_intervals.csv"),
                ],
            ),
            start_date=snapshots["effective_date"].min(),
            end_date=intervals["end_date"].max(),
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_lifecycle_contract",
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
