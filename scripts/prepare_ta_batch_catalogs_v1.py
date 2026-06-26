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


DEFAULT_CONFIG = Path("configs/ta_factor_batch_catalogs_v1.yaml")


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
    notes = str(result.get("notes", "")).strip()
    result["notes"] = f"{notes} {note_suffix}".strip()
    return result


def run(config_path: Path) -> dict[str, Path]:
    config = load_yaml(resolve_path(config_path))
    source_path = resolve_path(config["source_catalog"])
    passed_path = resolve_path(config["passed_catalog"])
    remaining_path = resolve_path(config["remaining_catalog"])
    combined_path = resolve_path(config["combined_catalog"])
    audit_path = resolve_path(config["audit_output"])
    report_path = resolve_path(config["report_output"])

    source = load_yaml(source_path)
    passed = load_yaml(passed_path)
    stages = config.get("stages", {})
    remaining_config = config.get("remaining", {})
    passed_names = {str(item["name"]) for item in passed.get("factors", [])}
    source_entries = [dict(item) for item in source.get("factors", [])]
    remaining_entries = [
        with_stage(
            entry,
            stage=str(stages.get("remaining", "ta_adapter_remaining_v4_pending")),
            enabled=bool(remaining_config.get("enabled", False)),
            runnable=bool(remaining_config.get("runnable", False)),
            note_suffix="Pending TA batch V4 evaluation.",
        )
        for entry in source_entries
        if str(entry.get("name")) not in passed_names
    ]
    passed_entries = [dict(item) for item in passed.get("factors", [])]
    combined_entries = sorted(passed_entries + remaining_entries, key=lambda item: str(item["name"]))

    common_policy = {
        "required_prefilter": ["data_quality", "tradability"],
        "principle": [
            "TA formulas are sourced from the local upstream ta repository.",
            "Excluded TA columns are not included in these catalogs.",
            "Remaining entries are disabled/non-runnable until batch V4 promotion.",
        ],
    }
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-26",
            "policy": {
                **common_policy,
                "purpose": "TA remaining factor catalog for resumable batch V4 evaluation.",
            },
            "factors": remaining_entries,
        },
        remaining_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-26",
            "policy": {
                **common_policy,
                "purpose": "Combined TA catalog: smoke-passed runnable entries plus remaining pending entries.",
            },
            "factors": combined_entries,
        },
        combined_path,
    )
    rows = [
        {
            "catalog": "source_smoke",
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
    ]
    audit = pd.DataFrame(rows)
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")
    lines = [
        "# TA Batch Catalogs V1",
        "",
        "This report prepares TA factors for resumable batch V4 evaluation.",
        "",
        "## Catalog Summary",
        "",
        markdown_table(audit),
        "",
        "## Next Step",
        "",
        "Run `scripts/run_factor_evaluation_batch_v1.py --config configs/factor_evaluation_batch_v1_ta_remaining74.yaml --dry-run` first.",
        "Then execute small batches with `--max-batches` before full resume execution.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"TA remaining catalog written to {remaining_path}", flush=True)
    return {"remaining": remaining_path, "combined": combined_path, "report": report_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare TA batch catalogs after smoke promotion.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
