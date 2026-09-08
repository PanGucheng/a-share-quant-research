"""Build primary evidence before freezing or applying candidate rules."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factor_research.long_history_boards import build_evidence  # noqa: E402
from factor_research.long_history_candidates import build_candidates  # noqa: E402


def build_delivery(run):
    """Attach period sample denominators/units without modifying the sealed snapshot."""
    import pandas as pd
    from factor_research.long_history_boards import verify_seal, seal
    from factor_research.long_history_screening import development_calendar, label_map

    source = run / "primary/evidence_v0"
    receipt = verify_seal(source)
    metrics = pd.read_parquet(source / "factor_period_metrics.parquet")
    samples = pd.read_csv(source / "daily_sample_counts_by_year.csv")
    quality = pd.read_csv(source / "data_quality_by_year.csv")
    groups = [(str(y), [y]) for y in range(2010, 2024)]
    groups += [("full", list(range(2010, 2024))), ("A", list(range(2010, 2015))),
               ("B", list(range(2015, 2018))), ("C", list(range(2018, 2021))),
               ("D", list(range(2021, 2024)))]
    totals, profiles = [], []
    for period, years in groups:
        total = samples.loc[samples.year.isin(years)].groupby("factor")[["ic_samples", "quantile_samples"]].sum().reset_index()
        total["period_id"] = period
        totals.append(total)
        frame = quality.loc[quality.year.isin(years)]
        profile = frame.groupby("factor").agg(
            rows=("rows", "sum"), finite_count=("finite_count", "sum"), missing_count=("missing_count", "sum"),
            infinite_count=("infinite_count", "sum"), first_finite_date=("first_finite_date", "min"),
            last_finite_date=("last_finite_date", "max"), finite_dates=("finite_dates", "sum"),
            observed_dates=("observed_dates", "sum"), constant_dates=("constant_dates", "sum"),
            min_count_variable_dates=("min_count_variable_dates", "sum")).reset_index()
        profile["coverage"] = profile.finite_count / profile.rows
        profile["period_id"] = period
        profile["scope"] = "feature_only_all_development_dates_including_immature_tail"
        profiles.append(profile)
    metrics = metrics.merge(pd.concat(totals), on=["factor", "period_id"], validate="many_to_one")
    quantile = metrics.metric.str.startswith("alphalens_q")
    metrics["valid_samples"] = metrics.ic_samples.where(~quantile, metrics.quantile_samples)
    metrics["sample_count_scope"] = "common_ic_mask"
    metrics.loc[quantile, "sample_count_scope"] = "common_quantile_mask_all_bins_not_per_bin"
    metrics["unit"] = "fractional_overlapping_20d_return"
    metrics.loc[metrics.metric.isin(["alphalens_ic", "jqfactor_ic", "qlib_ic", "qlib_pearson"]), "unit"] = "correlation"
    metrics["value"] = metrics["mean"]
    metrics["value_statistic"] = "mean_of_original_daily_values"
    metrics["direction_mode"] = "raw"
    metrics["run_id"] = run.name
    metrics["universe_id"] = metrics.universe
    metrics["raw_path"] = str(run.relative_to(ROOT) / "chunks/{year}/{factor}")
    if metrics.valid_samples.isna().any() or len(metrics) != 765 * 13 * 19:
        raise ValueError("incomplete factor evidence table")
    out = run / "primary/delivery_v0"
    out.mkdir(parents=True, exist_ok=False)
    metrics.to_parquet(out / "factor_evidence_table.parquet", index=False)
    pd.concat(profiles).to_csv(out / "data_quality_by_period.csv", index=False)
    contract = json.loads((run / "contract.json").read_text(encoding="utf-8"))
    calendar = development_calendar(Path(contract["provider"]) / "calendars/day.txt")
    label_map(calendar).to_parquet(out / "label_date_map.parquet", index=False)
    return seal(out, {"source_evidence_content_id": receipt["content_id"], "stage": "primary_descriptive_delivery",
                      "held_aside_recent_diagnostic_accessed": False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", choices=("evidence", "candidate", "delivery"), default="evidence")
    parser.add_argument("--rules-dir", type=Path)
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_id):
        parser.error("invalid run-id")
    run = ROOT / "outputs/long_history_multi_evaluator_screening_v1" / args.run_id
    if args.stage == "candidate" and args.rules_dir is None:
        parser.error("candidate requires --rules-dir")
    if args.stage == "evidence":
        result = build_evidence(ROOT, run)
    elif args.stage == "candidate":
        result = build_candidates(run, args.rules_dir)
    else:
        result = build_delivery(run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
