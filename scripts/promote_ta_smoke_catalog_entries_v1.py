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


DEFAULT_CONFIG = Path("configs/ta_factor_smoke_promotion_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def allowed_partial_pass(factor: str, system: str, failures: pd.DataFrame, allowed_steps: list[str]) -> bool:
    rows = failures[(failures["factor"].eq(factor)) & (failures["system"].eq(system))]
    if rows.empty:
        return True
    return set(rows["step"].astype(str)).issubset(set(allowed_steps))


def factor_promotion_status(
    factor: str,
    evaluator_status: pd.DataFrame,
    failures: pd.DataFrame,
    promotion: dict,
) -> tuple[bool, str]:
    required = [str(item) for item in promotion.get("required_pass_systems", [])]
    allowed_partial = {
        str(system): [str(step) for step in steps]
        for system, steps in promotion.get("allowed_partial_systems", {}).items()
    }
    status_rows = evaluator_status[evaluator_status["factor"].eq(factor)]
    missing_required = []
    for system in required:
        rows = status_rows[status_rows["system"].eq(system)]
        if rows.empty or not rows["status"].eq("pass").any():
            missing_required.append(system)
    if missing_required:
        return False, f"missing_required_pass:{','.join(missing_required)}"
    for system, allowed_steps in allowed_partial.items():
        rows = status_rows[status_rows["system"].eq(system)]
        if rows.empty:
            continue
        statuses = set(rows["status"].astype(str))
        if statuses <= {"pass"}:
            continue
        if "partial_pass" in statuses and allowed_partial_pass(factor, system, failures, allowed_steps):
            continue
        return False, f"blocked_partial:{system}"
    return True, "required_systems_passed_allowed_partials_only"


def promote_catalog(config_path: Path) -> Path:
    config = load_yaml(resolve_path(config_path))
    source_catalog_path = resolve_path(config["source_catalog"])
    evaluator_status_path = resolve_path(config["evaluator_status"])
    failure_path = resolve_path(config["failure_reasons"])
    selected_path = resolve_path(config["selected_factors"])
    output_catalog_path = resolve_path(config["output_catalog"])
    audit_output = resolve_path(config["audit_output"])
    report_output = resolve_path(config["report_output"])
    promotion = config.get("promotion", {})

    source_payload = load_yaml(source_catalog_path)
    evaluator_status = pd.read_csv(evaluator_status_path)
    failures = pd.read_csv(failure_path) if failure_path.exists() and failure_path.stat().st_size > 0 else pd.DataFrame()
    selected = pd.read_csv(selected_path)
    selected_factors = selected["factor"].astype(str).tolist()
    source_entries = {str(item["name"]): dict(item) for item in source_payload.get("factors", [])}

    promoted = []
    audit_rows = []
    for factor in selected_factors:
        passed, reason = factor_promotion_status(factor, evaluator_status, failures, promotion)
        entry = source_entries.get(factor)
        audit_rows.append(
            {
                "factor": factor,
                "source_catalog_present": entry is not None,
                "promoted": bool(passed and entry is not None),
                "reason": reason if entry is not None else "missing_source_catalog_entry",
            }
        )
        if passed and entry is not None:
            entry["stage"] = str(promotion.get("stage", "ta_adapter_v4_smoke_passed"))
            entry["enabled"] = bool(promotion.get("enabled", True))
            entry["runnable"] = bool(promotion.get("runnable", True))
            entry["notes"] = f"{entry.get('notes', '')} V4 smoke passed for selected TA adapter factor.".strip()
            promoted.append(entry)

    output_payload = {
        "version": 1,
        "updated": "2026-06-26",
        "policy": {
            "purpose": "Promoted TA smoke factors after V4 adapter evaluation.",
            "principle": [
                "This is a smoke-level runnable catalog, not the full TA source catalog.",
                "Promoted entries require Alphalens Reloaded and Qlib eval pass.",
                "jqfactor_analyzer partial_pass is allowed only for known factor_returns/factor_alpha_beta index-name failures.",
                "data_quality and tradability remain mandatory prefilters.",
            ],
            "required_prefilter": ["data_quality", "tradability"],
        },
        "factors": promoted,
    }
    output_catalog_path.parent.mkdir(parents=True, exist_ok=True)
    output_catalog_path.write_text(yaml.safe_dump(output_payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    audit = pd.DataFrame(audit_rows)
    audit.to_csv(audit_output, index=False, encoding="utf-8-sig")
    lines = [
        "# TA Smoke Promotion V1",
        "",
        f"- Source catalog: `{source_catalog_path.as_posix()}`",
        f"- Output catalog: `{output_catalog_path.as_posix()}`",
        f"- Selected factors: `{len(selected_factors)}`",
        f"- Promoted factors: `{len(promoted)}`",
        "",
        "## Audit",
        "",
        markdown_table(audit),
    ]
    report_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"TA smoke promotion catalog written to {output_catalog_path}", flush=True)
    return output_catalog_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote selected TA smoke factors after V4 evaluation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    promote_catalog(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
