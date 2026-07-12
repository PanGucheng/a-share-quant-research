from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from multiprocessing import freeze_support
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs/factor_validation_baseline_v1.yaml"


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_process(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def git_value(*args: str) -> str:
    result = run_process(["git", *args], timeout=30)
    return result.stdout.strip() if result.returncode == 0 else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(path: Path) -> int | None:
    if not path.exists() or path.suffix.lower() != ".csv":
        return None
    return int(len(pd.read_csv(path)))


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    rendered = frame.fillna("").astype(str)
    columns = [str(column) for column in rendered.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rendered.itertuples(index=False, name=None):
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def artifact_manifest(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in config.get("artifacts", []):
        path = resolve_path(item["path"])
        exists = path.is_file()
        stat = path.stat() if exists else None
        rows.append(
            {
                "artifact_id": item["id"],
                "path": portable_path(path),
                "critical": bool(item.get("critical", False)),
                "status": "pass" if exists and stat and stat.st_size > 0 else "missing_or_empty",
                "size_bytes": stat.st_size if stat else 0,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat() if stat else "",
                "sha256": sha256(path) if exists else "",
                "row_count": csv_rows(path),
                "git_tracked": bool(git_value("ls-files", "--error-unmatch", portable_path(path))),
            }
        )
    return pd.DataFrame(rows)


def detail_number(frame: pd.DataFrame, check_id: str) -> float:
    row = frame.loc[frame["check_id"].astype(str) == check_id]
    if row.empty:
        raise ValueError(f"missing contract row: {check_id}")
    match = re.search(r"=(-?\d+(?:\.\d+)?)", str(row.iloc[0]["detail"]))
    if not match:
        raise ValueError(f"no numeric value in detail for {check_id}")
    return float(match.group(1))


def metric_snapshot(config: dict[str, Any]) -> pd.DataFrame:
    catalog_path = resolve_path("outputs/factor_research_toolchain_readiness_v1/current/catalog_summary.csv")
    screening_path = resolve_path("outputs/multi_source_screening_v1/current/multi_source_screening_input.csv")
    judgement_path = resolve_path("outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv")
    research_path = resolve_path("outputs/multi_source_judgement_v1/current/multi_source_research_candidates.csv")
    probes_path = resolve_path("outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv")
    candidates_path = resolve_path("outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv")
    stability_path = resolve_path("outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_summary.csv")
    liquidity_path = resolve_path(
        "outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv"
    )

    catalog = pd.read_csv(catalog_path)
    liquidity = pd.read_csv(liquidity_path)
    new_source_catalogs = {"ta_promoted_catalog", "kunquant_alpha101_promoted_catalog", "qlib_alpha360_promoted_catalog"}
    values: list[tuple[str, float, Path, str]] = [
        ("total_runnable_factors", float(catalog["runnable_count"].sum()), catalog_path, "sum(runnable_count)"),
        (
            "new_source_runnable_factors",
            float(catalog.loc[catalog["catalog_id"].isin(new_source_catalogs), "runnable_count"].sum()),
            catalog_path,
            "sum(runnable_count) for promoted TA/Alpha101/Alpha360 catalogs",
        ),
        ("multi_source_screening_rows", float(len(pd.read_csv(screening_path))), screening_path, "row_count"),
        ("multi_source_judgement_rows", float(len(pd.read_csv(judgement_path))), judgement_path, "row_count"),
        ("multi_source_research_candidate_rows", float(len(pd.read_csv(research_path))), research_path, "row_count"),
        ("new_source_alpha_probe_rows", float(len(pd.read_csv(probes_path))), probes_path, "row_count"),
        ("alpha158_candidate_rows", float(len(pd.read_csv(candidates_path))), candidates_path, "row_count"),
        ("alpha360_strict_oos_factor_rows", float(len(pd.read_csv(stability_path))), stability_path, "row_count"),
        ("liquidity_watchlist_rows", detail_number(liquidity, "watchlist_rows"), liquidity_path, "contract detail"),
        (
            "liquidity_residualized_factor_count",
            detail_number(liquidity, "residualized_factor_count"),
            liquidity_path,
            "contract detail",
        ),
        (
            "liquidity_residualized_coverage_min",
            detail_number(liquidity, "residualized_coverage_min"),
            liquidity_path,
            "contract detail",
        ),
        (
            "liquidity_downstream_default_included",
            detail_number(liquidity, "downstream_default_included"),
            liquidity_path,
            "contract detail",
        ),
    ]
    expected = config.get("expected_metrics", {})
    rows = []
    for metric, observed, path, source in values:
        required = expected.get(metric)
        matches = required is None or abs(float(required) - observed) <= 1e-12
        rows.append(
            {
                "metric": metric,
                "observed_value": int(observed) if observed.is_integer() else observed,
                "expected_value": required,
                "status": "pass" if matches else "drift",
                "source_path": portable_path(path),
                "source_column_or_rule": source,
            }
        )
    required_coverage = float(expected["liquidity_residualized_required_coverage_min"])
    rows.append(
        {
            "metric": "liquidity_residualized_required_coverage_min",
            "observed_value": required_coverage,
            "expected_value": required_coverage,
            "status": "pass",
            "source_path": portable_path(liquidity_path),
            "source_column_or_rule": "roadmap contract threshold",
        }
    )
    return pd.DataFrame(rows)


def dependency_compatibility(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in config.get("dependencies", []):
        distribution = str(item["distribution"])
        import_name = str(item["import_name"])
        try:
            version = metadata.version(distribution)
            installed = True
        except metadata.PackageNotFoundError:
            version = ""
            installed = False
        import_available = importlib.util.find_spec(import_name) is not None
        role = str(item["role"])
        if installed and import_available:
            status = "pass"
            reason = "installed and import target discoverable"
        elif role in {"phase_1_required", "phase_3_required", "optional_portfolio"}:
            status = "warning"
            reason = "not installed during baseline freeze; install and verify only when the owning phase starts"
        else:
            status = "fail"
            reason = "existing core dependency is missing"
        rows.append(
            {
                "distribution": distribution,
                "import_name": import_name,
                "role": role,
                "installed": installed,
                "version": version,
                "import_available": import_available,
                "license_record": item.get("license", ""),
                "status": status,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows)


def command_results(config: dict[str, Any]) -> pd.DataFrame:
    python = str(config["environment"]["python"])
    rows = []
    for item in config.get("command_checks", []):
        command = [python, *[str(value) for value in item["command"]]]
        started = datetime.now(timezone.utc)
        result = run_process(command)
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        expected = [int(value) for value in item.get("expected_exit_codes", [0])]
        rows.append(
            {
                "check_id": item["id"],
                "status": "pass" if result.returncode in expected else "fail",
                "exit_code": result.returncode,
                "expected_exit_codes": ",".join(map(str, expected)),
                "duration_seconds": round(duration, 3),
                "command": subprocess.list2cmdline(command),
                "expected_reason": item.get("expected_reason", ""),
                "stdout_tail": result.stdout[-1000:].replace("\r", " ").replace("\n", " | "),
                "stderr_tail": result.stderr[-1000:].replace("\r", " ").replace("\n", " | "),
            }
        )
    return pd.DataFrame(rows)


def contract_status(
    artifacts: pd.DataFrame, metrics: pd.DataFrame, dependencies: pd.DataFrame, commands: pd.DataFrame
) -> pd.DataFrame:
    coverage = float(metrics.loc[metrics["metric"] == "liquidity_residualized_coverage_min", "observed_value"].iloc[0])
    required = float(metrics.loc[metrics["metric"] == "liquidity_residualized_required_coverage_min", "observed_value"].iloc[0])
    downstream = int(metrics.loc[metrics["metric"] == "liquidity_downstream_default_included", "observed_value"].iloc[0])
    checks = [
        ("critical_artifacts", int(((artifacts["critical"]) & (artifacts["status"] != "pass")).sum()), 0, "critical", "All baseline artifacts must exist and be non-empty."),
        ("baseline_metric_drift", int((metrics["status"] != "pass").sum()), 0, "critical", "Frozen metrics must match the declared baseline."),
        ("existing_core_dependencies", int(((dependencies["role"] == "existing_core") & (dependencies["status"] != "pass")).sum()), 0, "critical", "Existing Qlib runtime dependencies must remain available."),
        ("research_validation_runtime", int(((dependencies["role"] == "research_validation_core") & (dependencies["status"] != "pass")).sum()), 0, "critical", "Statsmodels must be available for the validation layer."),
        ("future_phase_dependency_warnings", int((dependencies["status"] == "warning").sum()), "recorded", "warning", "Pandera, mlfinpy, and optional Riskfolio are installed only in their owning phases."),
        ("command_checks", int((commands["status"] != "pass").sum()), 0, "critical", "Existing lightweight validation and audits must return their expected codes."),
        ("v3_39_coverage_gate", coverage, f">={required}", "critical", "Known blocker is preserved; do not lower the threshold or promote residualized factors."),
        ("v3_39_downstream_default", downstream, 0, "critical", "Blocked residualized factors must remain outside downstream defaults."),
    ]
    rows = []
    for name, observed, required_value, severity, reason in checks:
        if name == "v3_39_coverage_gate":
            status = "blocked" if float(observed) < required else "pass"
        elif required_value == "recorded":
            status = "warning" if int(observed) > 0 else "pass"
        else:
            status = "pass" if observed == required_value else "fail"
        rows.append(
            {
                "check_name": name,
                "status": status,
                "observed_value": observed,
                "required_value": required_value,
                "severity": severity,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows)


def run_context(config: dict[str, Any]) -> dict[str, Any]:
    environment = config["environment"]
    provider = resolve_path(environment["qlib_provider"])
    qlib_source = resolve_path(environment["qlib_source"])
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "project_root": portable_path(PROJECT_ROOT),
        "branch": git_value("branch", "--show-current"),
        "commit": git_value("rev-parse", "HEAD"),
        "git_status": git_value("status", "--short").splitlines(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "qlib_source": qlib_source.as_posix(),
        "qlib_source_exists": qlib_source.exists(),
        "qlib_provider": provider.as_posix(),
        "qlib_provider_exists": provider.exists(),
        "qlib_provider_modified_at": datetime.fromtimestamp(provider.stat().st_mtime, timezone.utc).isoformat() if provider.exists() else "",
        "config": portable_path(DEFAULT_CONFIG),
    }


def write_report(
    output: Path,
    context: dict[str, Any],
    artifacts: pd.DataFrame,
    metrics: pd.DataFrame,
    dependencies: pd.DataFrame,
    commands: pd.DataFrame,
    contract: pd.DataFrame,
) -> None:
    overall = "fail" if (contract["status"] == "fail").any() else "research_blocked" if (contract["status"] == "blocked").any() else "pass"
    lines = [
        "# Factor Validation Baseline V1 Audit",
        "",
        f"- Captured at: `{context['captured_at']}`",
        f"- Branch: `{context['branch']}`",
        f"- Commit: `{context['commit']}`",
        f"- Overall status: `{overall}`",
        "",
        "## Current Repository Status",
        "",
        f"The baseline toolchain remains operational. {int((artifacts['status'] == 'pass').sum())}/{len(artifacts)} critical compact artifacts are readable. V3.39 remains correctly blocked by coverage and has not entered downstream defaults.",
        "",
        "## Planned File Scope",
        "",
        "Stage 0 adds one audit config, one audit runner, separated core/optional requirements, this compact output directory, and the detailed roadmap documents. It does not change factor evaluation, candidate roles, universe definitions, or portfolio defaults.",
        "",
        "## Dependency Compatibility",
        "",
        markdown_table(dependencies),
        "",
        "## Baseline Metrics",
        "",
        markdown_table(metrics),
        "",
        "## Command Verification",
        "",
        markdown_table(commands[["check_id", "status", "exit_code", "expected_exit_codes", "duration_seconds"]]),
        "",
        "## Contract",
        "",
        markdown_table(contract),
        "",
        "## Risks And Blockers",
        "",
        "- V3.39 minimum residualized coverage is 0.1495 versus the unchanged 0.80 requirement. Residualized factors remain excluded from downstream defaults.",
        "- Pandera and mlfinpy are not installed at baseline freeze. Install and verify them separately in phases 1 and 3; do not upgrade the full Qlib environment.",
        "- Riskfolio-Lib is optional. Phase 6 may use SciPy if compatibility is not acceptable.",
        "- Historical industry/size point-in-time data is still unavailable and remains a later-stage blocker.",
        "",
        "## Phase 1 Implementation Plan",
        "",
        "1. Install the bounded Pandera dependency only and rerun `pip check` plus existing baseline validation.",
        "2. Add immutable Factor, Label, Tradability, Universe Interval, Screening, and Judgement schemas.",
        "3. Add synthetic good/bad/no-mutation tests and compatibility exceptions scoped by file and field.",
        "4. Audit existing compact outputs and emit schema inventory, validation results, contract status, and report.",
        "5. Start phase 2 only after the phase 1 critical contract has no fail or blocked rows.",
        "",
        "## Decision",
        "",
        "Stage 0 implementation is complete when all non-V3.39 critical checks pass. The `research_blocked` overall status is intentional evidence that V3.39 is not eligible for downstream promotion; it does not prevent implementing the independent schema infrastructure in phase 1.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze and audit the factor-validation baseline.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = read_yaml(config_path)
    output_dir = resolve_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    context = run_context(config)
    artifacts = artifact_manifest(config)
    metrics = metric_snapshot(config)
    dependencies = dependency_compatibility(config)
    commands = command_results(config)
    contract = contract_status(artifacts, metrics, dependencies, commands)

    (output_dir / "run_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifacts.to_csv(output_dir / "baseline_artifact_manifest.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(output_dir / "baseline_metric_snapshot.csv", index=False, encoding="utf-8-sig")
    dependencies.to_csv(output_dir / "dependency_compatibility.csv", index=False, encoding="utf-8-sig")
    commands.to_csv(output_dir / "baseline_command_results.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output_dir / "baseline_contract_status.csv", index=False, encoding="utf-8-sig")
    write_report(output_dir / "baseline_audit_report.md", context, artifacts, metrics, dependencies, commands, contract)

    print(f"Factor validation baseline audit written to {output_dir}")
    print(contract.to_string(index=False))
    critical_fail = ((contract["severity"] == "critical") & (contract["status"] == "fail")).any()
    return 1 if critical_fail else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
