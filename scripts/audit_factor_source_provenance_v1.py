from __future__ import annotations

import argparse
import importlib.metadata
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
    source_file_inventory,
    source_tree_hash,
)
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = (
    "artifact_manifest.json",
    "contract_status.csv",
    "factor_source_manifest.json",
    "factor_source_provenance_report.md",
    "repo_receipts.json",
    "resolved_config.json",
    "source_file_inventory.csv",
    "source_summary.csv",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def selected_hash(inventory: pd.DataFrame, role_patterns: tuple[str, ...]) -> str:
    mask = inventory["file_role"].astype(str).map(lambda role: any(pattern in role for pattern in role_patterns))
    selected = inventory.loc[mask]
    return source_tree_hash(selected) if not selected.empty else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact factor source and adapter provenance.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_source_provenance_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    catalog_manifest = load_artifact_manifest(resolve(config["factor_catalog_manifest"]))

    repo_receipts: dict[str, dict[str, object]] = {}
    repository_inventories: dict[str, pd.DataFrame] = {}
    contract_rows: list[dict[str, object]] = []
    for name, spec in config["repositories"].items():
        root = resolve(spec["path"])
        dependency_files = [str(item) for item in spec["dependency_files"]]
        receipt = git_repo_receipt(root, dependency_files)
        receipt["expected_commit"] = str(spec["expected_commit"])
        receipt["require_clean"] = bool(spec["require_clean"])
        repo_receipts[name] = receipt
        repository_inventories[name] = source_file_inventory(
            name,
            root,
            {f"repository:{index:03d}:{Path(path).name}": path for index, path in enumerate(dependency_files, start=1)},
        )
        contract_rows.extend(
            [
                contract_row(
                    f"{name}_commit_matches",
                    receipt["commit"] == str(spec["expected_commit"]),
                    receipt["commit"],
                    spec["expected_commit"],
                ),
                contract_row(
                    f"{name}_dependency_files_exist",
                    bool(repository_inventories[name]["exists"].all()),
                    int((~repository_inventories[name]["exists"]).sum()),
                    0,
                ),
                contract_row(
                    f"{name}_worktree_policy",
                    not receipt["dirty_paths"] if bool(spec["require_clean"]) else not receipt["dependency_dirty_paths"],
                    receipt["dirty_paths"] if bool(spec["require_clean"]) else receipt["dependency_dirty_paths"],
                    [],
                ),
            ]
        )

    source_inventories: list[pd.DataFrame] = []
    source_summary_rows: list[dict[str, object]] = []
    batch_key_material: dict[str, dict[str, object]] = {}
    for source, spec in config["sources"].items():
        frames = []
        repository_name = spec.get("repository")
        if repository_name:
            repo_frame = repository_inventories[str(repository_name)].copy()
            repo_frame["source"] = source
            frames.append(repo_frame)
        project_frame = source_file_inventory(source, PROJECT_ROOT, {str(role): str(path) for role, path in spec["project_files"].items()})
        frames.append(project_frame)
        inventory = pd.concat(frames, ignore_index=True)
        source_inventories.append(inventory)
        tree_hash = source_tree_hash(inventory)
        adapter_hash = selected_hash(inventory, ("adapter", "matrix_contract", "factor_library"))
        formula_hash = selected_hash(inventory, ("formula", "metadata", "catalog"))
        if repository_name:
            receipt = repo_receipts[str(repository_name)]
            commit = str(receipt["commit"])
            commit_tree = str(receipt["commit_tree"])
            remote_url = str(receipt["remote_url"])
            repo_clean = bool(receipt["repo_clean"])
            dependency_dirty_paths = list(receipt["dependency_dirty_paths"])
        else:
            commit = code_state.commit_sha
            commit_tree = ""
            remote_url = "project"
            repo_clean = not code_state.dirty
            dependency_dirty_paths = [] if not code_state.dirty else ["project_worktree"]
        source_summary_rows.append(
            {
                "source": source,
                "repository": repository_name or "project",
                "repository_commit": commit,
                "repository_commit_tree": commit_tree,
                "remote_url": remote_url,
                "repo_clean": repo_clean,
                "dependency_dirty_path_count": len(dependency_dirty_paths),
                "source_file_count": len(inventory),
                "source_specific_tree_hash": tree_hash,
                "adapter_hash": adapter_hash,
                "formula_or_metadata_hash": formula_hash,
            }
        )
        batch_key_material[source] = {
            "source_specific_tree_hash": tree_hash,
            "adapter_hash": adapter_hash,
            "formula_or_metadata_hash": formula_hash,
            "source_commit": commit,
            "qlib_commit": str(repo_receipts["qlib"]["commit"]),
        }
        contract_rows.extend(
            [
                contract_row(f"{source}_source_files_exist", bool(inventory["exists"].all()), int((~inventory["exists"]).sum()), 0),
                contract_row(f"{source}_source_tree_hash", len(tree_hash) == 64, tree_hash, "sha256"),
                contract_row(f"{source}_adapter_hash", len(adapter_hash) == 64, adapter_hash, "sha256"),
                contract_row(f"{source}_formula_or_metadata_hash", len(formula_hash) == 64, formula_hash, "sha256"),
            ]
        )

    import qlib

    qlib_repo = resolve(config["repositories"]["qlib"]["path"])
    qlib_file = Path(qlib.__file__).resolve()
    qlib_version = importlib.metadata.version("pyqlib")
    contract_rows.append(
        contract_row("qlib_import_resolves_to_audited_repo", qlib_repo in qlib_file.parents, qlib_file.as_posix(), qlib_repo.as_posix())
    )
    all_inventory = pd.concat(source_inventories, ignore_index=True)
    source_summary = pd.DataFrame(source_summary_rows).sort_values("source").reset_index(drop=True)
    contracts = pd.DataFrame(contract_rows)
    ready = bool(contracts["status"].eq("pass").all())
    custom_manifest = {
        "schema_version": 1,
        "factor_catalog_artifact_id": catalog_manifest["artifact_id"],
        "factor_catalog_id": catalog_manifest["factor_catalog_id"],
        "qlib_version": qlib_version,
        "qlib_import_path": qlib_file.as_posix(),
        "qlib_commit": repo_receipts["qlib"]["commit"],
        "repositories": repo_receipts,
        "batch_key_material": batch_key_material,
    }

    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        all_inventory.to_csv(publisher.path("source_file_inventory.csv"), index=False, encoding="utf-8-sig")
        source_summary.to_csv(publisher.path("source_summary.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("factor_source_manifest.json").write_text(
            json.dumps(custom_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        publisher.path("repo_receipts.json").write_text(
            json.dumps(repo_receipts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
        publisher.path("factor_source_provenance_report.md").write_text(
            "# Factor Source Provenance V1\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Qlib version/commit: `{qlib_version}` / `{repo_receipts['qlib']['commit']}`\n"
            + f"- Audited factor sources: `{len(source_summary)}`\n"
            + f"- Qlib dirty paths outside dependency closure: `{len(repo_receipts['qlib']['dirty_paths'])}`\n"
            + "- TA and KunQuant require clean worktrees; Qlib may only contain dirty paths outside the audited dependency closure.\n",
            encoding="utf-8",
        )
        files = [publisher.path(item) for item in CONTROLLED if item != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="factor_source_provenance_v1",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=code_state,
            input_manifest_paths=[resolve(config["factor_catalog_manifest"])],
            factor_catalog_id=catalog_manifest["factor_catalog_id"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_factor_source_provenance",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
