import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.evaluator import FactorResearchConfig, load_feature_frame
from factor_research.factor_library import FACTOR_COLUMNS, add_basic_factors
from research_validation.model_entry_gate import assert_model_entry_files


def train_predict_by_date(frame: pd.DataFrame, label: str, train_end: str, test_start: str) -> pd.DataFrame:
    data = frame[["datetime", "instrument", label, *FACTOR_COLUMNS]].replace([np.inf, -np.inf], np.nan).dropna()
    train = data[data["datetime"] <= pd.Timestamp(train_end)]
    test = data[data["datetime"] >= pd.Timestamp(test_start)]

    model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    model.fit(train[FACTOR_COLUMNS], train[label])
    test = test.copy()
    test["score"] = model.predict(test[FACTOR_COLUMNS])
    return test[["datetime", "instrument", label, "score"]]


def score_ic(prediction: pd.DataFrame, label: str) -> tuple[pd.DataFrame, dict]:
    rows = []
    for dt, group in prediction.groupby("datetime", sort=True):
        if len(group) < 2:
            continue
        rows.append(
            {
                "datetime": dt,
                "count": int(len(group)),
                "ic": group["score"].corr(group[label], method="pearson"),
                "rank_ic": group["score"].corr(group[label], method="spearman"),
            }
        )
    ic = pd.DataFrame(rows)
    summary = {
        "ic_mean": float(ic["ic"].mean()),
        "icir": float(ic["ic"].mean() / ic["ic"].std()) if len(ic) > 1 and ic["ic"].std() else np.nan,
        "rank_ic_mean": float(ic["rank_ic"].mean()),
        "rank_icir": float(ic["rank_ic"].mean() / ic["rank_ic"].std())
        if len(ic) > 1 and ic["rank_ic"].std()
        else np.nan,
        "test_dates": int(len(ic)),
        "prediction_rows": int(len(prediction)),
    }
    return ic, summary


def write_report(config, train_end: str, test_start: str, summary: dict, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Linear Factor Model Sanity Check",
        "",
        f"- Provider URI: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Feature range: `{config.start_time}` to `{config.end_time}`",
        f"- Label: `{config.label}`",
        f"- Train end: `{train_end}`",
        f"- Test start: `{test_start}`",
        f"- Model: `StandardScaler + Ridge(alpha=1.0)`",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        if isinstance(value, float):
            lines.append(f"| {key} | `{value:.6f}` |")
        else:
            lines.append(f"| {key} | `{value}` |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run a lightweight Ridge sanity check on basic factor features.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", required=True)
    parser.add_argument("--start-time", default="2010-01-01")
    parser.add_argument("--end-time", default="2020-08-01")
    parser.add_argument("--label", default="label_1d_t1")
    parser.add_argument("--train-end", default="2016-12-31")
    parser.add_argument("--test-start", default="2017-01-01")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--readiness-summary", type=Path, default=Path("outputs/full_research_669_readiness_v1/current/readiness_summary.csv"))
    parser.add_argument("--selection-status", type=Path, default=Path("outputs/full_research_669_readiness_v1/current/selection_status.csv"))
    parser.add_argument("--selection-name", default="split_specific_holdout_clean_allowlists_v1")
    args = parser.parse_args()

    readiness_path = args.readiness_summary if args.readiness_summary.is_absolute() else PROJECT_ROOT / args.readiness_summary
    selection_path = args.selection_status if args.selection_status.is_absolute() else PROJECT_ROOT / args.selection_status
    assert_model_entry_files(readiness_path, selection_path, selection_name=args.selection_name)

    config = FactorResearchConfig(
        provider_uri=args.provider_uri,
        market=args.market,
        start_time=args.start_time,
        end_time=args.end_time,
        label=args.label,
        output_dir=Path(args.output_dir),
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = load_feature_frame(config)
    factors = add_basic_factors(raw)
    prediction = train_predict_by_date(factors, args.label, args.train_end, args.test_start)
    ic, summary = score_ic(prediction, args.label)

    prediction.to_csv(output_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    ic.to_csv(output_dir / "ic_series.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    write_report(config, args.train_end, args.test_start, summary, output_dir / "linear_factor_model_report.md")
    print(f"Wrote linear factor model outputs to {output_dir}")


if __name__ == "__main__":
    main()
