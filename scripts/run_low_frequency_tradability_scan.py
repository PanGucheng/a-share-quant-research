import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.evaluator import FactorResearchConfig
from scripts.run_factor_score_portfolio import parse_weights
from scripts.run_low_frequency_tradability_portfolio import (
    prepare_frame,
    run_low_frequency_portfolio,
    write_outputs,
)


WEIGHT_PRESETS = {
    "low_risk": "std_20:-1,amplitude_20:-1",
    "low_risk_rev": "std_20:-1,amplitude_20:-1,rev_5:0.25",
    "low_risk_momentum_guard": "std_20:-1,amplitude_20:-1,ret_20:-0.25",
}

LABEL_REBALANCE = {
    "label_20d_t1": 20,
    "label_10d_t1": 10,
}


def safe_name(raw: str) -> str:
    return raw.replace(":", "").replace("/", "-").replace(",", "_").replace(" ", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the default low-frequency tradability portfolio scan.")
    parser.add_argument("--provider-uri", default="E:/qlib_prj/qlib_data/cn_data_community_20260609_derived")
    parser.add_argument("--market", default="all_stock_shsz_liquid2000")
    parser.add_argument("--start-time", required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--tradability-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--topk", default="100,200,300")
    parser.add_argument("--cost-bps", default="5,10,20")
    parser.add_argument("--clip", type=float, default=3.0)
    parser.add_argument("--min-liquidity-bucket", type=int, default=3)
    parser.add_argument("--min-tradability-score", type=float, default=75.0)
    parser.add_argument("--min-capacity-multiple", type=float, default=2.0)
    args = parser.parse_args()

    topk_values = [int(value) for value in args.topk.split(",")]
    cost_values = [float(value) for value in args.cost_bps.split(",")]
    output_root = Path(args.output_root)

    for preset_name, preset in WEIGHT_PRESETS.items():
        weights = parse_weights(preset)
        config = FactorResearchConfig(
            provider_uri=args.provider_uri,
            market=args.market,
            start_time=args.start_time,
            end_time=args.end_time,
            label="label_20d_t1",
            output_dir=output_root,
        )
        frame = prepare_frame(config, Path(args.tradability_dir), weights, args.clip)
        for label, rebalance_every in LABEL_REBALANCE.items():
            for topk in topk_values:
                for cost_bps in cost_values:
                    daily, rebalances, positions, summary = run_low_frequency_portfolio(
                        frame,
                        label,
                        topk,
                        rebalance_every,
                        cost_bps,
                        args.min_liquidity_bucket,
                        args.min_tradability_score,
                        args.min_capacity_multiple,
                    )
                    summary.update(
                        {
                            "window_start": args.start_time,
                            "window_end": args.end_time,
                            "weight_preset": preset_name,
                            "score_weights": preset,
                        }
                    )
                    output_dir = output_root / (
                        f"{safe_name(args.start_time)}_{safe_name(args.end_time)}_"
                        f"{label}_reb{rebalance_every}_top{topk}_{preset_name}_cost{cost_bps:g}"
                    )
                    config = FactorResearchConfig(
                        provider_uri=args.provider_uri,
                        market=args.market,
                        start_time=args.start_time,
                        end_time=args.end_time,
                        label=label,
                        output_dir=output_dir,
                    )
                    write_outputs(output_dir, config, weights, daily, rebalances, positions, summary)
                    print(f"Wrote scan item: {output_dir}")


if __name__ == "__main__":
    main()
