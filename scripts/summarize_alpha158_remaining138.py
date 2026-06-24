from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402


DEFAULT_BATCH_ROOT = Path("outputs/factor_evaluation_batch_v1/alpha158_remaining138")
DEFAULT_AUDIT = Path("outputs/factor_catalog_alpha158_v1/alpha158_remaining138_promotion_audit.csv")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def batch_dirs(batch_root: Path) -> list[Path]:
    runs = batch_root / "runs"
    return sorted([path for path in runs.glob("batch_*") if path.is_dir()])


def build_metric_index(batch_root: Path) -> pd.DataFrame:
    rows = []
    for batch_dir in batch_dirs(batch_root):
        batch_id = batch_dir.name
        open_source = read_csv(batch_dir / "open_source_metric_index.csv")
        context = read_csv(batch_dir / "context" / "context_metric_index.csv")
        for row in open_source.itertuples(index=False):
            rows.append(
                {
                    "batch_id": batch_id,
                    "scope": "open_source",
                    "system": row.system,
                    "factor": row.factor,
                    "return_mode": "",
                    "group_dimension": "",
                    "metric": row.metric,
                    "group": "",
                    "quantile": "",
                    "horizon": row.horizon,
                    "value": row.value,
                    "source_file": row.source_file,
                }
            )
        for row in context.itertuples(index=False):
            rows.append(
                {
                    "batch_id": batch_id,
                    "scope": "context",
                    "system": row.system,
                    "factor": row.factor,
                    "return_mode": row.return_mode,
                    "group_dimension": row.group_dimension,
                    "metric": row.metric,
                    "group": row.group,
                    "quantile": row.quantile,
                    "horizon": row.horizon,
                    "value": row.value,
                    "source_file": row.source_file,
                }
            )
    return pd.DataFrame(rows)


def concat_from_batches(batch_root: Path, relative_path: str) -> pd.DataFrame:
    frames = []
    for batch_dir in batch_dirs(batch_root):
        frame = read_csv(batch_dir / relative_path)
        if not frame.empty:
            frame.insert(0, "batch_id", batch_dir.name)
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def mean_ic_view(metric_index: pd.DataFrame) -> pd.DataFrame:
    if metric_index.empty:
        return pd.DataFrame()
    view = metric_index[
        metric_index["scope"].eq("open_source")
        & metric_index["metric"].astype(str).str.contains("mean_information_coefficient", regex=False)
    ].copy()
    if view.empty:
        return view
    view["abs_value"] = pd.to_numeric(view["value"], errors="coerce").abs()
    return view.sort_values(["horizon", "abs_value"], ascending=[True, False])[
        ["system", "factor", "horizon", "metric", "value"]
    ].head(40)


def write_report(batch_root: Path, audit_path: Path, metric_index: pd.DataFrame) -> None:
    manifest = read_csv(batch_root / "batch_manifest.csv")
    summary = read_csv(batch_root / "batch_output_summary.csv")
    evaluator_status = concat_from_batches(batch_root, "evaluator_status.csv")
    context_status = concat_from_batches(batch_root, "context/context_evaluator_status.csv")
    failures = concat_from_batches(batch_root, "factor_failure_reasons.csv")
    audit = read_csv(audit_path)
    batch_counts = manifest.groupby("status").size().reset_index(name="count") if not manifest.empty else pd.DataFrame()
    evaluator_counts = (
        evaluator_status.groupby(["system", "status"]).size().reset_index(name="count")
        if not evaluator_status.empty
        else pd.DataFrame()
    )
    context_counts = (
        context_status.groupby("status").size().reset_index(name="count") if not context_status.empty else pd.DataFrame()
    )
    failure_counts = (
        failures.groupby(["system", "step"]).size().reset_index(name="count") if not failures.empty else pd.DataFrame()
    )
    promotion_counts = (
        audit.groupby("promotable").size().reset_index(name="count") if not audit.empty else pd.DataFrame()
    )
    holdouts = audit[audit["promotable"].astype(str).ne("True")][
        ["factor", "alphalens_status", "qlib_status", "jqfactor_status", "failure_steps", "holdout_reason"]
    ] if not audit.empty else pd.DataFrame()
    lines = [
        "# Alpha158 Remaining138 Evaluation Summary",
        "",
        f"- Output: `{batch_root.as_posix()}`",
        f"- Metric index rows: `{len(metric_index)}`",
        "",
        "## Batch Status",
        "",
        markdown_table(batch_counts),
        "",
        "## Batch Output Summary",
        "",
        markdown_table(summary),
        "",
        "## Evaluator Status",
        "",
        markdown_table(evaluator_counts),
        "",
        "## Context Status",
        "",
        markdown_table(context_counts),
        "",
        "## Promotion Status",
        "",
        markdown_table(promotion_counts),
        "",
        "## Holdouts",
        "",
        markdown_table(holdouts),
        "",
        "## Mean IC Snapshot",
        "",
        markdown_table(mean_ic_view(metric_index)),
        "",
        "## Failure Counts",
        "",
        markdown_table(failure_counts),
        "",
        "## Notes",
        "",
        "- This summary does not create a combined score.",
        "- jqfactor_analyzer partial-pass is expected in the current pandas 2.x environment for known factor-return and alpha/beta steps.",
        "- Alphalens partial-pass factors are held out from the strict runnable catalog until turnover diagnostics are reviewed.",
    ]
    (batch_root / "alpha158_remaining138_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    batch_root = resolve_path(args.batch_root)
    audit_path = resolve_path(args.audit)
    metric_index = build_metric_index(batch_root)
    metric_index.to_csv(batch_root / "alpha158_remaining138_metric_index.csv", index=False, encoding="utf-8-sig")
    write_report(batch_root, audit_path, metric_index)
    print(f"Alpha158 remaining138 summary written to {batch_root}", flush=True)
    return batch_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Alpha158 remaining138 batch outputs.")
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
