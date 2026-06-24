from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.report import markdown_table  # noqa: E402
from scripts.build_alpha158_expression_frame_v1 import load_config, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha158_expression_adapter_v1.yaml")


def load_expression_frame(output_dir: Path) -> pd.DataFrame:
    path = output_dir / "factor_frame.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Missing expression frame: {path}")
    frame = pd.read_pickle(path)
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame


def load_base_fields(provider_uri: str, market: str, start: str, end: str) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=provider_uri, region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    fields = ["$open", "$high", "$low", "$close"]
    data = D.features(D.instruments(market), fields, start_time=start, end_time=end, freq="day")
    frame = data.reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame


def duplicate_check(frame: pd.DataFrame) -> pd.DataFrame:
    duplicates = frame.duplicated(["datetime", "instrument"], keep=False)
    return pd.DataFrame(
        [
            {
                "check": "duplicate_datetime_instrument",
                "status": "pass" if not duplicates.any() else "failed",
                "detail": int(duplicates.sum()),
            }
        ]
    )


def coverage_check(frame: pd.DataFrame, factor_columns: list[str]) -> pd.DataFrame:
    rows = []
    total = len(frame)
    for factor in factor_columns:
        valid = pd.to_numeric(frame[factor], errors="coerce").notna()
        rows.append(
            {
                "factor": factor,
                "valid_rows": int(valid.sum()),
                "total_rows": int(total),
                "coverage": valid.sum() / total if total else 0.0,
                "status": "pass" if valid.any() else "failed",
            }
        )
    return pd.DataFrame(rows)


def manual_formula_check(expression_frame: pd.DataFrame, base_frame: pd.DataFrame) -> pd.DataFrame:
    merged = expression_frame[["datetime", "instrument", "alpha158_KMID", "alpha158_KLEN"]].merge(
        base_frame,
        on=["datetime", "instrument"],
        how="inner",
    )
    rows = []
    checks = {
        "alpha158_KMID": (merged["$close"] - merged["$open"]) / merged["$open"],
        "alpha158_KLEN": (merged["$high"] - merged["$low"]) / merged["$open"],
    }
    for factor, expected in checks.items():
        actual = pd.to_numeric(merged[factor], errors="coerce")
        expected = pd.to_numeric(expected, errors="coerce")
        valid = actual.notna() & expected.notna() & np.isfinite(actual) & np.isfinite(expected)
        diff = (actual.loc[valid] - expected.loc[valid]).abs()
        max_abs_error = float(diff.max()) if not diff.empty else np.nan
        rows.append(
            {
                "check": f"{factor}_manual_formula",
                "matched_rows": int(valid.sum()),
                "max_abs_error": max_abs_error,
                "status": "pass" if valid.any() and max_abs_error <= 1e-10 else "failed",
            }
        )
    return pd.DataFrame(rows)


def missing_window_check(frame: pd.DataFrame, factor_columns: list[str]) -> pd.DataFrame:
    rows = []
    for factor in factor_columns:
        per_date = frame.groupby("datetime")[factor].apply(lambda values: pd.to_numeric(values, errors="coerce").notna().mean())
        first_valid = per_date[per_date.gt(0)].index.min() if per_date.gt(0).any() else pd.NaT
        rows.append(
            {
                "factor": factor,
                "first_valid_date": str(first_valid.date()) if pd.notna(first_valid) else "",
                "min_daily_coverage": float(per_date.min()) if not per_date.empty else 0.0,
                "mean_daily_coverage": float(per_date.mean()) if not per_date.empty else 0.0,
            }
        )
    return pd.DataFrame(rows)


def write_report(
    output_dir: Path,
    duplicate_result: pd.DataFrame,
    coverage: pd.DataFrame,
    manual: pd.DataFrame,
    missing: pd.DataFrame,
) -> None:
    status_rows = pd.concat(
        [
            duplicate_result,
            manual.rename(columns={"check": "check", "status": "status"}).assign(detail=""),
            pd.DataFrame(
                [
                    {
                        "check": "all_selected_factors_have_values",
                        "status": "pass" if coverage["status"].eq("pass").all() else "failed",
                        "detail": int(coverage["status"].ne("pass").sum()),
                    }
                ]
            ),
        ],
        ignore_index=True,
        sort=False,
    )
    lines = [
        "# Alpha158 Expression Frame Validation V1",
        "",
        "## Status",
        "",
        markdown_table(status_rows.fillna("")),
        "",
        "## Coverage",
        "",
        markdown_table(coverage),
        "",
        "## Missing Window Summary",
        "",
        markdown_table(missing),
        "",
        "## Output Files",
        "",
        "- `validation_status.csv`",
        "- `validation_factor_coverage.csv`",
        "- `validation_manual_formula.csv`",
        "- `validation_missing_window.csv`",
    ]
    (output_dir / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    status_rows.to_csv(output_dir / "validation_status.csv", index=False, encoding="utf-8-sig")


def run(args: argparse.Namespace) -> Path:
    config = load_config(resolve_path(args.config))
    output_dir = config.output_dir
    frame = load_expression_frame(output_dir)
    factor_columns = [column for column in frame.columns if column not in {"datetime", "instrument"}]
    duplicate_result = duplicate_check(frame)
    coverage = coverage_check(frame, factor_columns)
    base = load_base_fields(config.provider_uri, config.market, config.start, config.end)
    manual = manual_formula_check(frame, base)
    missing = missing_window_check(frame, factor_columns)

    coverage.to_csv(output_dir / "validation_factor_coverage.csv", index=False, encoding="utf-8-sig")
    manual.to_csv(output_dir / "validation_manual_formula.csv", index=False, encoding="utf-8-sig")
    missing.to_csv(output_dir / "validation_missing_window.csv", index=False, encoding="utf-8-sig")
    write_report(output_dir, duplicate_result, coverage, manual, missing)

    status = pd.read_csv(output_dir / "validation_status.csv")
    failed = status[status["status"].ne("pass")]
    if not failed.empty:
        raise ValueError(f"Alpha158 expression validation failed: {failed.to_dict(orient='records')}")
    print(f"Alpha158 expression frame validation passed: {output_dir}", flush=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Alpha158 expression frame V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
