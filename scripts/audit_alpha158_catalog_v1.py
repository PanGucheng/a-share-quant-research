from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.qlib_alpha158 import (  # noqa: E402
    alpha158_catalog_payload,
    build_alpha158_formulas,
    build_formula_inventory,
    collect_provider_fields,
    qlib_source_commit,
)
from factor_research.report import markdown_table  # noqa: E402


DEFAULT_PROVIDER = Path("E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
DEFAULT_QLIB_SOURCE = Path("E:/qlib_prj/qlib_clone")
DEFAULT_OUTPUT = Path("outputs/factor_catalog_alpha158_v1")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def write_yaml(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def build_field_usage(inventory: pd.DataFrame, provider_fields: pd.DataFrame) -> pd.DataFrame:
    usage_rows = []
    for row in inventory.itertuples(index=False):
        for field in [item for item in str(row.required_fields).split(",") if item]:
            usage_rows.append({"field": field.removeprefix("$"), "factor_name": row.factor_name})
    usage = pd.DataFrame(usage_rows)
    if usage.empty:
        return pd.DataFrame(columns=["field", "factor_count", "provider_presence_rate"])
    counts = usage.groupby("field").size().reset_index(name="factor_count")
    merged = counts.merge(provider_fields[["field", "file_presence_rate"]], on="field", how="left")
    merged["provider_presence_rate"] = merged["file_presence_rate"].fillna(0.0)
    return merged[["field", "factor_count", "provider_presence_rate"]].sort_values("field")


def write_report(
    output_dir: Path,
    provider_uri: Path,
    qlib_source: Path,
    source_commit: str,
    inventory: pd.DataFrame,
    field_usage: pd.DataFrame,
    first_batch: pd.DataFrame,
) -> None:
    category_summary = inventory.groupby(["category", "field_status"]).size().reset_index(name="factor_count")
    status_summary = inventory.groupby("field_status").size().reset_index(name="factor_count")
    lines = [
        "# Qlib Alpha158 Catalog Audit V1",
        "",
        f"- Provider: `{provider_uri.as_posix()}`",
        f"- Qlib source: `{qlib_source.as_posix()}`",
        f"- Qlib commit: `{source_commit}`",
        "- Source function: `qlib.contrib.data.loader.Alpha158DL.get_feature_config`",
        "- License: `MIT`",
        "",
        "## Scope",
        "",
        "This audit extracts Alpha158 formulas from the local Qlib source and checks whether their raw fields exist in the current provider. It does not run factor evaluation and does not mark Alpha158 entries as runnable yet.",
        "",
        "## Status Summary",
        "",
        markdown_table(status_summary),
        "",
        "## Category Summary",
        "",
        markdown_table(category_summary),
        "",
        "## Field Usage",
        "",
        markdown_table(field_usage),
        "",
        "## First Batch Preview",
        "",
        markdown_table(first_batch[["factor_name", "catalog_name", "category", "required_fields", "field_status", "expression"]]),
        "",
        "## Output Files",
        "",
        "- `alpha158_formula_inventory.csv`",
        "- `alpha158_field_usage.csv`",
        "- `alpha158_catalog_all.yaml`",
        "- `alpha158_catalog_first_batch.yaml`",
        "- `alpha158_audit_report.md`",
        "",
        "## Next Step",
        "",
        "Build and validate a Qlib expression adapter before setting these entries to `runnable: true`.",
    ]
    (output_dir / "alpha158_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    provider_uri = resolve_path(args.provider_uri)
    qlib_source = resolve_path(args.qlib_source)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_commit = qlib_source_commit(qlib_source)
    provider_fields = collect_provider_fields(provider_uri)
    formulas = build_alpha158_formulas(qlib_source)
    inventory = build_formula_inventory(formulas, provider_fields, qlib_source, source_commit)
    available = inventory[inventory["field_status"].eq("available")].copy()
    first_batch = available.head(args.first_batch_size).copy()
    field_usage = build_field_usage(inventory, provider_fields)

    provider_fields.to_csv(output_dir / "provider_field_presence.csv", index=False, encoding="utf-8-sig")
    inventory.to_csv(output_dir / "alpha158_formula_inventory.csv", index=False, encoding="utf-8-sig")
    field_usage.to_csv(output_dir / "alpha158_field_usage.csv", index=False, encoding="utf-8-sig")
    write_yaml(
        alpha158_catalog_payload(inventory, enabled=False, runnable=False, stage="alpha158_adapter_pending"),
        output_dir / "alpha158_catalog_all.yaml",
    )
    write_yaml(
        alpha158_catalog_payload(first_batch, enabled=False, runnable=False, stage="alpha158_first_batch_adapter_pending"),
        output_dir / "alpha158_catalog_first_batch.yaml",
    )
    write_report(output_dir, provider_uri, qlib_source, source_commit, inventory, field_usage, first_batch)

    if len(inventory) != 158:
        raise ValueError(f"Expected 158 Alpha158 formulas, got {len(inventory)}")
    missing = inventory[inventory["field_status"].ne("available")]
    if not missing.empty:
        print(f"Alpha158 audit completed with missing fields in {len(missing)} formulas.", flush=True)
    else:
        print("Alpha158 audit completed: all 158 formulas have provider fields available.", flush=True)
    print(f"Outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Qlib Alpha158 formulas against the current provider.")
    parser.add_argument("--provider-uri", type=Path, default=DEFAULT_PROVIDER)
    parser.add_argument("--qlib-source", type=Path, default=DEFAULT_QLIB_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--first-batch-size", type=int, default=20)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
