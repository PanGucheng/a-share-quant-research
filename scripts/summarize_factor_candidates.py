from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("outputs/factor_research_v2/liquid2000_default")
DEFAULT_OUTPUT_CSV = Path("outputs/reports/factor_candidate_pool.csv")
DEFAULT_OUTPUT_MD = Path("outputs/reports/factor_candidate_pool.md")


def resolve_path(path: Path) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return path if path.is_absolute() else project_root / path


def load_decision_file(input_dir: Path) -> pd.DataFrame:
    path = input_dir / "factor_candidate_decision.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing candidate decision file: {path}")
    frame = pd.read_csv(path)
    frame.insert(0, "run_name", input_dir.name)
    return frame


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.6f}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in display.values.tolist())
    return "\n".join(lines)


def existing_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def write_markdown(pool: pd.DataFrame, output: Path) -> None:
    counts = pool.groupby(["run_name", "label", "decision"]).size().reset_index(name="count")
    promoted = pool[pool["decision"] == "promote"].sort_values(
        ["label", "main_directional_rank_ic"], ascending=[True, False]
    )
    watch = pool[pool["decision"] == "watch"].sort_values(
        ["label", "main_directional_rank_ic"], ascending=[True, False]
    )
    rejected = pool[pool["decision"] == "reject"].sort_values(
        ["label", "main_directional_rank_ic"], ascending=[True, False]
    )

    lines = [
        "# Factor Candidate Pool",
        "",
        "This file summarizes the current factor candidates produced by factor research V2.",
        "",
        "## Decision Counts",
        "",
        markdown_table(counts),
        "",
        "## Promote",
        "",
        markdown_table(
            promoted[existing_columns(
                promoted,
                [
                    "run_name",
                    "label",
                    "factor",
                    "category",
                    "expected_direction",
                    "main_directional_rank_ic",
                    "main_ic_win_rate",
                    "oos_directional_rank_ic",
                    "mean_top_quantile_turnover",
                    "stability_score",
                    "monotonicity_score",
                    "directional_spread",
                    "reason",
                ],
            )]
            if not promoted.empty
            else pd.DataFrame()
        ),
        "",
        "## Watch",
        "",
        markdown_table(
            watch[existing_columns(
                watch,
                [
                    "run_name",
                    "label",
                    "factor",
                    "category",
                    "expected_direction",
                    "main_directional_rank_ic",
                    "main_ic_win_rate",
                    "oos_directional_rank_ic",
                    "mean_top_quantile_turnover",
                    "reason",
                ],
            )].head(40)
            if not watch.empty
            else pd.DataFrame()
        ),
        "",
        "## Reject",
        "",
        markdown_table(
            rejected[existing_columns(
                rejected,
                [
                    "run_name",
                    "label",
                    "factor",
                    "category",
                    "expected_direction",
                    "main_directional_rank_ic",
                    "main_ic_win_rate",
                    "oos_directional_rank_ic",
                    "mean_top_quantile_turnover",
                    "reason",
                    "redundancy_group",
                ],
            )].head(40)
            if not rejected.empty
            else pd.DataFrame()
        ),
        "",
        "## How To Use",
        "",
        "- Treat `promote` as a research-pool signal, not a live-trading signal.",
        "- Add new candidate factors to the registry and rerun V2 before touching model or portfolio logic.",
        "- Use `watch` rows to decide whether a factor needs a direction hypothesis, neutralization, or decomposition.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    input_dirs = [resolve_path(path) for path in (args.input_dir or [DEFAULT_INPUT])]
    pool = pd.concat([load_decision_file(path) for path in input_dirs], ignore_index=True)
    output_csv = resolve_path(args.output_csv)
    output_md = resolve_path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(output_csv, index=False, encoding="utf-8-sig")
    write_markdown(pool, output_md)
    print(f"Candidate pool written to {output_csv}")
    print(f"Candidate report written to {output_md}")
    return output_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize factor research V2 candidate decisions.")
    parser.add_argument("--input-dir", type=Path, action="append", default=None)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser


if __name__ == "__main__":
    run(build_parser().parse_args())
