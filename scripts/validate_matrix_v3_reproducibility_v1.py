from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    sha256_file,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = (
    "artifact_manifest.json",
    "batch_reproducibility.csv",
    "contract_status.csv",
    "legacy_evidence_receipt.json",
    "matrix_v3_reproducibility_report.md",
    "resolved_config.json",
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def git_show(reference: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{reference}:{Path(path).as_posix()}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip())
    return result.stdout


def compare_partition(legacy_path: Path, current_path: Path, tolerance: float) -> dict[str, object]:
    legacy = pd.read_parquet(legacy_path)
    current = pd.read_parquet(current_path)
    columns_match = legacy.columns.tolist() == current.columns.tolist()
    row_count_match = len(legacy) == len(current)
    key_match = bool(
        row_count_match
        and legacy[["datetime", "instrument"]].reset_index(drop=True).equals(
            current[["datetime", "instrument"]].reset_index(drop=True)
        )
    )
    factors = [column for column in current.columns if column not in {"datetime", "instrument"}]
    nan_mismatch_count = 0
    nonzero_difference_count = 0
    max_absolute_difference = 0.0
    coverage_difference_max = 0.0
    if columns_match and row_count_match:
        for factor in factors:
            before = pd.to_numeric(legacy[factor], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
            after = pd.to_numeric(current[factor], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
            before_nan = np.isnan(before)
            after_nan = np.isnan(after)
            nan_mismatch_count += int(np.count_nonzero(before_nan != after_nan))
            valid = ~(before_nan | after_nan)
            difference = np.abs(before[valid] - after[valid])
            if difference.size:
                nonzero_difference_count += int(np.count_nonzero(difference > tolerance))
                max_absolute_difference = max(max_absolute_difference, float(np.max(difference)))
            coverage_difference_max = max(
                coverage_difference_max,
                abs(float(np.mean(~before_nan)) - float(np.mean(~after_nan))),
            )
    return {
        "legacy_row_count": len(legacy),
        "current_row_count": len(current),
        "factor_count": len(factors),
        "columns_match": columns_match,
        "key_match": key_match,
        "nan_mismatch_count": nan_mismatch_count,
        "nonzero_difference_count": nonzero_difference_count,
        "max_absolute_difference": max_absolute_difference,
        "max_coverage_difference": coverage_difference_max,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare all authoritative matrix v3 partitions to PR #4 evidence.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_feature_matrix_669_reproducibility_v3.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    current_manifest_path = resolve(config["current_matrix_manifest"])
    current_manifest = load_artifact_manifest(current_manifest_path)
    current_issues = validate_manifest_outputs(current_manifest, current_manifest_path.parent)
    current_batch = pd.read_csv(resolve(config["current_batch_manifest"]))
    legacy_manifest = json.loads(git_show(str(config["legacy_git_ref"]), str(config["legacy_manifest_path"])))
    legacy_batch = pd.read_csv(
        io.StringIO(
            git_show(
                str(config["legacy_git_ref"]),
                str(config["legacy_batch_manifest_path"]),
            )
        )
    )
    legacy_by_batch = legacy_batch.set_index("batch_id")
    rows = []
    for row in current_batch.itertuples(index=False):
        batch_id = str(row.batch_id)
        legacy_row = legacy_by_batch.loc[batch_id]
        legacy_path = resolve(config["legacy_runtime_dir"]) / f"{batch_id}.parquet"
        current_path = resolve(config["current_runtime_dir"]) / f"{batch_id}.parquet"
        comparison = compare_partition(legacy_path, current_path, float(config["absolute_tolerance"]))
        rows.append(
            {
                "batch_id": batch_id,
                "source": row.source,
                **comparison,
                "legacy_sha256_recorded": str(legacy_row["output_sha256"]),
                "legacy_sha256_current": sha256_file(legacy_path),
                "current_sha256_recorded": str(row.output_sha256),
                "current_sha256_current": sha256_file(current_path),
            }
        )
    comparison = pd.DataFrame(rows)
    checks = pd.DataFrame(
        [
            contract_row("current_matrix_fresh", not current_issues, len(current_issues), 0),
            contract_row("batch_count", len(comparison) == int(config["expected_batch_count"]), len(comparison), int(config["expected_batch_count"])),
            contract_row("factor_count", int(comparison["factor_count"].sum()) == int(config["expected_factor_count"]), int(comparison["factor_count"].sum()), int(config["expected_factor_count"])),
            contract_row("columns_exact", bool(comparison["columns_match"].all()), int((~comparison["columns_match"]).sum()), 0),
            contract_row("keys_exact", bool(comparison["key_match"].all()), int((~comparison["key_match"]).sum()), 0),
            contract_row("nan_patterns_exact", int(comparison["nan_mismatch_count"].sum()) == 0, int(comparison["nan_mismatch_count"].sum()), 0),
            contract_row("values_within_tolerance", int(comparison["nonzero_difference_count"].sum()) == 0, int(comparison["nonzero_difference_count"].sum()), 0),
            contract_row("coverage_exact", float(comparison["max_coverage_difference"].max()) == 0.0, float(comparison["max_coverage_difference"].max()), 0.0),
            contract_row("legacy_runtime_hashes_match_pr4", bool(comparison["legacy_sha256_recorded"].eq(comparison["legacy_sha256_current"]).all()), int((comparison["legacy_sha256_recorded"] != comparison["legacy_sha256_current"]).sum()), 0),
            contract_row("v3_runtime_hashes_match_manifest", bool(comparison["current_sha256_recorded"].eq(comparison["current_sha256_current"]).all()), int((comparison["current_sha256_recorded"] != comparison["current_sha256_current"]).sum()), 0),
        ]
    )
    ready = bool(checks["status"].eq("pass").all())
    legacy_receipt = {
        "git_ref": config["legacy_git_ref"],
        "artifact_id": legacy_manifest["artifact_id"],
        "code_commit_sha": legacy_manifest["code_commit_sha"],
        "factor_frame_id": legacy_manifest["factor_frame_id"],
        "batch_manifest_path": config["legacy_batch_manifest_path"],
        "batch_count": len(legacy_batch),
    }
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        comparison.to_csv(publisher.path("batch_reproducibility.csv"), index=False, encoding="utf-8-sig")
        checks.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("legacy_evidence_receipt.json").write_text(json.dumps(legacy_receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        publisher.path("resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        publisher.path("matrix_v3_reproducibility_report.md").write_text(
            "# Matrix V3 Reproducibility Validation\n\n"
            + f"- Status: `{'pass' if ready else 'blocked'}`\n"
            + f"- Compared batches/factors: `{len(comparison)}` / `{int(comparison['factor_count'].sum())}`\n"
            + f"- Key/NaN/value mismatches: `{int((~comparison['key_match']).sum())}` / `{int(comparison['nan_mismatch_count'].sum())}` / `{int(comparison['nonzero_difference_count'].sum())}`\n"
            + f"- Maximum absolute value difference: `{float(comparison['max_absolute_difference'].max())}`\n"
            + f"- Legacy evidence: `{legacy_receipt['git_ref']}` / `{legacy_receipt['artifact_id']}`\n",
            encoding="utf-8",
        )
        files = [publisher.path(item) for item in CONTROLLED if item != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_feature_matrix_reproducibility_v3",
            config=config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[current_manifest_path],
            factor_frame_id=current_manifest["factor_frame_id"],
            start_date=current_manifest["start_date"],
            end_date=current_manifest["end_date"],
            lineage_status="complete",
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_matrix_v3_reproducibility",
        )
        publisher.publish()
    print(checks.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
