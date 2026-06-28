from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha360_strict_oos_extension_audit_v1.yaml")


@dataclass(frozen=True)
class StrictOosAuditRules:
    min_factor_count: int
    min_coverage: float
    min_passed_batches: int
    min_metric_rows: int
    allowed_partial_system: str
    allowed_partial_steps: tuple[str, ...]


@dataclass(frozen=True)
class StrictOosAuditConfig:
    expression_summary: Path
    batch_manifest: Path
    batch_output_summary: Path
    evaluator_status: Path
    failure_reasons: Path
    metric_index: Path
    output_dir: Path
    expected_factors: tuple[str, ...]
    rules: StrictOosAuditRules


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing or empty required input: {path}")
    return pd.read_csv(path)


def load_config(path: Path) -> StrictOosAuditConfig:
    payload = yaml.safe_load(resolve_path(path).read_text(encoding="utf-8")) or {}
    rules = payload.get("rules", {})
    return StrictOosAuditConfig(
        expression_summary=resolve_path(payload["expression_summary"]),
        batch_manifest=resolve_path(payload["batch_manifest"]),
        batch_output_summary=resolve_path(payload["batch_output_summary"]),
        evaluator_status=resolve_path(payload["evaluator_status"]),
        failure_reasons=resolve_path(payload["failure_reasons"]),
        metric_index=resolve_path(payload["metric_index"]),
        output_dir=resolve_path(payload.get("output_dir", "outputs/alpha360_strict_oos_extension_v1/current")),
        expected_factors=tuple(str(item) for item in payload.get("expected_factors", [])),
        rules=StrictOosAuditRules(
            min_factor_count=int(rules.get("min_factor_count", 3)),
            min_coverage=float(rules.get("min_coverage", 0.95)),
            min_passed_batches=int(rules.get("min_passed_batches", 1)),
            min_metric_rows=int(rules.get("min_metric_rows", 54)),
            allowed_partial_system=str(rules.get("allowed_partial_system", "jqfactor_analyzer")),
            allowed_partial_steps=tuple(str(item) for item in rules.get("allowed_partial_steps", [])),
        ),
    )


def build_metric_summary(metric_index: pd.DataFrame, expected_factors: tuple[str, ...]) -> pd.DataFrame:
    metric_index = metric_index.copy()
    metric_index["value"] = pd.to_numeric(metric_index["value"], errors="coerce")
    selected = metric_index[
        metric_index["factor"].isin(expected_factors)
        & metric_index["metric"].isin(
            [
                "mean_information_coefficient",
                "information_ratio",
                "annualized_return",
                "mean",
            ]
        )
    ].copy()
    selected["metric_key"] = selected["system"] + ":" + selected["metric"] + ":" + selected["horizon"].astype(str)
    pivot = selected.pivot_table(index="factor", columns="metric_key", values="value", aggfunc="first").reset_index()
    return pivot.sort_values("factor").reset_index(drop=True)


def allowed_partial_only(status: pd.DataFrame, failures: pd.DataFrame, rules: StrictOosAuditRules) -> tuple[bool, str]:
    blocking_status = status[status["status"].isin(["failed", "not_run"])]
    if not blocking_status.empty:
        return False, f"blocking_status={len(blocking_status)}"
    partial = status[status["status"].eq("partial_pass")]
    unexpected_partial = partial[partial["system"].ne(rules.allowed_partial_system)]
    if not unexpected_partial.empty:
        return False, f"unexpected_partial={len(unexpected_partial)}"
    if partial.empty:
        return True, "partial_pass=0"
    if failures.empty:
        return False, "partial_pass_without_failures"
    failure_steps = set(str(item) for item in failures["step"].dropna().unique())
    allowed_steps = set(rules.allowed_partial_steps)
    unexpected_steps = sorted(failure_steps - allowed_steps)
    if unexpected_steps:
        return False, f"unexpected_failure_steps={','.join(unexpected_steps)}"
    unexpected_systems = sorted(set(failures["system"].dropna().astype(str)) - {rules.allowed_partial_system})
    if unexpected_systems:
        return False, f"unexpected_failure_systems={','.join(unexpected_systems)}"
    return True, f"allowed_partial_rows={len(partial)}, allowed_failure_rows={len(failures)}"


