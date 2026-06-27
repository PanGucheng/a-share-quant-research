from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha101_factor_batch_catalogs_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def with_stage(entry: dict, *, stage: str, enabled: bool, runnable: bool, note_suffix: str) -> dict:
    result = dict(entry)
    result["stage"] = stage
    result["enabled"] = bool(enabled)
    result["runnable"] = bool(runnable)
    result["compute_adapter"] = "factor_research.alpha101_source.compute_alpha101_features"
    notes = str(result.get("notes", "")).replace("Metadata only. Formula exists in KunQuant all_alpha; adapter and V4 validation are pending.", "").strip()
    result["notes"] = f"{notes} {note_suffix}".strip()
    return result


def load_inventory(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    inventory = pd.read_csv(path)
    if "eligible" in inventory.columns:
        inventory["eligible"] = inventory["eligible"].astype(str).str.lower().isin({"true", "1", "yes"})
    return inventory


def adapter_config_payload(config: dict, selected_factors: list[str]) -> dict:
    adapter = config["adapter"]
    source = adapter["source"]
    return {
        "provider_uri": adapter["provider_uri"],
        "market": adapter["market"],
        "start": adapter["start"],
        "end": adapter["end"],
        "max_instruments": adapter.get("max_instruments"),
        "source": {
            "local_path": source["local_path"],
            "source_commit": source["source_commit"],
            "source_file": source["source_file"],
            "source_module": source["source_module"],
            "license": source["license"],
        },
        "alpha101": {
            "metadata_catalog": config["source_catalog"],
            "selected_smoke_factors": selected_factors,
        },
        "catalog": {
            "stage": config.get("stages", {}).get("combined_pending", "alpha101_adapter_combined_v4_pending"),
            "enabled": False,
            "runnable": False,
            "labels": [str(item) for item in adapter.get("labels", [])],
        },
        "cache": {
            "refresh": bool(adapter.get("cache", {}).get("refresh", False)),
        },
        "output_dir": adapter["output_dir"],
    }


def run(config_path: Path) -> dict[str, Path]:
    config = load_yaml(resolve_path(config_path))
    source_path = resolve_path(config["source_catalog"])
    passed_path = resolve_path(config["passed_catalog"])
    remaining_path = resolve_path(config["remaining_catalog"])
    combined_path = resolve_path(config["combined_catalog"])
    inventory_path = resolve_path(config["adapter_inventory"])
    candidate_path = resolve_path(config["batch_candidate_catalog"])
    adapter_holdout_path = resolve_path(config["adapter_holdout_catalog"])
    audit_path = resolve_path(config["audit_output"])
    report_path = resolve_path(config["report_output"])
    adapter_config_path = resolve_path(config["adapter_config_output"])

    source = load_yaml(source_path)
    passed = load_yaml(passed_path)
    stages = config.get("stages", {})
    remaining_config = config.get("remaining", {})
    source_entries = [dict(item) for item in source.get("factors", [])]
    passed_entries = [dict(item) for item in passed.get("factors", [])]
    passed_names = {str(item["name"]) for item in passed_entries}

    remaining_entries = [
        with_stage(
            entry,
            stage=str(stages.get("remaining", "alpha101_adapter_remaining_v4_pending")),
            enabled=bool(remaining_config.get("enabled", False)),
            runnable=bool(remaining_config.get("runnable", False)),
            note_suffix="Pending Alpha101 batch V4 evaluation.",
        )
        for entry in source_entries
        if str(entry.get("name")) not in passed_names
    ]
    combined_entries = sorted(passed_entries + remaining_entries, key=lambda item: str(item["name"]))
    inventory = load_inventory(inventory_path)
    candidate_entries = remaining_entries
    adapter_holdout_entries: list[dict] = []
    if not inventory.empty:
        eligible_names = set(inventory[inventory["eligible"]]["factor"].astype(str))
        exclusion_map = {
            str(row.factor): str(row.exclusion_reason)
            for row in inventory[~inventory["eligible"]].itertuples(index=False)
        }
        candidate_entries = [entry for entry in remaining_entries if str(entry["name"]) in eligible_names]
        adapter_holdout_entries = [
            with_stage(
                entry,
                stage=str(stages.get("adapter_holdout", "alpha101_adapter_zero_valid_holdout")),
                enabled=False,
                runnable=False,
                note_suffix=f"Alpha101 adapter holdout: {exclusion_map.get(str(entry['name']), 'adapter_ineligible')}.",
            )
            for entry in remaining_entries
            if str(entry["name"]) not in eligible_names
        ]

    common_policy = {
        "required_prefilter": ["data_quality", "tradability"],
        "principle": [
            "Alpha101 formulas are sourced from the local KunQuant reference repository.",
            "Remaining entries are disabled/non-runnable until batch V4 promotion.",
            "Use project-unique catalog names as factor IDs to avoid cross-source alpha name collisions.",
        ],
    }
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Alpha101 remaining factor catalog for resumable batch V4 evaluation."},
            "factors": remaining_entries,
        },
        remaining_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Combined Alpha101 catalog: smoke-passed runnable entries plus remaining pending entries."},
            "factors": combined_entries,
        },
        combined_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Alpha101 batch candidate catalog after adapter inventory eligibility checks."},
            "factors": candidate_entries,
        },
        candidate_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Alpha101 adapter holdouts excluded from V4 batch because factor values were not evaluable."},
            "factors": adapter_holdout_entries,
        },
        adapter_holdout_path,
    )
    write_yaml(adapter_config_payload(config, [str(item["name"]) for item in combined_entries]), adapter_config_path)

    rows = [
        {
            "catalog": "metadata_source",
            "path": source_path.as_posix(),
            "factor_count": len(source_entries),
            "enabled_count": int(sum(bool(item.get("enabled")) for item in source_entries)),
            "runnable_count": int(sum(bool(item.get("runnable")) for item in source_entries)),
        },
        {
            "catalog": "passed_smoke",
            "path": passed_path.as_posix(),
            "factor_count": len(passed_entries),
            "enabled_count": int(sum(bool(item.get("enabled")) for item in passed_entries)),
            "runnable_count": int(sum(bool(item.get("runnable")) for item in passed_entries)),
        },
        {
            "catalog": "remaining",
            "path": remaining_path.as_posix(),
            "factor_count": len(remaining_entries),
            "enabled_count": int(sum(bool(item.get("enabled")) for item in remaining_entries)),
            "runnable_count": int(sum(bool(item.get("runnable")) for item in remaining_entries)),
        },
        {
            "catalog": "combined",
            "path": combined_path.as_posix(),
            "factor_count": len(combined_entries),
            "enabled_count": int(sum(bool(item.get("enabled")) for item in combined_entries)),
            "runnable_count": int(sum(bool(item.get("runnable")) for item in combined_entries)),
        },
        {
            "catalog": "batch_candidate",
            "path": candidate_path.as_posix(),
            "factor_count": len(candidate_entries),
            "enabled_count": int(sum(bool(item.get("enabled")) for item in candidate_entries)),
            "runnable_count": int(sum(bool(item.get("runnable")) for item in candidate_entries)),
        },
        {
            "catalog": "adapter_holdout",
            "path": adapter_holdout_path.as_posix(),
            "factor_count": len(adapter_holdout_entries),
            "enabled_count": int(sum(bool(item.get("enabled")) for item in adapter_holdout_entries)),
            "runnable_count": int(sum(bool(item.get("runnable")) for item in adapter_holdout_entries)),
        },
    ]
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")
    lines = [
        "# Alpha101 Batch Catalogs V1",
        "",
        "This report prepares KunQuant Alpha101 factors for resumable batch V4 evaluation.",
        "",
        "## Catalog Summary",
        "",
        markdown_table(audit),
        "",
        "## Generated Adapter Config",
        "",
        f"- `{adapter_config_path.as_posix()}`",
        "",
        "## Adapter Inventory",
        "",
        f"- Inventory: `{inventory_path.as_posix()}`",
        f"- Batch candidates: `{len(candidate_entries)}`",
        f"- Adapter holdouts: `{len(adapter_holdout_entries)}`",
        "",
        "## Next Step",
        "",
        "Run the generated Alpha101 adapter config to build the combined factor frame.",
        "Then dry-run the batch runner against the batch candidate catalog before executing small batches.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Alpha101 remaining catalog written to {remaining_path}", flush=True)
    print(f"Alpha101 batch adapter config written to {adapter_config_path}", flush=True)
    return {
        "remaining": remaining_path,
        "combined": combined_path,
        "candidate": candidate_path,
        "adapter_holdout": adapter_holdout_path,
        "adapter_config": adapter_config_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Alpha101 batch catalogs after smoke promotion.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
