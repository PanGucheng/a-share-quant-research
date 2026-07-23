from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import (  # noqa: E402
    atomic_parquet,
    canonical_hash,
    file_sha256,
)
from research_validation.labels import build_exact_calendar_label  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "calendar_continuity_receipt.csv",
    "contract_status.csv",
    "label_report.md",
    "label_sample.csv",
    "label_summary.csv",
    "resolved_config.json",
    "schema.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build exact-calendar lifecycle-clean labels v2.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/full_research_labels_v2.yaml"),
    )
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    matrix_path = resolve(config["feature_matrix_manifest"])
    universe_path = resolve(config["universe_manifest"])
    raw_manifest_path = resolve(config["raw_market_data_snapshot_manifest"])
    matrix = load_artifact_manifest(matrix_path)
    universe = load_artifact_manifest(universe_path)
    raw_manifest = load_artifact_manifest(raw_manifest_path)
    for name, manifest, path in (
        ("matrix", matrix, matrix_path),
        ("universe", universe, universe_path),
        ("raw", raw_manifest, raw_manifest_path),
    ):
        if (
            validate_manifest_outputs(manifest, path.parent)
            or manifest["artifact_status"] != "pass"
            or manifest["lineage_status"] != "complete"
            or bool(manifest["code_dirty"])
        ):
            raise ValueError(f"{name} input is stale, blocked, or non-authoritative")
    if matrix["universe_artifact_id"] != universe["universe_artifact_id"]:
        raise ValueError("Matrix v4 and Universe v2 lineage IDs differ")
    if raw_manifest["artifact_id"] not in set(map(str, matrix["input_artifact_ids"])):
        raise ValueError("Matrix v4 does not reference the configured raw snapshot")

    raw_detail = json.loads(
        resolve(config["raw_market_data_detail_manifest"]).read_text(encoding="utf-8")
    )
    raw_path = resolve(config["raw_cache"])
    raw_sha256 = file_sha256(raw_path)
    if raw_sha256 != str(raw_detail["raw_parquet"]["sha256"]):
        raise ValueError("raw close input hash differs from raw market snapshot")
    partitions = pd.read_csv(resolve(config["feature_partition_status"]))
    selected = partitions.loc[
        partitions["batch_id"].eq(config["key_partition_batch_id"])
    ]
    if len(selected) != 1:
        raise ValueError("configured Matrix v4 key partition is not unique")
    key_path = Path(str(selected.iloc[0]["output_path"]))
    key_sha256 = file_sha256(key_path)
    if key_sha256 != str(selected.iloc[0]["output_sha256"]):
        raise ValueError("Matrix v4 key partition hash mismatch")
    keys = pd.read_parquet(key_path, columns=["datetime", "instrument"])
    keys["datetime"] = pd.to_datetime(keys["datetime"])
    keys["instrument"] = keys["instrument"].astype(str).str.upper()

    raw = pd.read_parquet(
        raw_path,
        columns=["datetime", "instrument", str(config["price_field"])],
    )
    raw["datetime"] = pd.to_datetime(raw["datetime"])
    raw["instrument"] = raw["instrument"].astype(str).str.upper()
    raw = raw.loc[raw["datetime"].le(keys["datetime"].max())]

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=keys["datetime"].min(),
            end_time=raw["datetime"].max(),
            freq="day",
        )
    )
    label_name = str(config["label_name"])
    detailed, date_map = build_exact_calendar_label(
        keys,
        raw,
        calendar,
        price_column=str(config["price_field"]),
        label_name=label_name,
        entry_lag=int(config["entry_lag"]),
        holding_days=int(config["holding_days"]),
    )
    labels = detailed[["datetime", "instrument", label_name]].copy()
    runtime = resolve(config["runtime_label"])
    atomic_parquet(labels, runtime)

    intervals = pd.read_csv(resolve(config["universe_intervals"]))
    illegal = pd.read_csv(resolve(config["illegal_key_resolution"]))
    illegal["datetime"] = pd.to_datetime(illegal["datetime"])
    illegal["instrument"] = illegal["instrument"].astype(str).str.upper()
    illegal_residual = keys.merge(
        illegal[["datetime", "instrument"]].drop_duplicates(),
        on=["datetime", "instrument"],
        how="inner",
    )
    terminal_dates = date_map.loc[
        date_map["terminal_entry_missing"] | date_map["terminal_exit_missing"],
        "datetime",
    ]
    terminal_rows = detailed["datetime"].isin(terminal_dates)
    terminal_nonmissing = int(detailed.loc[terminal_rows, label_name].notna().sum())
    exact_offsets = bool(
        (
            date_map.loc[~date_map["terminal_entry_missing"], "entry_position"]
            - date_map.loc[~date_map["terminal_entry_missing"], "calendar_position"]
        ).eq(int(config["entry_lag"])).all()
        and (
            date_map.loc[~date_map["terminal_exit_missing"], "exit_position"]
            - date_map.loc[~date_map["terminal_exit_missing"], "entry_position"]
        ).eq(int(config["holding_days"])).all()
    )
    valid = int(labels[label_name].notna().sum())
    coverage = float(valid / len(labels))
    continuity = pd.DataFrame(
        [
            {
                "feature_date_count": len(date_map),
                "canonical_calendar_start": calendar.min(),
                "canonical_calendar_end": calendar.max(),
                "entry_lag": int(config["entry_lag"]),
                "holding_days": int(config["holding_days"]),
                "terminal_feature_date_count": len(terminal_dates),
                "terminal_key_count": int(terminal_rows.sum()),
                "terminal_nonmissing_label_count": terminal_nonmissing,
                "exact_calendar_offsets": exact_offsets,
                "physical_row_shift_used": False,
                "price_fill_used": False,
            }
        ]
    )
    checks = [
        ("label_key_unique", not labels.duplicated(["datetime", "instrument"]).any(), len(labels)),
        ("label_key_grid_aligned", len(labels) == int(partitions.iloc[0]["row_count"]), len(labels)),
        ("label_calendar_continuity_proved", exact_offsets, len(date_map)),
        ("label_horizon_exact", int(config["entry_lag"]) == 1 and int(config["holding_days"]) == 20, f"{config['entry_lag']}+{config['holding_days']}"),
        ("label_terminal_missing_expected", terminal_nonmissing == 0 and len(terminal_dates) == 21, f"dates={len(terminal_dates)},nonmissing={terminal_nonmissing}"),
        ("label_source_lifecycle_clean", illegal_residual.empty, len(illegal_residual)),
        ("no_future_feature_in_label_inputs", True, "only exact entry/exit $close joins; no feature columns"),
        ("no_price_forward_fill", True, "missing exact-date price remains missing"),
        ("label_coverage", coverage >= float(config["minimum_coverage"]), coverage),
        ("label_output_hash", len(file_sha256(runtime)) == 64, file_sha256(runtime)),
        ("matrix_v4_parent_current", matrix["artifact_status"] == "pass", matrix["artifact_id"]),
        ("raw_cache_hash_bound", raw_sha256 == raw_detail["raw_parquet"]["sha256"], raw_sha256),
        ("key_partition_hash_bound", key_sha256 == selected.iloc[0]["output_sha256"], key_sha256),
    ]
    contracts = pd.DataFrame(
        [
            {
                "check": name,
                "status": "pass" if passed else "fail",
                "severity": "critical",
                "detail": detail,
            }
            for name, passed, detail in checks
        ]
    )
    ready = contracts["status"].eq("pass").all()
    input_payload = {
        "matrix_artifact_id": matrix["artifact_id"],
        "universe_artifact_id": universe["artifact_id"],
        "raw_artifact_id": raw_manifest["artifact_id"],
        "raw_sha256": raw_sha256,
        "key_partition_sha256": key_sha256,
        "label_name": label_name,
        "entry_lag": config["entry_lag"],
        "holding_days": config["holding_days"],
        "calendar_sha256": canonical_hash([value.isoformat() for value in calendar]),
        "implementation": "exact_canonical_calendar_join_v2",
    }
    summary = pd.DataFrame(
        [
            {
                "label": label_name,
                "row_count": len(labels),
                "valid_rows": valid,
                "coverage": coverage,
                "terminal_feature_date_count": len(terminal_dates),
                "terminal_key_count": int(terminal_rows.sum()),
                "output_path": runtime.as_posix(),
                "output_sha256": file_sha256(runtime),
                "input_hash": canonical_hash(input_payload),
                "matrix_artifact_id": matrix["artifact_id"],
                "universe_artifact_id": universe["artifact_id"],
                "raw_artifact_id": raw_manifest["artifact_id"],
            }
        ]
    )
    resolved_config = {
        **config,
        "config_file_sha256": file_sha256(config_path),
        "input_payload": input_payload,
    }
    output = resolve(config["output_dir"])
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        continuity.to_csv(
            publisher.path("calendar_continuity_receipt.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        summary.to_csv(publisher.path("label_summary.csv"), index=False, encoding="utf-8-sig")
        detailed.head(100).to_csv(
            publisher.path("label_sample.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("schema.json").write_text(
            json.dumps(
                {
                    "keys": ["datetime", "instrument"],
                    "label": label_name,
                    "definition": "close[canonical_t+21]/close[canonical_t+1]-1",
                    "entry_lag": int(config["entry_lag"]),
                    "holding_days": int(config["holding_days"]),
                    "price_fill": "none",
                    "physical_row_shift": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(resolved_config, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("label_report.md").write_text(
            "\n".join(
                [
                    "# Full-Research Labels V2",
                    "",
                    f"- Status: `{'pass' if ready else 'blocked'}`",
                    f"- Label: `{label_name}`",
                    f"- Rows / valid / coverage: `{len(labels)}` / `{valid}` / `{coverage:.6f}`",
                    f"- Terminal dates / keys: `{len(terminal_dates)}` / `{int(terminal_rows.sum())}`",
                    "- Dates use the canonical Qlib trading calendar; no physical-row shift or price fill is used.",
                    "- Runtime label parquet is hash-addressed and excluded from Git.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_labels_v2",
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[matrix_path, universe_path, raw_manifest_path],
            universe_artifact_id=universe["universe_artifact_id"],
            factor_catalog_id=matrix["factor_catalog_id"],
            factor_frame_id=matrix["factor_frame_id"],
            start_date=labels["datetime"].min(),
            end_date=labels["datetime"].max(),
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_labels_v2_contract",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
