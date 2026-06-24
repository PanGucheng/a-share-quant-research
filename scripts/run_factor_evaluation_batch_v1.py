from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.catalog import (  # noqa: E402
    catalog_frame,
    load_factor_catalog,
    select_entries,
    validate_against_registry,
)
from factor_research.registry import FACTOR_SPECS  # noqa: E402
from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/factor_evaluation_batch_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def portable_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def parse_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def chunked(values: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        raise ValueError("batch_size must be positive")
    return [values[index : index + size] for index in range(0, len(values), size)]


def apply_cli_overrides(config: dict, args: argparse.Namespace) -> dict:
    result = dict(config)
    selection = dict(result.get("selection", {}))
    if args.names is not None:
        selection["names"] = args.names
    if args.stages is not None:
        selection["stages"] = args.stages
    if args.max_factors is not None:
        selection["max_factors"] = args.max_factors
    result["selection"] = selection
    batching = dict(result.get("batching", {}))
    if args.batch_size is not None:
        batching["batch_size"] = args.batch_size
    if args.max_batches is not None:
        batching["max_batches"] = args.max_batches
    result["batching"] = batching
    if args.output_root is not None:
        result["output_root"] = str(args.output_root)
    return result


def selected_factor_names(config: dict, catalog_path: Path, output_root: Path) -> list[str]:
    entries = load_factor_catalog(catalog_path)
    selection = config.get("selection", {})
    allow_external_specs = bool(selection.get("allow_external_specs", False))
    selected = select_entries(
        entries,
        enabled_only=bool(selection.get("enabled_only", True)),
        runnable_only=bool(selection.get("runnable_only", True)),
        stages=selection.get("stages") or None,
        categories=selection.get("categories") or None,
        sources=selection.get("sources") or None,
        names=selection.get("names") or None,
        max_factors=selection.get("max_factors"),
    )
    if not selected:
        raise ValueError("No factors selected from factor catalog")
    output_root.mkdir(parents=True, exist_ok=True)
    catalog_frame(entries).to_csv(output_root / "factor_catalog_snapshot.csv", index=False, encoding="utf-8-sig")
    catalog_frame(selected).to_csv(output_root / "selected_factor_catalog.csv", index=False, encoding="utf-8-sig")
    registry_names = [spec.name for spec in FACTOR_SPECS]
    validation = validate_against_registry(entries, registry_names)
    validation.to_csv(output_root / "factor_catalog_validation.csv", index=False, encoding="utf-8-sig")
    invalid_selected = validation[
        validation["name"].isin([entry.name for entry in selected])
        & validation["status"].ne("ok")
    ].copy()
    if allow_external_specs and not invalid_selected.empty:
        allowed_names = {entry.name for entry in selected if entry.compute_adapter != "factor_research.factor_library.add_basic_factors"}
        invalid_selected = invalid_selected[~invalid_selected["name"].isin(allowed_names)]
    if not invalid_selected.empty:
        raise ValueError(f"Selected runnable factors missing registry entries: {invalid_selected['name'].tolist()}")
    return [entry.registry_name for entry in selected]


def assert_runnable_selection_for_execution(config: dict, catalog_path: Path) -> None:
    selection = config.get("selection", {})
    execution = config.get("execution", {})
    allow_non_runnable_external = bool(execution.get("allow_non_runnable_external", False))
    allow_external_specs = bool(selection.get("allow_external_specs", False))
    entries = load_factor_catalog(catalog_path)
    selected = select_entries(
        entries,
        enabled_only=bool(selection.get("enabled_only", True)),
        runnable_only=bool(selection.get("runnable_only", True)),
        stages=selection.get("stages") or None,
        categories=selection.get("categories") or None,
        sources=selection.get("sources") or None,
        names=selection.get("names") or None,
        max_factors=selection.get("max_factors"),
    )
    blocked = []
    for entry in selected:
        if entry.runnable:
            continue
        if (
            allow_non_runnable_external
            and allow_external_specs
            and entry.compute_adapter != "factor_research.factor_library.add_basic_factors"
        ):
            continue
        blocked.append(entry.name)
    if blocked:
        raise ValueError(
            "Non-runnable catalog entries can only be planned with --dry-run. "
            f"Blocked entries: {blocked[:10]}"
        )


def make_batch_config(base_config: dict, batch_factors: list[str], batch_output_dir: Path) -> dict:
    config = dict(base_config)
    evaluation = dict(config.get("evaluation", {}))
    evaluation["factors"] = batch_factors
    evaluation["output_dir"] = portable_path(batch_output_dir)
    config["evaluation"] = evaluation
    return config


def batch_complete(batch_output_dir: Path) -> bool:
    required = [
        batch_output_dir / "evaluator_status.csv",
        batch_output_dir / "open_source_metric_index.csv",
        batch_output_dir / "factor_evaluation_v4_report.md",
    ]
    return all(path.exists() and path.stat().st_size > 0 for path in required)


def run_child(python: str, batch_config_path: Path, stdout_path: Path, stderr_path: Path) -> int:
    command = [
        python,
        str(PROJECT_ROOT / "scripts" / "run_factor_evaluation_v4.py"),
        "--config",
        str(batch_config_path),
    ]
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, stdout=stdout, stderr=stderr, text=True, check=False)
    return int(completed.returncode)


