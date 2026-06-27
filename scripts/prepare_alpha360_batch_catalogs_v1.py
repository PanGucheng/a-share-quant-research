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


DEFAULT_CONFIG = Path("configs/alpha360_factor_batch_catalogs_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
    result["compute_adapter"] = "qlib_expression_adapter_pending"
    notes = str(result.get("notes", "")).strip()
    result["notes"] = f"{notes} {note_suffix}".strip()
    return result


def expression_adapter_config(config: dict, candidate_catalog: Path, selected_count: int) -> dict:
    adapter = config["expression_adapter"]
    return {
        "provider_uri": adapter["provider_uri"],
        "market": adapter["market"],
        "start": adapter["start"],
        "end": adapter["end"],
        "max_instruments": adapter.get("max_instruments"),
        "catalog_path": portable_path(candidate_catalog),
        "inventory_path": "outputs/factor_catalog_alpha360_v1/alpha360_formula_inventory.csv",
        "output_dir": adapter["output_dir"],
        "selection": {
            "enabled_only": False,
            "runnable_only": False,
            "stages": [config["candidate"].get("stage", "alpha360_adapter_batch_v4_pending")],
            "names": [],
            "max_factors": selected_count,
        },
        "expression": {
            "batch_size": int(adapter.get("batch_size", 20)),
        },
        "cache": {
            "refresh": bool(adapter.get("refresh", False)),
        },
    }


def batch_base_config(config: dict, candidate_catalog: Path) -> dict:
    base = config["v4_base"]
    expression = config["expression_adapter"]
    return {
        "qlib": {
            "provider_uri": base["provider_uri"],
            "market": base["market"],
        },
        "evaluation": {
            "output_dir": base["output_dir"],
            "labels": [str(item) for item in base.get("labels", [])],
            "factors": [],
            "systems": [str(item) for item in base.get("systems", [])],
            "quantiles": int(base.get("quantiles", 5)),
            "min_count": int(base.get("min_count", 50)),
            "sample_rows": int(base.get("sample_rows", 200)),
        },
        "window": {
            "name": base["window_name"],
            "start": base["start"],
            "end": base["end"],
            "tradability_dir": base["tradability_dir"],
            "data_quality_dir": base["data_quality_dir"],
        },
        "tradable_filter": {
            "min_liquidity_bucket": int(base.get("min_liquidity_bucket", 3)),
            "min_tradability_score": float(base.get("min_tradability_score", 75.0)),
        },
        "cache": {
            "feature_cache_dir": "tmp/factor_feature_cache",
            "factor_cache_dir": "tmp/factor_frame_cache",
            "refresh_feature_cache": False,
            "refresh_factor_cache": False,
        },
        "external_factor_frame": {
            "enabled": True,
            "path": str(Path(expression["output_dir"]) / "factor_frame.pkl").replace("\\", "/"),
            "catalog_path": portable_path(candidate_catalog),
            "require_enabled": False,
            "require_runnable": False,
        },
        "context": {
            "enabled": bool(base.get("context_enabled", False)),
        },
    }


def batch_runner_config(config: dict, candidate_catalog: Path, base_config_path: Path) -> dict:
    runner = config["batch_runner"]
    return {
        "base_config": portable_path(base_config_path),
        "catalog": portable_path(candidate_catalog),
        "python": runner["python"],
        "output_root": runner["output_root"],
        "selection": {
            "enabled_only": False,
            "runnable_only": False,
            "allow_external_specs": True,
            "stages": [config["candidate"].get("stage", "alpha360_adapter_batch_v4_pending")],
            "categories": [],
            "sources": ["qlib_alpha360"],
            "names": [],
            "max_factors": None,
        },
        "execution": {
            "allow_non_runnable_external": True,
        },
        "batching": {
            "batch_size": int(runner.get("batch_size", 5)),
            "resume": bool(runner.get("resume", True)),
            "max_batches": runner.get("max_batches"),
        },
    }


def run(config_path: Path) -> dict[str, Path]:
    config = load_yaml(resolve_path(config_path))
    source_path = resolve_path(config["source_catalog"])
    candidate_path = resolve_path(config["batch_candidate_catalog"])
    holdout_path = resolve_path(config["adapter_holdout_catalog"])
    combined_path = resolve_path(config["combined_catalog"])
    audit_path = resolve_path(config["audit_output"])
    report_path = resolve_path(config["report_output"])
    expression_config_path = resolve_path(config["expression_config_output"])
    batch_base_config_path = resolve_path(config["batch_base_config_output"])
    batch_runner_config_path = resolve_path(config["batch_runner_config_output"])

    source = load_yaml(source_path)
    source_entries = [dict(item) for item in source.get("factors", [])]
    holdout_names = {str(item) for item in config.get("holdout", {}).get("names", [])}
    holdout_reason = str(config.get("holdout", {}).get("reason", "adapter_holdout"))
    candidate_stage = str(config.get("candidate", {}).get("stage", "alpha360_adapter_batch_v4_pending"))
    holdout_stage = str(config.get("holdout", {}).get("stage", "alpha360_adapter_constant_holdout"))

    candidate_entries = [
        with_stage(
            entry,
            stage=candidate_stage,
            enabled=bool(config.get("candidate", {}).get("enabled", False)),
            runnable=bool(config.get("candidate", {}).get("runnable", False)),
            note_suffix="Pending Alpha360 batch V4 evaluation.",
        )
        for entry in source_entries
        if str(entry.get("name")) not in holdout_names
    ]
    holdout_entries = [
        with_stage(
            entry,
            stage=holdout_stage,
            enabled=False,
            runnable=False,
            note_suffix=f"Alpha360 adapter holdout: {holdout_reason}.",
        )
        for entry in source_entries
        if str(entry.get("name")) in holdout_names
    ]
    combined_entries = sorted(candidate_entries + holdout_entries, key=lambda item: str(item["name"]))

    common_policy = {
        "required_prefilter": ["data_quality", "tradability"],
        "principle": [
            "Alpha360 formulas are sourced from the local Qlib repository.",
            "Batch candidates remain disabled/non-runnable until V4 promotion.",
            "Constant normalization identities are held out before batch evaluation.",
        ],
    }
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Alpha360 batch candidate catalog after adapter smoke and V4 smoke."},
            "factors": candidate_entries,
        },
        candidate_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Alpha360 adapter holdouts excluded from batch because they are constant normalization identities."},
            "factors": holdout_entries,
        },
        holdout_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-28",
            "policy": {**common_policy, "purpose": "Combined Alpha360 catalog: batch candidates plus adapter holdouts."},
            "factors": combined_entries,
        },
        combined_path,
    )
    write_yaml(expression_adapter_config(config, candidate_path, len(candidate_entries)), expression_config_path)
    write_yaml(batch_base_config(config, candidate_path), batch_base_config_path)
    write_yaml(batch_runner_config(config, candidate_path, batch_base_config_path), batch_runner_config_path)

    audit = pd.DataFrame(
        [
            {
                "catalog": "source_all",
                "path": portable_path(source_path),
                "factor_count": len(source_entries),
                "enabled_count": int(sum(bool(item.get("enabled")) for item in source_entries)),
                "runnable_count": int(sum(bool(item.get("runnable")) for item in source_entries)),
            },
            {
                "catalog": "batch_candidate",
                "path": portable_path(candidate_path),
                "factor_count": len(candidate_entries),
                "enabled_count": int(sum(bool(item.get("enabled")) for item in candidate_entries)),
                "runnable_count": int(sum(bool(item.get("runnable")) for item in candidate_entries)),
            },
            {
                "catalog": "adapter_holdout",
                "path": portable_path(holdout_path),
                "factor_count": len(holdout_entries),
                "enabled_count": int(sum(bool(item.get("enabled")) for item in holdout_entries)),
                "runnable_count": int(sum(bool(item.get("runnable")) for item in holdout_entries)),
            },
            {
                "catalog": "combined",
                "path": portable_path(combined_path),
                "factor_count": len(combined_entries),
                "enabled_count": int(sum(bool(item.get("enabled")) for item in combined_entries)),
                "runnable_count": int(sum(bool(item.get("runnable")) for item in combined_entries)),
            },
        ]
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")

    lines = [
        "# Alpha360 Batch Catalogs V1",
        "",
        "This report prepares Qlib Alpha360 factors for resumable batch V4 evaluation.",
        "",
        "## Catalog Summary",
        "",
        markdown_table(audit),
        "",
        "## Holdout Rule",
        "",
        f"- Holdout names: `{', '.join(sorted(holdout_names))}`",
        f"- Reason: `{holdout_reason}`",
        "",
        "## Generated Configs",
        "",
        f"- Expression adapter: `{portable_path(expression_config_path)}`",
        f"- V4 batch base: `{portable_path(batch_base_config_path)}`",
        f"- Batch runner: `{portable_path(batch_runner_config_path)}`",
        "",
        "## Next Step",
        "",
        "Run the generated expression adapter config to build the Alpha360 batch factor frame.",
        "Then dry-run the batch runner before executing small resumable batches.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if len(source_entries) != 360:
        raise ValueError(f"Expected 360 Alpha360 source entries, got {len(source_entries)}")
    if len(candidate_entries) != 358:
        raise ValueError(f"Expected 358 Alpha360 batch candidates, got {len(candidate_entries)}")
    if len(holdout_entries) != 2:
        raise ValueError(f"Expected 2 Alpha360 adapter holdouts, got {len(holdout_entries)}")

    print(f"Alpha360 batch candidate catalog written to {candidate_path}", flush=True)
    print(f"Alpha360 adapter holdout catalog written to {holdout_path}", flush=True)
    return {
        "candidate": candidate_path,
        "holdout": holdout_path,
        "combined": combined_path,
        "expression_config": expression_config_path,
        "batch_runner_config": batch_runner_config_path,
        "report": report_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Alpha360 batch catalogs after smoke evaluation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
