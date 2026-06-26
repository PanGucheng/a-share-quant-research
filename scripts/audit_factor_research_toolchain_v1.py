from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import freeze_support
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.catalog import catalog_frame, load_factor_catalog  # noqa: E402
from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/factor_research_toolchain_readiness_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def portable_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def count_file_rows(path: Path, yaml_key: str | None = None) -> int | None:
    if not path.exists() or path.stat().st_size <= 0:
        return None
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return int(len(pd.read_csv(path)))
    if suffix in {".yaml", ".yml"}:
        payload = load_yaml(path)
        value = payload.get(yaml_key) if yaml_key else None
        if value is None:
            for key in ("factors", "sources", "planned_sources"):
                if isinstance(payload.get(key), list):
                    value = payload[key]
                    break
        return int(len(value)) if isinstance(value, list) else None
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return int(len(data))
        if isinstance(data, dict):
            return int(len(data))
    if suffix in {".md", ".txt", ".log"}:
        return int(len(path.read_text(encoding="utf-8", errors="ignore").splitlines()))
    return None


def audit_catalogs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    catalog_rows: list[dict[str, Any]] = []
    entries_frames: list[pd.DataFrame] = []
    for item in config.get("catalogs", []):
        catalog_id = str(item["id"])
        path = resolve_path(item["path"])
        if not path.exists():
            catalog_rows.append(
                {
                    "catalog_id": catalog_id,
                    "path": portable_path(path),
                    "status": "missing",
                    "factor_count": 0,
                    "enabled_count": 0,
                    "runnable_count": 0,
                    "role": item.get("role", ""),
                }
            )
            continue
        entries = load_factor_catalog(path)
        frame = catalog_frame(entries)
        if not frame.empty:
            frame.insert(0, "catalog_id", catalog_id)
            entries_frames.append(frame)
        catalog_rows.append(
            {
                "catalog_id": catalog_id,
                "path": portable_path(path),
                "status": "pass" if entries else "empty",
                "factor_count": int(len(entries)),
                "enabled_count": int(sum(entry.enabled for entry in entries)),
                "runnable_count": int(sum(entry.runnable for entry in entries)),
                "role": item.get("role", ""),
            }
        )
    all_entries = pd.concat(entries_frames, ignore_index=True) if entries_frames else pd.DataFrame()
    if all_entries.empty:
        stage_counts = pd.DataFrame(
            columns=["catalog_id", "source_project", "stage", "enabled", "runnable", "factor_count"]
        )
    else:
        stage_counts = (
            all_entries.groupby(["catalog_id", "source_project", "stage", "enabled", "runnable"], dropna=False)
            .size()
            .reset_index(name="factor_count")
            .sort_values(["catalog_id", "source_project", "stage", "enabled", "runnable"])
        )
    return pd.DataFrame(catalog_rows), all_entries, stage_counts


