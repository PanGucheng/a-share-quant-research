import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_factor_score_portfolio import markdown_table


DEFAULT_SLICES = {
    "historical_reference_2010_2016": ("2010-01-01", "2016-12-31"),
    "baseline_alignment_2017_2020": ("2017-01-01", "2020-08-01"),
    "main_research_2021_2023": ("2021-01-01", "2023-12-29"),
    "recent_oos_2024_2026": ("2024-01-01", "2026-06-09"),
}

SUMMARY_COLUMNS = [
    "slice",
    "start_time",
    "end_time",
    "market",
    "label",
    "factor",
    "category",
    "expected_direction",
    "coverage",
    "mean_rank_ic",
    "directional_mean_rank_ic",
    "rank_icir",
    "mean_ic",
    "icir",
    "valid_rows",
]


def slice_output_dir(root: Path, market: str, label: str, slice_name: str) -> Path:
    return root / f"{market}_{label}_{slice_name}"


def run_slice(
    python_exe: str,
    provider_uri: str,
    market: str,
    label: str,
    slice_name: str,
    start_time: str,
    end_time: str,
    output_root: Path,
):
    output_dir = slice_output_dir(output_root, market, label, slice_name)
    if (output_dir / "factor_summary.csv").exists():
        return
    cmd = [
        python_exe,
        "-m",
        "factor_research.runner",
        "--provider-uri",
        provider_uri,
        "--market",
        market,
        "--label",
        label,
        "--start-time",
        start_time,
        "--end-time",
        end_time,
        "--output-dir",
        str(output_dir),
    ]
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def load_slice_summary(output_root: Path, market: str, label: str) -> pd.DataFrame:
    frames = []
    for slice_name, (start_time, end_time) in DEFAULT_SLICES.items():
        path = slice_output_dir(output_root, market, label, slice_name) / "factor_summary.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        frame.insert(0, "label", label)
        frame.insert(0, "market", market)
        frame.insert(0, "end_time", end_time)
        frame.insert(0, "start_time", start_time)
        frame.insert(0, "slice", slice_name)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SUMMARY_COLUMNS)


def factor_stability(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor, group in frame.groupby("factor", sort=True):
        directional = group["directional_mean_rank_ic"].dropna()
        rank_ic = group["mean_rank_ic"].dropna()
        rows.append(
            {
                "factor": factor,
                "category": group["category"].iloc[0],
                "expected_direction": group["expected_direction"].iloc[0],
                "slice_count": int(len(group)),
                "positive_directional_slices": int((directional > 0).sum()),
                "mean_directional_rank_ic": directional.mean() if not directional.empty else pd.NA,
                "min_directional_rank_ic": directional.min() if not directional.empty else pd.NA,
                "mean_abs_rank_ic": rank_ic.abs().mean() if not rank_ic.empty else pd.NA,
                "latest_rank_ic": group.loc[group["slice"] == "recent_oos_2024_2026", "mean_rank_ic"].mean(),
                "latest_directional_rank_ic": group.loc[
                    group["slice"] == "recent_oos_2024_2026", "directional_mean_rank_ic"
                ].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["positive_directional_slices", "mean_directional_rank_ic"], ascending=[False, False]
    )


def write_report(frame: pd.DataFrame, stability: pd.DataFrame, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    display = frame[
        [
            "slice",
            "factor",
            "category",
            "expected_direction",
            "coverage",
            "mean_rank_ic",
            "directional_mean_rank_ic",
            "rank_icir",
        ]
    ].sort_values(["slice", "directional_mean_rank_ic"], ascending=[True, False])
    lines = [
        "# Factor Time Slice Stability",
        "",
        "## Stability Summary",
        "",
        markdown_table(stability),
        "",
        "## Slice Details",
        "",
        markdown_table(display),
        "",
        "## Interpretation Guide",
        "",
        "- `2010-2016` is historical reference, not the main training target.",
        "- `2017-2020` is baseline alignment for earlier Qlib-style experiments.",
        "- `2021-2023` should become the main research window.",
        "- `2024-2026` is recent out-of-sample and should be touched lightly to avoid overfitting.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run and summarize factor research over fixed time slices.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", default="all_stock_shsz_liquid2000")
    parser.add_argument("--label", default="label_1d_t1")
    parser.add_argument("--python-exe", default="E:/anaconda_envs/qlib_env/python.exe")
    parser.add_argument("--output-root", default="outputs/factor_time_slices")
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--stability-csv", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if not args.skip_run:
        for slice_name, (start_time, end_time) in DEFAULT_SLICES.items():
            run_slice(
                args.python_exe,
                args.provider_uri,
                args.market,
                args.label,
                slice_name,
                start_time,
                end_time,
                output_root,
            )

    summary = load_slice_summary(output_root, args.market, args.label)
    stability = factor_stability(summary)

    summary_path = Path(args.summary_csv)
    stability_path = Path(args.stability_csv)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    stability_path.parent.mkdir(parents=True, exist_ok=True)
    summary[SUMMARY_COLUMNS].to_csv(summary_path, index=False, encoding="utf-8-sig")
    stability.to_csv(stability_path, index=False, encoding="utf-8-sig")
    write_report(summary, stability, Path(args.report_md))
    print(f"Wrote factor time-slice report to {args.report_md}")


if __name__ == "__main__":
    main()
