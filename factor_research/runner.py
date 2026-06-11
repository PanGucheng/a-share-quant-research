import argparse
from pathlib import Path

from factor_research.evaluator import FactorResearchConfig, run_factor_research


def main():
    parser = argparse.ArgumentParser(description="Run minimal daily cross-sectional factor research.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", default="csi500")
    parser.add_argument("--start-time", default="2017-01-01")
    parser.add_argument("--end-time", default="2020-08-01")
    parser.add_argument("--label", default="label_1d_t1")
    parser.add_argument("--quantiles", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=50)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = run_factor_research(
        FactorResearchConfig(
            provider_uri=args.provider_uri,
            market=args.market,
            start_time=args.start_time,
            end_time=args.end_time,
            label=args.label,
            quantiles=args.quantiles,
            min_count=args.min_count,
            output_dir=Path(args.output_dir),
        )
    )
    print(f"Wrote factor research outputs to {output_dir}")


if __name__ == "__main__":
    main()
