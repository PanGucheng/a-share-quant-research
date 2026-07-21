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

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.input_provenance import (  # noqa: E402
    git_repo_receipt,
    inventory_tree_hash,
    normalized_required_fields,
    provider_file_inventory,
    raw_parquet_receipt,
)
from research_validation.lineage import (  # noqa: E402
    canonical_json,
    capture_code_state,
    load_artifact_manifest,
    sha256_text,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = (
    "artifact_manifest.json",
    "contract_status.csv",
    "field_schema.json",
    "provider_file_inventory.csv",
    "raw_market_data_manifest.json",
    "raw_market_data_report.md",
    "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact raw/provider inputs for the 669-factor matrix.")
    parser.add_argument("--config", type=Path, default=Path("configs/raw_market_data_snapshot_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}

    provider_root = resolve(config["provider_uri"])
    raw_path = resolve(config["raw_cache_path"])
    intervals = pd.read_csv(resolve(config["universe_intervals"]))
    factor_inventory = pd.read_csv(resolve(config["factor_inventory"]))
    universe_manifest = load_artifact_manifest(resolve(config["universe_manifest"]))
    catalog_manifest = load_artifact_manifest(resolve(config["factor_catalog_manifest"]))
    parent_issues = [
        *validate_manifest_outputs(universe_manifest, resolve(config["universe_manifest"]).parent),
        *validate_manifest_outputs(catalog_manifest, resolve(config["factor_catalog_manifest"]).parent),
    ]
    symbols = sorted(intervals["instrument"].astype(str).str.upper().unique())
    fields = normalized_required_fields(factor_inventory["required_fields"])
    raw_fields = [str(item) for item in config["raw_required_columns"] if str(item).startswith("$")]
    fields = sorted(set(fields).union(raw_fields))

    provider_inventory = provider_file_inventory(
        provider_root,
        symbols,
        fields,
        calendar_files=[str(item) for item in config["calendar_files"]],
        instrument_files=[str(item) for item in config["instrument_files"]],
        workers=int(config.get("hash_workers", 8)),
    )
    provider_tree = inventory_tree_hash(provider_inventory)
    raw_receipt, field_schema = raw_parquet_receipt(raw_path, [str(item) for item in config["raw_required_columns"]])
    expected_instrument_hash = sha256_text(canonical_json(symbols))
    qlib_receipt = git_repo_receipt(resolve(config["qlib_repo"]), ["qlib/contrib/data/loader.py"])
    provider_snapshot_id = f"provider-snapshot:{provider_tree}"
    raw_market_data_id = "raw-market-data:" + sha256_text(
        canonical_json(
            {
                "provider_snapshot_id": provider_snapshot_id,
                "raw_sha256": raw_receipt["sha256"],
                "universe_artifact_id": universe_manifest["artifact_id"],
                "factor_catalog_artifact_id": catalog_manifest["artifact_id"],
                "required_fields": fields,
            }
        )
    )
    custom_manifest = {
        "schema_version": 1,
        "raw_market_data_id": raw_market_data_id,
        "provider_snapshot_id": provider_snapshot_id,
        "provider_uri": str(config["provider_uri"]),
        "provider_resolved_path": provider_root.as_posix(),
        "provider_tree_sha256": provider_tree,
        "provider_file_count": int(len(provider_inventory)),
        "provider_missing_file_count": int((~provider_inventory["exists"]).sum()),
        "required_fields": fields,
        "calendar_files": [str(item) for item in config["calendar_files"]],
        "instrument_files": [str(item) for item in config["instrument_files"]],
        "raw_parquet": raw_receipt,
        "qlib_commit": qlib_receipt["commit"],
        "qlib_commit_tree": qlib_receipt["commit_tree"],
        "qlib_dirty_paths": qlib_receipt["dirty_paths"],
        "universe_artifact_id": universe_manifest["artifact_id"],
        "factor_catalog_artifact_id": catalog_manifest["artifact_id"],
    }

    checks = [
        contract_row("parent_artifacts_fresh", not parent_issues, len(parent_issues), 0),
        contract_row(
            "provider_files_complete",
            bool(provider_inventory["exists"].all()),
            int((~provider_inventory["exists"]).sum()),
            0,
        ),
        contract_row(
            "provider_inventory_count",
            len(provider_inventory)
            == len(symbols) * len(fields) + len(config["calendar_files"]) + len(config["instrument_files"]),
            len(provider_inventory),
            len(symbols) * len(fields) + len(config["calendar_files"]) + len(config["instrument_files"]),
        ),
        contract_row("raw_schema_complete", not raw_receipt["missing_required_columns"], raw_receipt["missing_required_columns"], []),
        contract_row("raw_duplicate_key_count", raw_receipt["duplicate_key_count"] == 0, raw_receipt["duplicate_key_count"], 0),
        contract_row("raw_row_count", raw_receipt["row_count"] == int(config["expected_raw_rows"]), raw_receipt["row_count"], int(config["expected_raw_rows"])),
        contract_row("raw_instrument_count", raw_receipt["instrument_count"] == int(config["expected_instruments"]), raw_receipt["instrument_count"], int(config["expected_instruments"])),
        contract_row("raw_instrument_set", raw_receipt["instrument_set_sha256"] == expected_instrument_hash, raw_receipt["instrument_set_sha256"], expected_instrument_hash),
        contract_row("raw_start_date", pd.Timestamp(raw_receipt["date_min"]) == pd.Timestamp(config["warmup_start_date"]), raw_receipt["date_min"], config["warmup_start_date"]),
        contract_row("raw_end_date", pd.Timestamp(raw_receipt["date_max"]) == pd.Timestamp(config["end_date"]), raw_receipt["date_max"], config["end_date"]),
        contract_row("qlib_commit", qlib_receipt["commit"] == str(config["expected_qlib_commit"]), qlib_receipt["commit"], config["expected_qlib_commit"]),
        contract_row("qlib_dependency_closure_clean", not qlib_receipt["dependency_dirty_paths"], qlib_receipt["dependency_dirty_paths"], []),
        contract_row("raw_sha256_present", len(str(raw_receipt["sha256"])) == 64, raw_receipt["sha256"], "sha256"),
    ]
    contracts = pd.DataFrame(checks)
    ready = bool(contracts["status"].eq("pass").all())
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        provider_inventory.to_csv(publisher.path("provider_file_inventory.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("raw_market_data_manifest.json").write_text(
            json.dumps(custom_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        publisher.path("field_schema.json").write_text(
            json.dumps(field_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
        publisher.path("raw_market_data_report.md").write_text(
            "# Raw Market Data Snapshot V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Provider snapshot: `{provider_snapshot_id}`\n"
            + f"- Provider files: `{len(provider_inventory)}`; missing: `{int((~provider_inventory['exists']).sum())}`\n"
            + f"- Raw rows/instruments: `{raw_receipt['row_count']}` / `{raw_receipt['instrument_count']}`\n"
            + f"- Raw SHA256: `{raw_receipt['sha256']}`\n"
            + f"- Qlib commit: `{qlib_receipt['commit']}`\n"
            + f"- Qlib dirty paths outside dependency closure: `{len(qlib_receipt['dirty_paths'])}`\n",
            encoding="utf-8",
        )
        files = [publisher.path(item) for item in CONTROLLED if item != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="raw_market_data_snapshot_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[resolve(config["universe_manifest"]), resolve(config["factor_catalog_manifest"])],
            universe_artifact_id=universe_manifest["universe_artifact_id"],
            factor_catalog_id=catalog_manifest["factor_catalog_id"],
            start_date=raw_receipt["date_min"],
            end_date=raw_receipt["date_max"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_raw_market_data_provenance",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
