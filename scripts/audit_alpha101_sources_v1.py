from __future__ import annotations

import argparse
import ast
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

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha101_source_audit_v1.yaml")
ALPHA_RE = re.compile(r"alpha\d{3}$")
ALL_DATA_FIELDS = {
    "open": "$open",
    "close": "$close",
    "high": "$high",
    "low": "$low",
    "volume": "$volume",
    "amount": "$amount",
    "vwap": "$amount,$volume",
    "returns": "$close",
}


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class AllDataFieldVisitor(ast.NodeVisitor):
    def __init__(self, param_names: set[str]) -> None:
        self.param_names = param_names
        self.fields: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id in self.param_names:
            if node.attr in ALL_DATA_FIELDS:
                self.fields.add(node.attr)
        self.generic_visit(node)


def parse_kunquant_alpha101(path: Path) -> tuple[pd.DataFrame, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function_defs: dict[str, ast.FunctionDef] = {}
    all_alpha: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and ALPHA_RE.fullmatch(node.name):
            function_defs[node.name] = node
        if isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "all_alpha" in target_names and isinstance(node.value, ast.List):
                for item in node.value.elts:
                    if isinstance(item, ast.Name):
                        all_alpha.append(item.id)
    all_alpha_set = set(all_alpha)
    rows = []
    for name, node in sorted(function_defs.items()):
        params = {arg.arg for arg in node.args.args}
        visitor = AllDataFieldVisitor(params)
        visitor.visit(node)
        fields = sorted({field for item in visitor.fields for field in ALL_DATA_FIELDS[item].split(",")})
        if not fields:
            fields = ["$open", "$close", "$high", "$low", "$volume", "$amount"]
        rows.append(
            {
                "factor": f"kunquant_alpha101_{name}",
                "registry_name": name,
                "source_function": name,
                "in_all_alpha": name in all_alpha_set,
                "required_fields": ",".join(fields),
                "param_names": ",".join(sorted(params)),
                "status": "formula_available_adapter_pending" if name in all_alpha_set else "formula_defined_not_in_all_alpha",
            }
        )
    return pd.DataFrame(rows), all_alpha


def audit_sources(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_rows = []
    inventory_frames = []
    for source in config.get("sources", []):
        source_id = str(source["id"])
        local_path = resolve_path(source["local_path"])
        source_file = str(source.get("source_file", ""))
        source_path = local_path / source_file
        license_path = local_path / "LICENSE"
        source_status = "available" if source_path.exists() and source_path.stat().st_size > 0 else "missing"
        license_status = "available" if license_path.exists() and license_path.stat().st_size > 0 else "missing"
        function_count = 0
        all_alpha_count = 0
        if source_id == "kunquant_alpha101" and source_status == "available":
            inventory, all_alpha = parse_kunquant_alpha101(source_path)
            inventory.insert(0, "source_project", source_id)
            inventory["source_file"] = portable_path(source_path)
            inventory["source_commit"] = source["source_commit"]
            inventory["license"] = source["license"]
            inventory_frames.append(inventory)
            function_count = int(len(inventory))
            all_alpha_count = int(len(all_alpha))
        source_rows.append(
            {
                "source_project": source_id,
                "name": source.get("name", ""),
                "implementation_role": source.get("implementation_role", ""),
                "local_path": portable_path(local_path),
                "source_file": source_file,
                "source_status": source_status,
                "license": source.get("license", ""),
                "license_status": license_status,
                "source_commit": source.get("source_commit", ""),
                "function_count": function_count,
                "all_alpha_count": all_alpha_count,
                "adapter_status": "adapter_pending" if function_count else "not_runnable_reference",
            }
        )
    inventory_frame = pd.concat(inventory_frames, ignore_index=True) if inventory_frames else pd.DataFrame()
    return pd.DataFrame(source_rows), inventory_frame


def write_metadata_catalog(config: dict[str, Any], inventory: pd.DataFrame, output: Path) -> None:
    policy = config.get("policy", {})
    labels = [str(item) for item in config.get("labels", [])]
    source = next(item for item in config.get("sources", []) if item["id"] == "kunquant_alpha101")
    factors = []
    for row in inventory[inventory["in_all_alpha"].map(bool)].itertuples(index=False):
        factors.append(
            {
                "name": row.factor,
                "registry_name": row.registry_name,
                "category": "alpha101",
                "source_project": "kunquant_alpha101",
                "source_file": "KunQuant/predefined/Alpha101.py",
                "source_function": row.source_function,
                "source_commit": source["source_commit"],
                "license": source["license"],
                "expected_direction": policy.get("expected_direction", "watch"),
                "required_fields": str(row.required_fields).split(","),
                "labels": labels,
                "stage": policy.get("default_stage", "alpha101_source_audit_adapter_pending"),
                "enabled": False,
                "runnable": False,
                "compute_adapter": policy.get("compute_adapter", "kunquant_alpha101_adapter_pending"),
                "notes": "Metadata only. Formula exists in KunQuant all_alpha; adapter and V4 validation are pending.",
            }
        )
    payload = {
        "version": 1,
        "updated": "2026-06-26",
        "policy": {
            "purpose": "KunQuant Alpha101 metadata catalog before adapter implementation.",
            "required_prefilter": policy.get("required_prefilter", []),
            "principle": [
                "Do not mark Alpha101 entries runnable until adapter smoke and V4 evaluation pass.",
                "Reuse KunQuant formula definitions instead of hand-writing Alpha101 formulas.",
            ],
        },
        "factors": factors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_report(output_dir: Path, sources: pd.DataFrame, inventory: pd.DataFrame, catalog_path: Path) -> None:
    available = inventory[inventory["in_all_alpha"].map(bool)] if not inventory.empty else pd.DataFrame()
    missing_numbers = []
    if not available.empty:
        present = {int(str(name).replace("alpha", "")) for name in available["registry_name"]}
        missing_numbers = [number for number in range(1, 102) if number not in present]
    lines = [
        "# Alpha101 Source Audit V1",
        "",
        "## Source Summary",
        "",
        markdown_table(sources),
        "",
        "## KunQuant Inventory",
        "",
        f"- Formula functions parsed: `{len(inventory)}`",
        f"- Functions in `all_alpha`: `{len(available)}`",
        f"- Missing Alpha101 numbers from 1..101: `{','.join(str(item) for item in missing_numbers)}`",
        f"- Metadata catalog: `{portable_path(catalog_path)}`",
        "",
        "## Sample Factors",
        "",
        markdown_table(available.head(30) if not available.empty else pd.DataFrame()),
        "",
        "## Decision",
        "",
        "- Use KunQuant as the primary Alpha101 formula source for the next adapter stage.",
        "- Treat Ginkgo_Alpha101 as metadata/reference only because the local clone contains README/LICENSE but no formula implementation files.",
        "- Keep all generated Alpha101 catalog entries disabled and non-runnable until adapter smoke and V4 validation pass.",
    ]
    (output_dir / "alpha101_source_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> Path:
    config = load_yaml(resolve_path(config_path))
    output_dir = resolve_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    sources, inventory = audit_sources(config)
    catalog_path = resolve_path(config["metadata_catalog"])
    write_metadata_catalog(config, inventory, catalog_path)
    sources.to_csv(output_dir / "alpha101_source_summary.csv", index=False, encoding="utf-8-sig")
    inventory.to_csv(output_dir / "kunquant_alpha101_inventory.csv", index=False, encoding="utf-8-sig")
    write_report(output_dir, sources, inventory, catalog_path)
    print(f"Alpha101 source audit outputs written to {output_dir}", flush=True)
    print(f"KunQuant all_alpha entries: {int(inventory['in_all_alpha'].sum()) if not inventory.empty else 0}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Alpha101 open-source formula sources before adapter work.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
