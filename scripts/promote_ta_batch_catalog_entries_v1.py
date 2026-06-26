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


DEFAULT_CONFIG = Path("configs/ta_factor_batch_promotion_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def load_batch_outputs(batch_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    status_frames = []
    failure_frames = []
    metric_frames = []
    for run_dir in sorted((batch_root / "runs").glob("batch_*")):
        status_path = run_dir / "evaluator_status.csv"
        failure_path = run_dir / "factor_failure_reasons.csv"
        metric_path = run_dir / "open_source_metric_index.csv"
        if status_path.exists():
            status_frames.append(pd.read_csv(status_path).assign(batch=run_dir.name))
        if failure_path.exists():
            failure_frames.append(pd.read_csv(failure_path).assign(batch=run_dir.name))
        if metric_path.exists():
            metric_frames.append(pd.read_csv(metric_path).assign(batch=run_dir.name))
    status = pd.concat(status_frames, ignore_index=True) if status_frames else pd.DataFrame()
    failures = pd.concat(failure_frames, ignore_index=True) if failure_frames else pd.DataFrame()
    metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    return status, failures, metrics


def failure_steps(failures: pd.DataFrame, factor: str, system: str) -> set[str]:
    if failures.empty:
        return set()
    rows = failures[(failures["factor"].eq(factor)) & (failures["system"].eq(system))]
    return set(rows["step"].astype(str))


def system_status(status: pd.DataFrame, factor: str, system: str) -> str:
    rows = status[(status["factor"].eq(factor)) & (status["system"].eq(system))]
    if rows.empty:
        return "missing"
    values = set(rows["status"].astype(str))
    if values == {"pass"}:
        return "pass"
    if "failed" in values:
        return "failed"
    if "partial_pass" in values:
        return "partial_pass"
    return ",".join(sorted(values))


def classify_factor(factor: str, status: pd.DataFrame, failures: pd.DataFrame, promotion: dict) -> tuple[str, str]:
    required = [str(item) for item in promotion.get("required_pass_systems", [])]
    allowed_partial = {
        str(system): {str(step) for step in steps}
        for system, steps in promotion.get("allowed_partial_systems", {}).items()
    }
    holdout_partial = {
        str(system): {str(step) for step in steps}
        for system, steps in promotion.get("holdout_partial_systems", {}).items()
    }
    for system in required:
        current = system_status(status, factor, system)
        if current == "pass":
            continue
        steps = failure_steps(failures, factor, system)
        if current == "partial_pass" and system in holdout_partial and steps.issubset(holdout_partial[system]):
            return "holdout", f"{system}_partial:{','.join(sorted(steps))}"
        return "holdout", f"{system}_{current}"
    for system, allowed_steps in allowed_partial.items():
        current = system_status(status, factor, system)
        if current in {"missing", "pass"}:
            continue
        steps = failure_steps(failures, factor, system)
        if current == "partial_pass" and steps.issubset(allowed_steps):
            continue
        return "holdout", f"{system}_{current}:{','.join(sorted(steps))}"
    return "promoted", "required_pass_allowed_partials_only"


def update_entry(entry: dict, *, stage: str, enabled: bool, runnable: bool, suffix: str) -> dict:
    result = dict(entry)
    result["stage"] = stage
    result["enabled"] = bool(enabled)
    result["runnable"] = bool(runnable)
    notes = str(result.get("notes", "")).replace("Pending TA batch V4 evaluation.", "").strip()
    result["notes"] = f"{notes} {suffix}".strip()
    return result


def run(config_path: Path) -> dict[str, Path]:
    config = load_yaml(resolve_path(config_path))
    source_path = resolve_path(config["source_catalog"])
    existing_path = resolve_path(config["existing_passed_catalog"])
    batch_root = resolve_path(config["batch_root"])
    batch_passed_path = resolve_path(config["batch_passed_catalog"])
    holdout_path = resolve_path(config["holdout_catalog"])
    combined_path = resolve_path(config["combined_promoted_catalog"])
    audit_path = resolve_path(config["promotion_audit"])
    metric_output = resolve_path(config["metric_index_output"])
    report_path = resolve_path(config["report_output"])
    promotion = config.get("promotion", {})

    source = load_yaml(source_path)
    existing = load_yaml(existing_path)
    source_entries = {str(item["name"]): dict(item) for item in source.get("factors", [])}
    existing_entries = [dict(item) for item in existing.get("factors", [])]
    status, failures, metrics = load_batch_outputs(batch_root)
    if status.empty:
        raise FileNotFoundError(f"No evaluator_status.csv files found under {batch_root / 'runs'}")

    promoted_entries = []
    holdout_entries = []
    audit_rows = []
    for factor, entry in source_entries.items():
        decision, reason = classify_factor(factor, status, failures, promotion)
        alpha_status = system_status(status, factor, "alphalens_reloaded")
        jq_status = system_status(status, factor, "jqfactor_analyzer")
        qlib_status = system_status(status, factor, "qlib_eval")
        if decision == "promoted":
            promoted_entries.append(
                update_entry(
                    entry,
                    stage=str(promotion.get("passed_stage", "ta_adapter_v4_batch_passed")),
                    enabled=True,
                    runnable=True,
                    suffix="TA batch V4 passed.",
                )
            )
        else:
            holdout_entries.append(
                update_entry(
                    entry,
                    stage=str(promotion.get("holdout_stage", "ta_adapter_v4_batch_holdout")),
                    enabled=False,
                    runnable=False,
                    suffix=f"TA batch V4 holdout: {reason}.",
                )
            )
        audit_rows.append(
            {
                "factor": factor,
                "decision": decision,
                "reason": reason,
                "alphalens_status": alpha_status,
                "jqfactor_status": jq_status,
                "qlib_status": qlib_status,
            }
        )

    common_policy = {
        "required_prefilter": ["data_quality", "tradability"],
        "principle": [
            "TA formulas are sourced from the local upstream ta repository.",
            "Promoted entries require Alphalens Reloaded and Qlib eval pass.",
            "jqfactor_analyzer partial_pass is allowed only for known factor_returns/factor_alpha_beta index-name failures.",
            "Alphalens quantile_turnover partial failures are held out for review.",
        ],
    }
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-26",
            "policy": {**common_policy, "purpose": "TA batch-passed factors after remaining74 V4 evaluation."},
            "factors": promoted_entries,
        },
        batch_passed_path,
    )
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-26",
            "policy": {**common_policy, "purpose": "TA holdout factors after remaining74 V4 evaluation."},
            "factors": holdout_entries,
        },
        holdout_path,
    )
    combined = sorted(existing_entries + promoted_entries, key=lambda item: str(item["name"]))
    write_yaml(
        {
            "version": 1,
            "updated": "2026-06-26",
            "policy": {**common_policy, "purpose": "Combined TA promoted catalog: smoke passed plus batch passed."},
            "factors": combined,
        },
        combined_path,
    )
    audit = pd.DataFrame(audit_rows).sort_values(["decision", "factor"])
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")
    metrics.to_csv(metric_output, index=False, encoding="utf-8-sig")
    decision_counts = audit.groupby("decision").size().reset_index(name="count")
    status_counts = status.groupby(["system", "status"]).size().reset_index(name="count")
    failure_counts = (
        failures.groupby(["system", "step", "error"]).size().reset_index(name="count")
        if not failures.empty
        else pd.DataFrame()
    )
    lines = [
        "# TA Batch Promotion V1",
        "",
        f"- Batch root: `{batch_root.as_posix()}`",
        f"- Source factors: `{len(source_entries)}`",
        f"- Batch promoted: `{len(promoted_entries)}`",
        f"- Batch holdout: `{len(holdout_entries)}`",
        f"- Combined promoted: `{len(combined)}`",
        "",
        "## Decision Counts",
        "",
        markdown_table(decision_counts),
        "",
        "## Evaluator Status",
        "",
        markdown_table(status_counts),
        "",
        "## Failure Counts",
        "",
        markdown_table(failure_counts),
        "",
        "## Holdout Factors",
        "",
        markdown_table(audit[audit["decision"].eq("holdout")]),
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"TA batch promotion catalog written to {combined_path}", flush=True)
    return {"combined": combined_path, "audit": audit_path, "report": report_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote TA remaining batch factors after V4 evaluation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