def summarize_batch_outputs(output_root: Path, manifest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in manifest.itertuples(index=False):
        batch_dir = Path(row.output_dir)
        status_path = batch_dir / "evaluator_status.csv"
        failure_path = batch_dir / "factor_failure_reasons.csv"
        metric_path = batch_dir / "open_source_metric_index.csv"
        context_metric_path = batch_dir / "context" / "context_metric_index.csv"
        evaluator_rows = len(pd.read_csv(status_path)) if status_path.exists() else 0
        failure_rows = len(pd.read_csv(failure_path)) if failure_path.exists() else 0
        metric_rows = len(pd.read_csv(metric_path)) if metric_path.exists() else 0
        context_metric_rows = len(pd.read_csv(context_metric_path)) if context_metric_path.exists() else 0
        rows.append(
            {
                "batch_id": row.batch_id,
                "status": row.status,
                "factor_count": row.factor_count,
                "factors": row.factors,
                "evaluator_status_rows": evaluator_rows,
                "failure_rows": failure_rows,
                "metric_rows": metric_rows,
                "context_metric_rows": context_metric_rows,
                "output_dir": str(batch_dir),
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(output_root / "batch_output_summary.csv", index=False, encoding="utf-8-sig")
    return result


def write_report(output_root: Path, config_path: Path, dry_run: bool, manifest: pd.DataFrame, summary: pd.DataFrame) -> None:
    status_counts = manifest.groupby("status").size().reset_index(name="batch_count") if not manifest.empty else pd.DataFrame()
    lines = [
        "# Factor Evaluation Batch V1 Report",
        "",
        f"- Config: `{portable_path(config_path)}`",
        f"- Dry run: `{str(dry_run).lower()}`",
        f"- Batch count: `{len(manifest)}`",
        f"- Total selected factors: `{int(manifest['factor_count'].sum()) if not manifest.empty else 0}`",
        "",
        "## Batch Status",
        "",
        markdown_table(status_counts),
        "",
        "## Batch Manifest",
        "",
        markdown_table(manifest[["batch_id", "status", "factor_count", "factors", "output_dir"]]),
        "",
        "## Output Summary",
        "",
        markdown_table(summary),
        "",
        "## Output Files",
        "",
        "- `factor_catalog_snapshot.csv`",
        "- `selected_factor_catalog.csv`",
        "- `factor_catalog_validation.csv`",
        "- `generated_configs/batch_*.yaml`",
        "- `batch_manifest.csv`",
        "- `batch_output_summary.csv`",
        "- `logs/batch_*.stdout.log`",
        "- `logs/batch_*.stderr.log`",
    ]
    (output_root / "factor_evaluation_batch_v1_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    config_path = resolve_path(args.config)
    config = apply_cli_overrides(load_yaml(config_path), args)
    output_root = resolve_path(config.get("output_root", "outputs/factor_evaluation_batch_v1/default"))
    base_config_path = resolve_path(config["base_config"])
    catalog_path = resolve_path(config.get("catalog", "factor_research/factor_catalog.yaml"))
    base_config = load_yaml(base_config_path)
    if not args.dry_run:
        assert_runnable_selection_for_execution(config, catalog_path)
    factors = selected_factor_names(config, catalog_path, output_root)
    batching = config.get("batching", {})
    batch_size = int(batching.get("batch_size", 2))
    resume = bool(batching.get("resume", True))
    batches = chunked(factors, batch_size)
    max_batches = batching.get("max_batches")
    if max_batches is not None:
        batches = batches[: int(max_batches)]
    python = str(config.get("python", sys.executable))

    manifest_rows = []
    for index, batch_factors in enumerate(batches, start=1):
        batch_id = f"batch_{index:03d}"
        batch_output_dir = output_root / "runs" / batch_id
        batch_config_path = output_root / "generated_configs" / f"{batch_id}.yaml"
        batch_config = make_batch_config(base_config, batch_factors, batch_output_dir)
        write_yaml(batch_config, batch_config_path)
        started_at = datetime.now().isoformat(timespec="seconds")
        start = time.perf_counter()
        returncode: int | None = None
        if args.dry_run:
            status = "planned"
        elif resume and batch_complete(batch_output_dir):
            status = "skipped_existing"
        else:
            print(f"Running {batch_id}: {', '.join(batch_factors)}", flush=True)
            returncode = run_child(
                python,
                batch_config_path,
                output_root / "logs" / f"{batch_id}.stdout.log",
                output_root / "logs" / f"{batch_id}.stderr.log",
            )
            status = "pass" if returncode == 0 else "failed"
        elapsed = time.perf_counter() - start
        manifest_rows.append(
            {
                "batch_id": batch_id,
                "status": status,
                "returncode": returncode,
                "factor_count": len(batch_factors),
                "factors": ",".join(batch_factors),
                "config_path": str(batch_config_path),
                "output_dir": str(batch_output_dir),
                "started_at": started_at,
                "ended_at": datetime.now().isoformat(timespec="seconds"),
                "elapsed_seconds": round(elapsed, 3),
            }
        )
    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(output_root / "batch_manifest.csv", index=False, encoding="utf-8-sig")
    summary = summarize_batch_outputs(output_root, manifest)
    write_report(output_root, config_path, args.dry_run, manifest, summary)
    print(f"Batch V1 outputs written to {output_root}", flush=True)
    return output_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run resumable batches of Factor Evaluation V4.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="Generate selected catalog, configs, and manifest without executing V4.")
    parser.add_argument("--names", type=parse_csv, help="Comma-separated factor names overriding config selection.")
    parser.add_argument("--stages", type=parse_csv, help="Comma-separated catalog stages overriding config selection.")
    parser.add_argument("--max-factors", type=int, help="Limit selected factors.")
    parser.add_argument("--batch-size", type=int, help="Override batch size.")
    parser.add_argument("--max-batches", type=int, help="Limit generated/executed batches.")
    parser.add_argument("--output-root", type=Path, help="Override output root.")
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
