from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.catalog import FactorCatalogEntry, load_factor_catalog  # noqa: E402


DEFAULT_SOURCE_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_pending.yaml")
DEFAULT_OUTPUT_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_runnable.yaml")
DEFAULT_HOLDOUT_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_holdout.yaml")
DEFAULT_AUDIT_PATH = Path("outputs/factor_catalog_alpha158_v1/alpha158_remaining138_promotion_audit.csv")
DEFAULT_FULL_OUTPUT_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml")
DEFAULT_FIRST20_RUNNABLE = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml")
DEFAULT_EXPRESSION_DIR = Path("outputs/alpha158_expression_frame_v1/full158_main_research")
DEFAULT_BATCH_ROOT = Path("outputs/factor_evaluation_batch_v1/alpha158_remaining138")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def entry_mapping(entry: FactorCatalogEntry, *, stage: str, enabled: bool = True, runnable: bool = True) -> dict:
    payload = asdict(entry)
    payload["required_fields"] = list(entry.required_fields)
    payload["labels"] = list(entry.labels)
    payload["stage"] = stage
    payload["enabled"] = enabled
    payload["runnable"] = runnable
    payload["compute_adapter"] = "qlib_expression_frame_v1"
    return payload


def catalog_payload(factors: list[dict], purpose: str, source_catalogs: list[Path]) -> dict:
    return {
        "version": 1,
        "updated": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "policy": {
            "purpose": purpose,
            "principle": [
                "Entries are promoted only after expression validation, V4 batch evaluation, and context validation pass.",
                "Metric definitions remain in the external evaluator outputs.",
                "This catalog marks factors as runnable for research workflows, not approved for trading or model training.",
            ],
            "source_catalogs": [path.as_posix() for path in source_catalogs],
        },
        "factors": factors,
    }


def assert_expression_validation(expression_dir: Path) -> None:
    status_path = expression_dir / "validation_status.csv"
    coverage_path = expression_dir / "validation_factor_coverage.csv"
    if not status_path.exists() or not coverage_path.exists():
        raise FileNotFoundError(f"Missing expression validation outputs under {expression_dir}")
    status = pd.read_csv(status_path)
    failed = status[status["status"].ne("pass")]
    if not failed.empty:
        raise ValueError(f"Expression validation failed: {failed.to_dict(orient='records')}")
    coverage = pd.read_csv(coverage_path)
    empty = coverage[pd.to_numeric(coverage["valid_rows"], errors="coerce").fillna(0).le(0)]
    if not empty.empty:
        raise ValueError(f"Expression frame has empty factors: {empty['factor'].tolist()}")


def audit_batch_outputs(batch_root: Path, factors: list[str]) -> pd.DataFrame:
    manifest_path = batch_root / "batch_manifest.csv"
    summary_path = batch_root / "batch_output_summary.csv"
    if not manifest_path.exists() or not summary_path.exists():
        raise FileNotFoundError(f"Missing batch manifest or summary under {batch_root}")
    manifest = pd.read_csv(manifest_path)
    failed = manifest[manifest["status"].eq("failed")]
    if not failed.empty:
        raise ValueError(f"Batch manifest has failed batches: {failed.to_dict(orient='records')}")
    summary = pd.read_csv(summary_path)
    missing_output = summary[
        pd.to_numeric(summary["metric_rows"], errors="coerce").fillna(0).le(0)
        | pd.to_numeric(summary["context_metric_rows"], errors="coerce").fillna(0).le(0)
    ]
    if not missing_output.empty:
        raise ValueError(f"Batch summary has missing metrics: {missing_output.to_dict(orient='records')}")
    rows: dict[str, dict] = {
        factor: {
            "factor": factor,
            "alphalens_status": "",
            "jqfactor_status": "",
            "qlib_status": "",
            "context_failed_count": 0,
            "failure_steps": "",
            "promotable": False,
            "holdout_reason": "",
        }
        for factor in factors
    }
    failure_frames = []
    for row in manifest.itertuples(index=False):
        batch_dir = Path(row.output_dir)
        status_path = batch_dir / "evaluator_status.csv"
        context_status_path = batch_dir / "context" / "context_evaluator_status.csv"
        context_metric_path = batch_dir / "context" / "context_metric_index.csv"
        if not status_path.exists() or not context_status_path.exists() or not context_metric_path.exists():
            raise FileNotFoundError(f"Missing V4 outputs under {batch_dir}")
        evaluator_status = pd.read_csv(status_path)
        batch_factors = sorted(set(evaluator_status["factor"].dropna().astype(str)))
        for status_row in evaluator_status.itertuples(index=False):
            factor = str(status_row.factor)
            if factor not in rows:
                continue
            system = str(status_row.system)
            if system == "alphalens_reloaded":
                rows[factor]["alphalens_status"] = str(status_row.status)
            elif system == "jqfactor_analyzer":
                rows[factor]["jqfactor_status"] = str(status_row.status)
            elif system == "qlib_eval":
                rows[factor]["qlib_status"] = str(status_row.status)
        context_status = pd.read_csv(context_status_path)
        context_failed = context_status[context_status["status"].eq("failed")]
        if not context_failed.empty:
            raise ValueError(f"Context evaluator failed under {batch_dir}: {context_failed.to_dict(orient='records')}")
        failed_counts = context_failed.groupby("factor").size().to_dict() if "factor" in context_failed.columns else {}
        for factor in batch_factors:
            if factor in rows:
                rows[factor]["context_failed_count"] = int(failed_counts.get(factor, 0))
        failure_path = batch_dir / "factor_failure_reasons.csv"
        if failure_path.exists():
            failure_frames.append(pd.read_csv(failure_path))
    factors_seen = {
        factor
        for factor, row in rows.items()
        if row["alphalens_status"] or row["jqfactor_status"] or row["qlib_status"]
    }
    missing = sorted(set(factors) - factors_seen)
    if missing:
        raise ValueError(f"Batch outputs missing promoted factors: {missing}")
    failures = pd.concat(failure_frames, ignore_index=True) if failure_frames else pd.DataFrame()
    if not failures.empty:
        grouped = failures.groupby("factor")["step"].apply(lambda values: ",".join(sorted(set(map(str, values))))).to_dict()
        for factor, steps in grouped.items():
            if factor in rows:
                rows[factor]["failure_steps"] = steps
    audit = pd.DataFrame(rows.values()).sort_values("factor").reset_index(drop=True)
    for index, row in audit.iterrows():
        reasons = []
        if row["alphalens_status"] != "pass":
            reasons.append(f"alphalens={row['alphalens_status'] or 'missing'}")
        if row["qlib_status"] != "pass":
            reasons.append(f"qlib={row['qlib_status'] or 'missing'}")
        if row["jqfactor_status"] not in {"pass", "partial_pass"}:
            reasons.append(f"jqfactor={row['jqfactor_status'] or 'missing'}")
        if int(row["context_failed_count"]) > 0:
            reasons.append(f"context_failed={row['context_failed_count']}")
        if reasons:
            audit.at[index, "holdout_reason"] = ";".join(reasons)
            audit.at[index, "promotable"] = False
        else:
            audit.at[index, "promotable"] = True
    return audit