def audit_sources(config: dict[str, Any], all_entries: pd.DataFrame) -> pd.DataFrame:
    catalog_payload = load_yaml(resolve_path(config["catalogs"][0]["path"]))
    planned_sources = catalog_payload.get("planned_sources", [])
    manifest_path = resolve_path(config["source_manifest"])
    manifest_payload = load_yaml(manifest_path) if manifest_path.exists() else {}
    manifest_sources = {str(item.get("id")): item for item in manifest_payload.get("sources", [])}
    entry_counts = (
        all_entries.groupby("source_project")
        .agg(
            catalog_factor_count=("name", "count"),
            runnable_factor_count=("runnable", "sum"),
            enabled_factor_count=("enabled", "sum"),
        )
        .reset_index()
        if not all_entries.empty
        else pd.DataFrame(columns=["source_project", "catalog_factor_count", "runnable_factor_count", "enabled_factor_count"])
    )
    count_map = entry_counts.set_index("source_project").to_dict("index") if not entry_counts.empty else {}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source in planned_sources:
        source_project = str(source.get("source_project", ""))
        seen.add(source_project)
        local_path = resolve_path(source.get("local_path", ""))
        source_file = str(source.get("source_file", ""))
        source_file_path = local_path / source_file if source_file else local_path
        declared_status = str(source.get("status", ""))
        counts = count_map.get(source_project, {})
        runnable_count = int(counts.get("runnable_factor_count", 0))
        if runnable_count > 0:
            readiness = "ready"
            readiness_reason = "runnable catalog entries available"
        elif "pending" in declared_status or "future" in declared_status:
            readiness = "adapter_pending"
            readiness_reason = "source registered but calculation adapter is not promoted"
        elif declared_status == "design_reference":
            readiness = "reference_only"
            readiness_reason = "design reference, not a runnable factor source"
        else:
            readiness = "metadata_only"
            readiness_reason = "registered source has no runnable factors"
        rows.append(
            {
                "source_project": source_project,
                "manifest_id": "",
                "declared_status": declared_status,
                "license": source.get("license", ""),
                "local_path": portable_path(local_path),
                "local_path_status": "available" if local_path.exists() else "missing",
                "source_file": source_file,
                "source_file_status": "available" if source_file_path.exists() else "missing",
                "catalog_factor_count": int(counts.get("catalog_factor_count", 0)),
                "enabled_factor_count": int(counts.get("enabled_factor_count", 0)),
                "runnable_factor_count": runnable_count,
                "readiness": readiness,
                "readiness_reason": readiness_reason,
            }
        )

    for manifest_id, source in manifest_sources.items():
        source_project = manifest_id
        if source_project in seen:
            continue
        local_path = resolve_path(source.get("local_path", ""))
        source_files = source.get("source_files", [])
        file_statuses = []
        for source_file in source_files:
            candidate = local_path / str(source_file.get("path", ""))
            file_statuses.append("available" if candidate.exists() else "missing")
        declared_status = str(source.get("local_adapter", ""))
        counts = count_map.get(source_project, {})
        rows.append(
            {
                "source_project": source_project,
                "manifest_id": manifest_id,
                "declared_status": declared_status,
                "license": source.get("license", ""),
                "local_path": portable_path(local_path),
                "local_path_status": "available" if local_path.exists() else "missing",
                "source_file": ",".join(str(item.get("path", "")) for item in source_files),
                "source_file_status": "available" if file_statuses and all(status == "available" for status in file_statuses) else "partial_or_missing",
                "catalog_factor_count": int(counts.get("catalog_factor_count", 0)),
                "enabled_factor_count": int(counts.get("enabled_factor_count", 0)),
                "runnable_factor_count": int(counts.get("runnable_factor_count", 0)),
                "readiness": "reference_or_evaluator",
                "readiness_reason": source.get("planned_role", ""),
            }
        )
    return pd.DataFrame(rows).sort_values(["readiness", "source_project"])


