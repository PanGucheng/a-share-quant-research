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

from research_validation.input_provenance import git_repo_receipt  # noqa: E402
from research_validation.lineage import load_artifact_manifest, sha256_file, validate_manifest_outputs  # noqa: E402
from scripts.audit_factor_source_provenance_v1 import CONTROLLED  # noqa: E402


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate factor source provenance freshness.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_source_provenance_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    output = resolve(config["output_dir"])
    manifest = load_artifact_manifest(output / "artifact_manifest.json")
    issues = validate_manifest_outputs(manifest, output, config=config, controlled_outputs=CONTROLLED[1:])
    parent_path = resolve(config["factor_catalog_manifest"])
    parent = load_artifact_manifest(parent_path)
    issues.extend(validate_manifest_outputs(parent, parent_path.parent))
    recorded_receipts = json.loads((output / "repo_receipts.json").read_text(encoding="utf-8"))
    inventory = pd.read_csv(output / "source_file_inventory.csv")
    contracts = pd.read_csv(output / "contract_status.csv")
    failures = [f"{item.check_name}:{item.reason}" for item in issues]
    if parent["artifact_id"] not in manifest["input_artifact_ids"]:
        failures.append(f"missing_current_parent:{parent['artifact_id']}")
    for name, spec in config["repositories"].items():
        current = git_repo_receipt(resolve(spec["path"]), [str(item) for item in spec["dependency_files"]])
        recorded = recorded_receipts[name]
        for key in ("commit", "commit_tree", "dirty_paths", "dependency_dirty_paths"):
            if current[key] != recorded[key]:
                failures.append(f"{name}_{key}_mismatch")
    for row in inventory.itertuples(index=False):
        source_spec = config["sources"][str(row.source)]
        if str(row.file_role).startswith("repository:"):
            root = resolve(config["repositories"][source_spec["repository"]]["path"])
        else:
            root = PROJECT_ROOT
        path = root / str(row.relative_path)
        if not path.is_file() or sha256_file(path) != str(row.sha256):
            failures.append(f"source_file_hash_mismatch:{row.source}:{row.relative_path}")
    if bool(manifest["code_dirty"]):
        failures.append("provenance_generated_from_dirty_project_tree")
    if manifest["artifact_status"] != "pass":
        failures.append(f"artifact_status:{manifest['artifact_status']}")
    if not contracts["status"].eq("pass").all():
        failures.append("contract_status_failed")
    if failures:
        print("\n".join(failures))
        return 2
    print(f"Factor source provenance valid: {manifest['artifact_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
