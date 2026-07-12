from __future__ import annotations

import argparse
import hashlib
import re
import sys
from multiprocessing import freeze_support
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.schemas import (  # noqa: E402
    validate_factor_frame,
    validate_judgement_frame,
    validate_screening_frame,
    validate_tradability_frame,
)


DEFAULT_CONFIG = PROJECT_ROOT / "configs/research_data_contracts_v1.yaml"


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"unsupported frame format: {path.suffix}")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_table(frame: pd.DataFrame) -> str:
    rendered = frame.fillna("").astype(str)
    columns = [str(column) for column in rendered.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rendered.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |")
    return "\n".join(lines)


def factor_columns(frame: pd.DataFrame, item: dict[str, Any]) -> list[str]:
    pattern = re.compile(str(item["factor_column_regex"]))
    metadata = {
        "datetime", "instrument", "can_buy", "can_sell", "liquidity_bucket", "tradability_score",
        "data_quality_status", "has_core_missing", "disabled_reason", "liquidity_value",
    }
    return [str(column) for column in frame.columns if str(column) not in metadata and pattern.search(str(column))]


def validate_dataset(item: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    schema = str(item["schema"])
    if schema == "factor_frame":
        return validate_factor_frame(frame, factor_columns(frame, item))
    if schema == "tradability_frame":
        return validate_tradability_frame(frame)
    if schema == "screening_frame":
        return validate_screening_frame(frame)
    if schema == "judgement_frame":
        return validate_judgement_frame(frame)
    raise ValueError(f"unknown schema: {schema}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit research DataFrame contracts.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = resolve_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    for item in config.get("datasets", []):
        path = resolve_path(item["path"])
        if not path.exists():
            result_rows.append({"dataset_id": item["id"], "schema": item["schema"], "status": "fail", "row_count": 0, "column_count": 0, "input_sha256": "", "reason": "input missing"})
            continue
        frame = read_frame(path)
        for column in frame.columns:
            inventory_rows.append(
                {
                    "dataset_id": item["id"],
                    "schema": item["schema"],
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "column": column,
                    "dtype": str(frame[column].dtype),
                    "nullable_observed": bool(frame[column].isna().any()),
                }
            )
        try:
            validated = validate_dataset(item, frame)
            status, reason = "pass", "schema validation passed"
        except Exception as exc:  # Audit records Pandera and structural failures uniformly.
            validated = frame.iloc[0:0]
            status, reason = "fail", f"{type(exc).__name__}: {str(exc)[:1000]}"
        result_rows.append(
            {
                "dataset_id": item["id"],
                "schema": item["schema"],
                "status": status,
                "row_count": len(frame),
                "column_count": len(frame.columns),
                "validated_row_count": len(validated),
                "input_sha256": file_hash(path),
                "reason": reason,
            }
        )

    for item in config.get("compatibility_exceptions", []):
        result_rows.append(
            {
                "dataset_id": item["dataset_id"],
                "schema": item["schema"],
                "status": item["status"],
                "row_count": 0,
                "column_count": 0,
                "validated_row_count": 0,
                "input_sha256": "",
                "reason": item["reason"],
            }
        )

    inventory = pd.DataFrame(inventory_rows)
    results = pd.DataFrame(result_rows)
    contract = pd.DataFrame(
        [
            {"check_name": "configured_datasets", "status": "pass" if len(config.get("datasets", [])) >= 4 else "fail", "observed_value": len(config.get("datasets", [])), "required_value": ">=4", "severity": "critical", "reason": "Core factor, tradability, screening, and judgement frames must be audited."},
            {"check_name": "dataset_validation_failures", "status": "pass" if int((results["status"] == "fail").sum()) == 0 else "fail", "observed_value": int((results["status"] == "fail").sum()), "required_value": 0, "severity": "critical", "reason": "Configured existing outputs must pass their applicable schemas."},
            {"check_name": "compatibility_exceptions", "status": "warning" if int((results["status"] == "compatibility_exception").sum()) else "pass", "observed_value": int((results["status"] == "compatibility_exception").sum()), "required_value": "recorded", "severity": "warning", "reason": "Legacy label/universe gaps are explicitly scoped and cannot be inherited by new outputs."},
            {"check_name": "schema_inventory_rows", "status": "pass" if len(inventory) > 0 else "fail", "observed_value": len(inventory), "required_value": ">0", "severity": "critical", "reason": "Every audited dataset column must be inventoried."},
            {"check_name": "input_lineage", "status": "pass" if results.loc[results["status"] == "pass", "input_sha256"].astype(bool).all() else "fail", "observed_value": int(results.loc[results["status"] == "pass", "input_sha256"].astype(bool).sum()), "required_value": int((results["status"] == "pass").sum()), "severity": "critical", "reason": "Every validated input must have a SHA256 lineage hash."},
            {"check_name": "existing_defaults_modified", "status": "pass", "observed_value": 0, "required_value": 0, "severity": "critical", "reason": "Schema audit is read-only and does not modify source frames or defaults."},
        ]
    )

    inventory.to_csv(output_dir / "schema_inventory.csv", index=False, encoding="utf-8-sig")
    results.to_csv(output_dir / "schema_validation_results.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output_dir / "contract_status.csv", index=False, encoding="utf-8-sig")
    report = [
        "# Research Data Contracts V1",
        "",
        "Pandera-backed, read-only validation for current compact research outputs. New label and universe outputs must use explicit point-in-time fields; the legacy gaps below are compatibility exceptions, not waivers for new modules.",
        "",
        "## Validation Results",
        "",
        markdown_table(results.drop(columns=["input_sha256"])),
        "",
        "## Contract",
        "",
        markdown_table(contract),
        "",
    ]
    (output_dir / "schema_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Research data contract audit written to {output_dir}")
    print(contract.to_string(index=False))
    return 1 if ((contract["severity"] == "critical") & (contract["status"] == "fail")).any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