def build_contract_status(
    config: StrictOosAuditConfig,
    expression: pd.DataFrame,
    batch_manifest: pd.DataFrame,
    batch_summary: pd.DataFrame,
    status: pd.DataFrame,
    failures: pd.DataFrame,
    metric_index: pd.DataFrame,
) -> pd.DataFrame:
    rules = config.rules
    factors = set(str(item) for item in expression["factor"].dropna())
    missing_factors = sorted(set(config.expected_factors) - factors)
    coverage = pd.to_numeric(expression.get("coverage", pd.Series(dtype=float)), errors="coerce")
    min_coverage = float(coverage.min()) if not coverage.empty else 0.0
    passed_batches = int(batch_manifest["status"].eq("pass").sum()) if "status" in batch_manifest.columns else 0
    metric_factors = set(str(item) for item in metric_index.get("factor", pd.Series(dtype=str)).dropna())
    allowed_partial, partial_detail = allowed_partial_only(status, failures, rules)
    rows: list[dict[str, Any]] = [
        {
            "check_id": "expected_factor_count",
            "status": "pass" if len(factors) >= rules.min_factor_count and not missing_factors else "blocked",
            "detail": f"factors={len(factors)}, missing={','.join(missing_factors)}",
        },
        {
            "check_id": "expression_coverage",
            "status": "pass" if min_coverage >= rules.min_coverage else "blocked",
            "detail": f"min_coverage={min_coverage:.6f}",
        },
        {
            "check_id": "batch_passed",
            "status": "pass" if passed_batches >= rules.min_passed_batches else "blocked",
            "detail": f"passed_batches={passed_batches}",
        },
        {
            "check_id": "metric_index_rows",
            "status": "pass" if len(metric_index) >= rules.min_metric_rows else "blocked",
            "detail": f"metric_rows={len(metric_index)}",
        },
        {
            "check_id": "metric_factor_coverage",
            "status": "pass" if set(config.expected_factors).issubset(metric_factors) else "blocked",
            "detail": f"metric_factors={len(metric_factors)}",
        },
        {
            "check_id": "evaluator_status_allowed",
            "status": "pass" if allowed_partial else "blocked",
            "detail": partial_detail,
        },
        {
            "check_id": "no_training_side_effect",
            "status": "pass",
            "detail": "strict_oos_audit_only",
        },
    ]
    if not batch_summary.empty:
        rows.append(
            {
                "check_id": "batch_summary_metric_rows",
                "status": "pass"
                if int(pd.to_numeric(batch_summary.get("metric_rows", pd.Series([0])), errors="coerce").fillna(0).sum())
                >= rules.min_metric_rows
                else "blocked",
                "detail": "summary_metric_rows="
                + str(int(pd.to_numeric(batch_summary.get("metric_rows", pd.Series([0])), errors="coerce").fillna(0).sum())),
            }
        )
    return pd.DataFrame(rows)


def write_report(
    config: StrictOosAuditConfig,
    contract: pd.DataFrame,
    expression: pd.DataFrame,
    batch_manifest: pd.DataFrame,
    batch_summary: pd.DataFrame,
    status: pd.DataFrame,
    failures: pd.DataFrame,
    metric_summary: pd.DataFrame,
) -> None:
    lines = [
        "# Alpha360 Strict OOS Extension V1",
        "",
        "- Scope: strict OOS diagnostics for 3 reviewed Alpha360 probes.",
        "- Boundary: no model training, no strategy optimization, no evaluator definition changes.",
        f"- Expression summary: `{portable_path(config.expression_summary)}`",
        f"- Metric index: `{portable_path(config.metric_index)}`",
        "",
        "## Contract Status",
        "",
        markdown_table(contract),
        "",
        "## Expression Coverage",
        "",
        markdown_table(expression),
        "",
        "## Batch Manifest",
        "",
        markdown_table(batch_manifest),
        "",
        "## Batch Output Summary",
        "",
        markdown_table(batch_summary),
        "",
        "## Evaluator Status",
        "",
        markdown_table(status),
        "",
        "## Failure Reasons",
        "",
        markdown_table(failures) if not failures.empty else "No failures were recorded.",
        "",
        "## Metric Summary",
        "",
        markdown_table(metric_summary),
        "",
        "## Notes",
        "",
        "- jqfactor_analyzer partial pass is allowed only for the known factor_returns/factor_alpha_beta index-name issue.",
        "- This stage confirms evaluability and recent-OOS diagnostics; it does not promote factors into training inputs.",
    ]
    (config.output_dir / "alpha360_strict_oos_extension_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_audit(config: StrictOosAuditConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    expression = read_csv_required(config.expression_summary)
    batch_manifest = read_csv_required(config.batch_manifest)
    batch_summary = read_csv_required(config.batch_output_summary)
    status = read_csv_required(config.evaluator_status)
    failures = pd.read_csv(config.failure_reasons) if config.failure_reasons.exists() else pd.DataFrame()
    metric_index = read_csv_required(config.metric_index)
    metric_summary = build_metric_summary(metric_index, config.expected_factors)
    contract = build_contract_status(config, expression, batch_manifest, batch_summary, status, failures, metric_index)

    expression.to_csv(config.output_dir / "strict_oos_expression_summary.csv", index=False, encoding="utf-8-sig")
    batch_manifest.to_csv(config.output_dir / "strict_oos_batch_manifest.csv", index=False, encoding="utf-8-sig")
    batch_summary.to_csv(config.output_dir / "strict_oos_batch_output_summary.csv", index=False, encoding="utf-8-sig")
    status.to_csv(config.output_dir / "strict_oos_evaluator_status.csv", index=False, encoding="utf-8-sig")
    failures.to_csv(config.output_dir / "strict_oos_failure_reasons.csv", index=False, encoding="utf-8-sig")
    metric_summary.to_csv(config.output_dir / "strict_oos_metric_summary.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(config.output_dir / "strict_oos_contract_status.csv", index=False, encoding="utf-8-sig")
    write_report(config, contract, expression, batch_manifest, batch_summary, status, failures, metric_summary)
    return {
        "contract_status": contract,
        "metric_summary": metric_summary,
        "expression_summary": expression,
        "evaluator_status": status,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Alpha360 strict OOS extension V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    config = load_config(build_parser().parse_args().config)
    outputs = run_audit(config)
    blocked = outputs["contract_status"][outputs["contract_status"]["status"].eq("blocked")]
    print(f"Alpha360 strict OOS extension audit written to {config.output_dir}", flush=True)
    print(f"Contract rows: {len(outputs['contract_status'])}", flush=True)
    print(f"Metric summary rows: {len(outputs['metric_summary'])}", flush=True)
    if not blocked.empty:
        raise SystemExit(f"Alpha360 strict OOS contract blocked: {blocked.to_dict(orient='records')}")


if __name__ == "__main__":
    main()