def audit_contracts(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in config.get("required_output_contracts", []):
        path = resolve_path(item["path"])
        row_count = count_file_rows(path, item.get("yaml_key")) if path.exists() else None
        min_rows = item.get("min_rows")
        if not path.exists():
            status = "missing"
        elif path.stat().st_size <= 0:
            status = "empty"
        elif min_rows is not None and row_count is not None and row_count < int(min_rows):
            status = "below_min_rows"
        else:
            status = "pass"
        rows.append(
            {
                "contract_id": item["id"],
                "group": item.get("group", ""),
                "path": portable_path(path),
                "status": status,
                "row_count": row_count,
                "min_rows": min_rows,
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return pd.DataFrame(rows)


def audit_configs(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    systems: list[str] = []
    for item in config.get("batch_configs", []):
        path = resolve_path(item["path"])
        rows.append(
            {
                "config_id": item["id"],
                "kind": "batch",
                "path": portable_path(path),
                "status": "pass" if path.exists() and path.stat().st_size > 0 else "missing_or_empty",
                "detail": "",
            }
        )
    for item in config.get("evaluation_configs", []):
        path = resolve_path(item["path"])
        detail = ""
        if path.exists():
            payload = load_yaml(path)
            systems = [str(system) for system in payload.get("evaluation", {}).get("systems", [])]
            window = payload.get("window", {})
            tradability_dir = resolve_path(window.get("tradability_dir", "")) if window else None
            data_quality_dir = resolve_path(window.get("data_quality_dir", "")) if window else None
            detail = (
                f"systems={','.join(systems)}; "
                f"tradability_dir={'available' if tradability_dir and tradability_dir.exists() else 'missing'}; "
                f"data_quality_dir={'available' if data_quality_dir and data_quality_dir.exists() else 'missing'}"
            )
        rows.append(
            {
                "config_id": item["id"],
                "kind": "evaluation",
                "path": portable_path(path),
                "status": "pass" if path.exists() and path.stat().st_size > 0 else "missing_or_empty",
                "detail": detail,
            }
        )
    return pd.DataFrame(rows), systems


def build_readiness_checks(
    config: dict[str, Any],
    catalog_summary: pd.DataFrame,
    source_readiness: pd.DataFrame,
    contract_status: pd.DataFrame,
    config_status: pd.DataFrame,
    evaluator_systems: list[str],
) -> pd.DataFrame:
    rules = config.get("large_scale_rules", {})
    required_prefilter = set(str(item) for item in rules.get("required_prefilter", []))
    required_systems = set(str(item) for item in rules.get("required_evaluator_systems", []))
    catalog_payload = load_yaml(resolve_path(config["catalogs"][0]["path"]))
    manifest_payload = load_yaml(resolve_path(config["source_manifest"]))
    catalog_prefilter = set(catalog_payload.get("policy", {}).get("required_prefilter", []))
    manifest_prefilter = set(manifest_payload.get("policy", {}).get("required_prefilter", []))
    contract_missing = contract_status[contract_status["status"].ne("pass")]
    total_runnable = int(catalog_summary["runnable_count"].sum()) if not catalog_summary.empty else 0
    baseline_sources = set(str(item) for item in rules.get("baseline_sources", []))
    new_source_rows = source_readiness[
        ~source_readiness["source_project"].isin(baseline_sources)
        & source_readiness["readiness"].eq("ready")
    ]
    new_source_runnable = int(new_source_rows["runnable_factor_count"].sum()) if not new_source_rows.empty else 0
    rows = []

    def add(check_id: str, status: str, detail: str, recommendation: str) -> None:
        rows.append(
            {
                "check_id": check_id,
                "status": status,
                "detail": detail,
                "recommendation": recommendation,
            }
        )

    add(
        "prefilter_policy",
        "pass" if required_prefilter.issubset(catalog_prefilter) and required_prefilter.issubset(manifest_prefilter) else "blocked",
        f"catalog={','.join(sorted(catalog_prefilter))}; manifest={','.join(sorted(manifest_prefilter))}",
        "Keep data_quality and tradability as mandatory prefilters for every new factor source.",
    )
    add(
        "open_source_evaluator_systems",
        "pass" if required_systems.issubset(set(evaluator_systems)) else "blocked",
        f"systems={','.join(evaluator_systems)}",
        "Do not replace external evaluator definitions; keep Alphalens Reloaded, jqfactor_analyzer, Qlib eval, and project_current coexisting.",
    )
    add(
        "batch_runner",
        "pass" if config_status[config_status["kind"].eq("batch")]["status"].eq("pass").all() else "blocked",
        f"batch_configs={len(config_status[config_status['kind'].eq('batch')])}",
        "Use the batch runner for large jobs, with dry-run, resume, manifests, and logs.",
    )
    add(
        "required_output_contracts",
        "pass" if contract_missing.empty else "blocked",
        f"missing_or_failed={len(contract_missing)}",
        "Repair missing contracts before launching full-scale screening.",
    )
    add(
        "runnable_factor_inventory",
        "pass" if total_runnable >= int(rules.get("min_total_runnable_factors", 0)) else "partial",
        f"total_runnable={total_runnable}",
        "Alpha158 is enough to validate the machinery; more sources are needed for broad factor discovery.",
    )
    add(
        "new_source_adapter_inventory",
        "pass" if new_source_runnable >= int(rules.get("min_new_source_runnable_factors", 0)) else "blocked",
        f"new_source_runnable={new_source_runnable}",
        (
            "Expand the promoted non-Alpha158 catalog with resumable TA batch V4 before adding Alpha101."
            if new_source_runnable > 0
            else "Promote at least one non-Alpha158 open-source factor family, starting with an audited TA or Alpha101 adapter."
        ),
    )
    add(
        "generic_multi_source_screening",
        "partial",
        "Alpha158 has a mature specific screening/judgement/pool path; generic screening_v3 exists but is not yet the large-scale multi-source standard.",
        "Generalize the screening input and candidate-pool contracts before mixing TA, Alpha101, and future factors.",
    )
    return pd.DataFrame(rows)


def write_report(
    output_dir: Path,
    checks: pd.DataFrame,
    catalog_summary: pd.DataFrame,
    source_readiness: pd.DataFrame,
    contract_status: pd.DataFrame,
    stage_counts: pd.DataFrame,
) -> None:
    blocked = checks[checks["status"].eq("blocked")]
    partial = checks[checks["status"].eq("partial")]
    overall = "blocked" if not blocked.empty else ("partial" if not partial.empty else "ready")
    lines = [
        "# Factor Research Toolchain Readiness V1",
        "",
        f"- Overall status: `{overall}`",
        "- Scope: factor research and factor screening only.",
        "- Boundary: no Qlib baseline replacement, no new model training, no live trading, no evaluator definition changes.",
        "",
        "## Conclusion",
        "",
    ]
    if overall == "blocked":
        new_source = checks[checks["check_id"].eq("new_source_adapter_inventory")]
        detail = str(new_source.iloc[0]["detail"]) if not new_source.empty else ""
        if detail == "new_source_runnable=0":
            lines.extend(
                [
                    "The Alpha158 research path is reproducible, but the multi-source large-scale factor path is not ready yet.",
                    "The main blocker is that non-Alpha158 factor sources are registered as open-source references but do not yet have promoted runnable adapters.",
                ]
            )
        else:
            lines.extend(
                [
                    "The Alpha158 research path is reproducible, and a non-Alpha158 source has smoke-level runnable factors.",
                    "The multi-source large-scale path is still blocked because the promoted non-Alpha158 inventory is below the configured threshold.",
                ]
            )
    elif overall == "partial":
        lines.append("The toolchain can run validated Alpha158 research, but still needs one promoted non-Alpha158 source before broad discovery.")
    else:
        lines.append("The factor research toolchain is ready for large-scale multi-source screening.")
    lines.extend(
        [
            "",
            "## Readiness Checks",
            "",
            markdown_table(checks),
            "",
            "## Catalog Summary",
            "",
            markdown_table(catalog_summary),
            "",
            "## Source Readiness",
            "",
            markdown_table(
                source_readiness[
                    [
                        "source_project",
                        "declared_status",
                        "license",
                        "local_path_status",
                        "source_file_status",
                        "runnable_factor_count",
                        "readiness",
                        "readiness_reason",
                    ]
                ].head(40)
            ),
            "",
            "## Required Output Contracts",
            "",
            markdown_table(contract_status),
            "",
            "## Stage Counts",
            "",
            markdown_table(stage_counts.head(80)),
            "",
            "## Next Step",
            "",
            "1. Keep Alpha158 as the validated reference pipeline, not the next research bottleneck.",
            "2. Promote the first non-Alpha158 open-source source adapter, preferably `ta` because the local source is present and license is MIT.",
            "3. Run the new source through dry-run, smoke, partial batch, then full batch before adding it to the candidate pool.",
            "4. Generalize screening and candidate-pool contracts so Alpha158, TA, Alpha101, and later sources can coexist without rewriting evaluator metrics.",
        ]
    )
    (output_dir / "toolchain_readiness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> Path:
    config = load_yaml(resolve_path(config_path))
    output_dir = resolve_path(config.get("output_dir", "outputs/factor_research_toolchain_readiness_v1/current"))
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog_summary, all_entries, stage_counts = audit_catalogs(config)
    source_readiness = audit_sources(config, all_entries)
    contract_status = audit_contracts(config)
    config_status, evaluator_systems = audit_configs(config)
    checks = build_readiness_checks(
        config,
        catalog_summary,
        source_readiness,
        contract_status,
        config_status,
        evaluator_systems,
    )

    write_csv(catalog_summary, output_dir / "catalog_summary.csv")
    write_csv(all_entries, output_dir / "factor_catalog_entries.csv")
    write_csv(stage_counts, output_dir / "factor_stage_counts.csv")
    write_csv(source_readiness, output_dir / "source_readiness.csv")
    write_csv(contract_status, output_dir / "required_output_contracts.csv")
    write_csv(config_status, output_dir / "config_status.csv")
    write_csv(checks, output_dir / "toolchain_readiness_checks.csv")
    write_report(output_dir, checks, catalog_summary, source_readiness, contract_status, stage_counts)
    print(f"Factor research toolchain readiness outputs written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit factor research readiness before large-scale factor expansion.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args().config)


if __name__ == "__main__":
    main()
