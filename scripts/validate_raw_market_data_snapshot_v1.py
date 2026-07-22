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

from research_validation.input_provenance import inventory_tree_hash, verify_file_inventory  # noqa: E402
from research_validation.lineage import load_artifact_manifest, sha256_file, validate_manifest_outputs  # noqa: E402
from scripts.audit_raw_market_data_snapshot_v1 import CONTROLLED  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw market snapshot freshness and external inputs.")
    parser.add_argument("--config", type=Path, default=Path("configs/raw_market_data_snapshot_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    output = resolve(config["output_dir"])
    manifest = load_artifact_manifest(output / "artifact_manifest.json")
    issues = validate_manifest_outputs(manifest, output, config=config, controlled_outputs=CONTROLLED[1:])
    failures: list[str] = []
    for key in ("universe_manifest", "factor_catalog_manifest"):
        parent_path = resolve(config[key])
        parent = load_artifact_manifest(parent_path)
        issues.extend(validate_manifest_outputs(parent, parent_path.parent))
        if parent["artifact_id"] not in manifest["input_artifact_ids"]:
            failures.append(f"missing_current_parent:{parent['artifact_id']}")
    inventory = pd.read_csv(output / "provider_file_inventory.csv")
    verified = verify_file_inventory(resolve(config["provider_uri"]), inventory, workers=int(config.get("hash_workers", 8)))
    custom = json.loads((output / "raw_market_data_manifest.json").read_text(encoding="utf-8"))
    contracts = pd.read_csv(output / "contract_status.csv")
    failures.extend(f"{item.check_name}:{item.reason}" for item in issues)
    if not bool(verified["current_match"].all()):
        failures.append(f"provider_input_hash_mismatch:{int((~verified['current_match']).sum())}")
    if inventory_tree_hash(inventory) != custom["provider_tree_sha256"]:
        failures.append("provider_inventory_tree_hash_mismatch")
    raw_path = resolve(config["raw_cache_path"])
    if sha256_file(raw_path) != custom["raw_parquet"]["sha256"]:
        failures.append("raw_parquet_hash_mismatch")
    if bool(manifest["code_dirty"]):
        failures.append("provenance_generated_from_dirty_project_tree")
    if manifest["artifact_status"] != "pass":
        failures.append(f"artifact_status:{manifest['artifact_status']}")
    if not contracts["status"].eq("pass").all():
        failures.append("contract_status_failed")
    if failures:
        print("\n".join(failures))
        return 2
    print(f"Raw market provenance valid: {manifest['artifact_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
