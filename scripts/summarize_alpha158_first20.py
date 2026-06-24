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


DEFAULT_OUTPUT = Path("outputs/factor_evaluation_v4/alpha158_first20_smoke")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def build_metric_index(output_dir: Path) -> pd.DataFrame:
    open_source = read_csv(output_dir / "open_source_metric_index.csv")
    context = read_csv(output_dir / "context" / "context_metric_index.csv")
    rows = []
    if not open_source.empty:
        for row in open_source.itertuples(index=False):
            rows.append(
                {
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
    if not context.empty:
        for row in context.itertuples(index=False):
            rows.append(
                {
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


def write_report(output_dir: Path, metric_index: pd.DataFrame) -> None:
    evaluator_status = read_csv(output_dir / "evaluator_status.csv")
    context_status = read_csv(output_dir / "context" / "context_evaluator_status.csv")
    failures = read_csv(output_dir / "factor_failure_reasons.csv")
    external_summary = read_csv(output_dir / "external_factor_frame" / "external_factor_frame_summary.csv")
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
    lines = [
        "# Alpha158 First20 Evaluation Summary",
        "",
        f"- Output: `{output_dir.as_posix()}`",
        f"- Metric index rows: `{len(metric_index)}`",
        "",
        "## Evaluator Status",
        "",
        markdown_table(evaluator_counts),
        "",
        "## Context Status",
        "",
        markdown_table(context_counts),
        "",
        "## External Factor Coverage",
        "",
        markdown_table(external_summary),
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
        "- Context metrics remain separated from raw open-source metrics.",
    ]
    (output_dir / "alpha158_first20_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    output_dir = resolve_path(args.output_dir)
    metric_index = build_metric_index(output_dir)
    metric_index.to_csv(output_dir / "alpha158_first20_metric_index.csv", index=False, encoding="utf-8-sig")
    write_report(output_dir, metric_index)
    print(f"Alpha158 first20 summary written to {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Alpha158 first20 V4 outputs.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
