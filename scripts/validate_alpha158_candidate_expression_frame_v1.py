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
from scripts.build_alpha158_expression_frame_v1 import load_config, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha158_expression_adapter_candidates_recent_oos_v1.yaml")
DEFAULT_CANDIDATE_POOL = Path("outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv")


def load_candidates(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing candidate pool: {path}")
    frame = pd.read_csv(path)
    required = ["factor", "role"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"candidate pool missing required columns: {missing}")
    alpha = frame[frame["role"].eq("alpha_candidate")].copy()
    if alpha.empty:
        raise ValueError("candidate pool has no alpha_candidate rows")
    return alpha["factor"].astype(str).tolist()


def load_expression_frame(output_dir: Path) -> pd.DataFrame:
    path = output_dir / "factor_frame.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Missing expression frame: {path}")
    frame = pd.read_pickle(path)
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame


def coverage_table(frame: pd.DataFrame, factors: list[str]) -> pd.DataFrame:
    total = len(frame)
    rows = []
    for factor in factors:
        numeric = pd.to_numeric(frame[factor], errors="coerce")
        valid = numeric.notna()
        rows.append(
            {
                "factor": factor,
                "valid_rows": int(valid.sum()),
                "total_rows": int(total),
                "coverage": float(valid.sum() / total) if total else 0.0,
                "missing_rate": float(1 - valid.sum() / total) if total else 1.0,
                "first_valid_date": str(frame.loc[valid, "datetime"].min().date()) if valid.any() else "",
                "last_valid_date": str(frame.loc[valid, "datetime"].max().date()) if valid.any() else "",
            }
        )
    return pd.DataFrame(rows)


def validation_status(
    frame: pd.DataFrame,
    candidates: list[str],
    coverage: pd.DataFrame,
    start: str,
    end: str,
    min_coverage: float,
) -> pd.DataFrame:
    factor_columns = [column for column in frame.columns if column not in {"datetime", "instrument"}]
    duplicates = frame.duplicated(["datetime", "instrument"], keep=False)
    missing_candidates = sorted(set(candidates) - set(factor_columns))
    unexpected_factors = sorted(set(factor_columns) - set(candidates))
    date_min = frame["datetime"].min()
    date_max = frame["datetime"].max()
    rows = [
        {
            "check": "factor_count_matches_candidates",
            "status": "pass" if len(factor_columns) == len(candidates) else "failed",
            "detail": f"factor_columns={len(factor_columns)}, candidates={len(candidates)}",
        },
        {
            "check": "all_candidates_present",
            "status": "pass" if not missing_candidates else "failed",
            "detail": ",".join(missing_candidates),
        },
        {
            "check": "no_unexpected_factors",
            "status": "pass" if not unexpected_factors else "failed",
            "detail": ",".join(unexpected_factors),
        },
        {
            "check": "duplicate_datetime_instrument",
            "status": "pass" if not duplicates.any() else "failed",
            "detail": int(duplicates.sum()),
        },
        {
            "check": "date_range_non_empty",
            "status": "pass" if pd.notna(date_min) and pd.notna(date_max) else "failed",
            "detail": f"{date_min} to {date_max}",
        },
        {
            "check": "date_range_inside_config",
            "status": "pass"
            if pd.notna(date_min)
            and pd.notna(date_max)
            and date_min >= pd.Timestamp(start)
            and date_max <= pd.Timestamp(end)
            else "failed",
            "detail": f"{date_min} to {date_max}; config={start} to {end}",
        },
        {
            "check": "min_factor_coverage",
            "status": "pass" if coverage["coverage"].ge(min_coverage).all() else "failed",
            "detail": float(coverage["coverage"].min()) if not coverage.empty else 0.0,
        },
    ]
    return pd.DataFrame(rows)


def write_report(output_dir: Path, status: pd.DataFrame, coverage: pd.DataFrame, min_coverage: float) -> None:
    lines = [
        "# Alpha158 Candidate Expression Frame Validation V1",
        "",
        f"- Minimum coverage threshold: `{min_coverage}`",
        "",
        "## Status",
        "",
        markdown_table(status),
        "",
        "## Coverage",
        "",
        markdown_table(coverage),
        "",
        "## Output Files",
        "",
        "- `candidate_expression_validation_status.csv`",
        "- `candidate_expression_validation_coverage.csv`",
        "- `candidate_expression_validation_report.md`",
    ]
    (output_dir / "candidate_expression_validation_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> Path:
    config = load_config(resolve_path(args.config))
    candidates = load_candidates(resolve_path(args.candidate_pool))
    frame = load_expression_frame(config.output_dir)
    missing = [factor for factor in candidates if factor not in frame.columns]
    if missing:
        raise ValueError(f"expression frame missing candidates: {missing}")
    coverage = coverage_table(frame, candidates)
    status = validation_status(frame, candidates, coverage, config.start, config.end, args.min_coverage)
    coverage.to_csv(config.output_dir / "candidate_expression_validation_coverage.csv", index=False, encoding="utf-8-sig")
    status.to_csv(config.output_dir / "candidate_expression_validation_status.csv", index=False, encoding="utf-8-sig")
    write_report(config.output_dir, status, coverage, args.min_coverage)
    failed = status[status["status"].ne("pass")]
    if not failed.empty:
        raise ValueError(f"candidate expression validation failed: {failed.to_dict(orient='records')}")
    print(f"Alpha158 candidate expression validation passed: {config.output_dir}", flush=True)
    print(f"Rows: {len(frame):,}; candidates: {len(candidates)}", flush=True)
    return config.output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate candidate-only Alpha158 expression frame.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--candidate-pool", type=Path, default=DEFAULT_CANDIDATE_POOL)
    parser.add_argument("--min-coverage", type=float, default=0.99)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
