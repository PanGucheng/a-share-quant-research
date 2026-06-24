from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.catalog import load_factor_catalog  # noqa: E402


DEFAULT_SOURCE_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml")
DEFAULT_OUTPUT_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml")
DEFAULT_EXPRESSION_DIR = Path("outputs/alpha158_expression_frame_v1/first20_main_research")
DEFAULT_V4_OUTPUT = Path("outputs/factor_evaluation_v4/alpha158_first20_smoke")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def assert_expression_validation(expression_dir: Path) -> None:
    status_path = expression_dir / "validation_status.csv"
    if not status_path.exists():
        raise FileNotFoundError(status_path)
    status = pd.read_csv(status_path)
    failed = status[status["status"].ne("pass")]
    if not failed.empty:
        raise ValueError(f"Expression validation has failed rows: {failed.to_dict(orient='records')}")


def assert_v4_smoke(v4_output: Path, factors: list[str]) -> None:
    status_path = v4_output / "evaluator_status.csv"
    context_status_path = v4_output / "context" / "context_evaluator_status.csv"
    context_metric_path = v4_output / "context" / "context_metric_index.csv"
    if not status_path.exists():
        raise FileNotFoundError(status_path)
    status = pd.read_csv(status_path)
    required_pass = status[
        status["system"].isin(["alphalens_reloaded", "qlib_eval"])
        & status["factor"].isin(factors)
        & status["status"].ne("pass")
    ]
    if not required_pass.empty:
        raise ValueError(f"Required evaluators did not pass: {required_pass.to_dict(orient='records')}")
    jq = status[status["system"].eq("jqfactor_analyzer") & status["factor"].isin(factors)]
    if jq.empty or not jq["status"].isin(["pass", "partial_pass"]).all():
        raise ValueError("jqfactor_analyzer must be pass or partial_pass for every promoted factor")
    if not context_status_path.exists() or not context_metric_path.exists():
        raise FileNotFoundError("Missing context status or metric index")
    context_status = pd.read_csv(context_status_path)
    failed_context = context_status[context_status["status"].eq("failed")]
    if not failed_context.empty:
        raise ValueError(f"Context evaluator failed: {failed_context.to_dict(orient='records')}")
    context_metric = pd.read_csv(context_metric_path)
    missing_context = sorted(set(factors) - set(context_metric["factor"].dropna().unique()))
    if missing_context:
        raise ValueError(f"Context metric index missing promoted factors: {missing_context}")


def promoted_payload(source_catalog: Path, output_catalog: Path, stage: str) -> dict:
    entries = load_factor_catalog(source_catalog)
    factors = []
    for entry in entries:
        factors.append(
            {
                "name": entry.name,
                "registry_name": entry.registry_name,
                "category": entry.category,
                "source_project": entry.source_project,
                "source_file": entry.source_file,
                "source_function": entry.source_function,
                "source_commit": entry.source_commit,
                "license": entry.license,
                "expected_direction": entry.expected_direction,
                "required_fields": list(entry.required_fields),
                "labels": list(entry.labels),
                "stage": stage,
                "enabled": True,
                "runnable": True,
                "compute_adapter": "qlib_expression_frame_v1",
                "notes": entry.notes,
            }
        )
    return {
        "version": 1,
        "updated": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "policy": {
            "purpose": "Promoted Qlib Alpha158 first-batch catalog.",
            "principle": [
                "Entries are promoted only after expression validation and V4 smoke pass.",
                "Metric definitions remain in the external evaluator outputs.",
            ],
            "source_catalog": source_catalog.as_posix(),
            "output_catalog": output_catalog.as_posix(),
        },
        "factors": factors,
    }


def run(args: argparse.Namespace) -> Path:
    source_catalog = resolve_path(args.source_catalog)
    output_catalog = resolve_path(args.output_catalog)
    expression_dir = resolve_path(args.expression_dir)
    v4_output = resolve_path(args.v4_output)
    factors = [entry.name for entry in load_factor_catalog(source_catalog)]
    assert_expression_validation(expression_dir)
    assert_v4_smoke(v4_output, factors)
    payload = promoted_payload(source_catalog, output_catalog, args.stage)
    output_catalog.parent.mkdir(parents=True, exist_ok=True)
    output_catalog.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    print(f"Promoted {len(factors)} Alpha158 entries to {output_catalog}", flush=True)
    return output_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote Alpha158 catalog entries after V4 smoke validation.")
    parser.add_argument("--source-catalog", type=Path, default=DEFAULT_SOURCE_CATALOG)
    parser.add_argument("--output-catalog", type=Path, default=DEFAULT_OUTPUT_CATALOG)
    parser.add_argument("--expression-dir", type=Path, default=DEFAULT_EXPRESSION_DIR)
    parser.add_argument("--v4-output", type=Path, default=DEFAULT_V4_OUTPUT)
    parser.add_argument("--stage", default="alpha158_first20_v4_smoke_passed")
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