def run(args: argparse.Namespace) -> tuple[Path, Path]:
    source_catalog = resolve_path(args.source_catalog)
    output_catalog = resolve_path(args.output_catalog)
    holdout_catalog = resolve_path(args.holdout_catalog)
    audit_path = resolve_path(args.audit_path)
    full_output_catalog = resolve_path(args.full_output_catalog)
    first20_catalog = resolve_path(args.first20_runnable)
    expression_dir = resolve_path(args.expression_dir)
    batch_root = resolve_path(args.batch_root)
    source_entries = load_factor_catalog(source_catalog)
    factors = [entry.name for entry in source_entries]
    assert_expression_validation(expression_dir)
    audit = audit_batch_outputs(batch_root, factors)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")
    promotable = set(audit.loc[audit["promotable"].eq(True), "factor"])
    holdout = set(audit.loc[audit["promotable"].ne(True), "factor"])
    promoted = [entry_mapping(entry, stage=args.stage) for entry in source_entries if entry.name in promotable]
    holdout_entries = [
        entry_mapping(entry, stage=args.holdout_stage, enabled=False, runnable=False)
        for entry in source_entries
        if entry.name in holdout
    ]
    output_catalog.parent.mkdir(parents=True, exist_ok=True)
    output_catalog.write_text(
        yaml.safe_dump(
            catalog_payload(promoted, "Promoted Alpha158 remaining138 runnable catalog.", [source_catalog]),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    holdout_catalog.write_text(
        yaml.safe_dump(
            catalog_payload(holdout_entries, "Alpha158 remaining138 holdout catalog.", [source_catalog]),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    first20_entries = [entry_mapping(entry, stage=entry.stage) for entry in load_factor_catalog(first20_catalog)]
    full_output_catalog.write_text(
        yaml.safe_dump(
            catalog_payload(
                first20_entries + promoted,
                "Full Alpha158 runnable catalog: first20 plus remaining138.",
                [first20_catalog, output_catalog],
            ),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    print(f"Promoted {len(promoted)} remaining Alpha158 entries to {output_catalog}", flush=True)
    print(f"Holdout Alpha158 entries: {len(holdout_entries)} -> {holdout_catalog}", flush=True)
    print(f"Promotion audit written to {audit_path}", flush=True)
    print(f"Full Alpha158 runnable catalog written to {full_output_catalog}", flush=True)
    return output_catalog, full_output_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote Alpha158 batch-evaluated catalog entries.")
    parser.add_argument("--source-catalog", type=Path, default=DEFAULT_SOURCE_CATALOG)
    parser.add_argument("--output-catalog", type=Path, default=DEFAULT_OUTPUT_CATALOG)
    parser.add_argument("--holdout-catalog", type=Path, default=DEFAULT_HOLDOUT_CATALOG)
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--full-output-catalog", type=Path, default=DEFAULT_FULL_OUTPUT_CATALOG)
    parser.add_argument("--first20-runnable", type=Path, default=DEFAULT_FIRST20_RUNNABLE)
    parser.add_argument("--expression-dir", type=Path, default=DEFAULT_EXPRESSION_DIR)
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
    parser.add_argument("--stage", default="alpha158_remaining138_v4_batch_passed")
    parser.add_argument("--holdout-stage", default="alpha158_remaining138_v4_batch_holdout")
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
