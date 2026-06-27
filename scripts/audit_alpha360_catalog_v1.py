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

from factor_research.qlib_alpha360 import (  # noqa: E402
    ALPHA360_FIELD_ORDER,
    alpha360_catalog_payload,
    build_alpha360_formulas,
    build_formula_inventory,
    collect_provider_fields,
    qlib_source_commit,
    select_smoke_inventory,
)
from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha360_catalog_audit_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


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
    smoke_inventory: pd.DataFrame,
) -> None:
    family_summary = inventory.groupby(["family", "field_status"]).size().reset_index(name="factor_count")
    status_summary = inventory.groupby("field_status").size().reset_index(name="factor_count")
    lines = [
        "# Qlib Alpha360 Catalog Audit V1",
        "",
        f"- Provider: `{provider_uri.as_posix()}`",
        f"- Qlib source: `{qlib_source.as_posix()}`",
        f"- Qlib commit: `{source_commit}`",
        "- Source function: `qlib.contrib.data.loader.Alpha360DL.get_feature_config`",
        "- License: `MIT`",
        "",
        "## Scope",
        "",
        "This audit extracts the 360 normalized price/volume lag expressions from the local Qlib source and checks whether their raw fields exist in the current provider. It does not mark Alpha360 entries as runnable.",
        "",
        "## Status Summary",
        "",
        markdown_table(status_summary),
        "",
        "## Family Summary",
        "",
        markdown_table(family_summary),
        "",
        "## Field Usage",
        "",
        markdown_table(field_usage),
        "",
        "## Smoke Catalog Preview",
        "",
        markdown_table(
            smoke_inventory[
                ["factor_name", "catalog_name", "family", "lag", "required_fields", "field_status", "expression"]
            ]
        ),
        "",
        "## Output Files",
        "",
        "- `provider_field_presence.csv`",
        "- `alpha360_formula_inventory.csv`",
        "- `alpha360_field_usage.csv`",
        "- `alpha360_catalog_all.yaml`",
        "- `alpha360_catalog_smoke.yaml`",
        "- `alpha360_audit_report.md`",
        "",
        "## Next Step",
        "",
        "Build a small Qlib expression frame from `alpha360_catalog_smoke.yaml`, then run V4 smoke evaluation before any promotion.",
    ]
    (output_dir / "alpha360_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> Path:
    data = yaml.safe_load(resolve_path(config_path).read_text(encoding="utf-8")) or {}
    provider_uri = resolve_path(data["provider_uri"])
    qlib_source = resolve_path(data["qlib_source"])
    output_dir = resolve_path(data.get("output_dir", "outputs/factor_catalog_alpha360_v1"))
    smoke = data.get("smoke", {})
    smoke_fields = tuple(str(item).upper() for item in smoke.get("fields", ALPHA360_FIELD_ORDER))
    smoke_lags = tuple(int(item) for item in smoke.get("lags", [0, 5, 20, 59]))
    expected_smoke_count = int(smoke.get("expected_count", len(smoke_fields) * len(smoke_lags)))
    output_dir.mkdir(parents=True, exist_ok=True)

    source_commit = qlib_source_commit(qlib_source)
    provider_fields = collect_provider_fields(provider_uri)
    formulas = build_alpha360_formulas(qlib_source)
    inventory = build_formula_inventory(formulas, provider_fields, qlib_source, source_commit)
    field_usage = build_field_usage(inventory, provider_fields)
    smoke_inventory = select_smoke_inventory(inventory, smoke_fields=smoke_fields, smoke_lags=smoke_lags)

    provider_fields.to_csv(output_dir / "provider_field_presence.csv", index=False, encoding="utf-8-sig")
    inventory.to_csv(output_dir / "alpha360_formula_inventory.csv", index=False, encoding="utf-8-sig")
    field_usage.to_csv(output_dir / "alpha360_field_usage.csv", index=False, encoding="utf-8-sig")
    write_yaml(
        alpha360_catalog_payload(inventory, enabled=False, runnable=False, stage="alpha360_adapter_pending"),
        output_dir / "alpha360_catalog_all.yaml",
    )
    write_yaml(
        alpha360_catalog_payload(smoke_inventory, enabled=False, runnable=False, stage="alpha360_smoke_adapter_pending"),
        output_dir / "alpha360_catalog_smoke.yaml",
    )
    write_report(output_dir, provider_uri, qlib_source, source_commit, inventory, field_usage, smoke_inventory)

    if len(inventory) != 360:
        raise ValueError(f"Expected 360 Alpha360 formulas, got {len(inventory)}")
    missing = inventory[inventory["field_status"].ne("available")]
    if not missing.empty:
        raise ValueError(f"Alpha360 audit found formulas with missing provider fields: {len(missing)}")
    if len(smoke_inventory) != expected_smoke_count:
        raise ValueError(f"Expected {expected_smoke_count} Alpha360 smoke formulas, got {len(smoke_inventory)}")

    print("Alpha360 audit completed: all 360 formulas have provider fields available.", flush=True)
    print(f"Smoke catalog entries: {len(smoke_inventory)}", flush=True)
    print(f"Outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Qlib Alpha360 formulas against the current provider.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
