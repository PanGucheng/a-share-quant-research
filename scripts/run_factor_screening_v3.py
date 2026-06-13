from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.registry import enabled_specs
from factor_research.screening_v3 import ScreeningRules, build_candidate_board, load_screening_inputs, write_screening_report


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a factor candidate board from factor research V3 outputs.")
    parser.add_argument("--input-dir", type=Path, default=Path("outputs/factor_research_v3/liquid2000_core"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_screening_v3/liquid2000_core"))
    parser.add_argument("--label", default="label_20d_t1")
    parser.add_argument("--portfolio-min-rank-ic", type=float, default=0.03)
    parser.add_argument("--research-min-rank-ic", type=float, default=0.015)
    parser.add_argument("--min-oos-rank-ic", type=float, default=0.005)
    parser.add_argument("--min-residual-retention", type=float, default=0.25)
    parser.add_argument("--exposure-corr-threshold", type=float, default=0.80)
    parser.add_argument("--redundancy-corr-threshold", type=float, default=0.85)
    return parser


def run(args: argparse.Namespace) -> Path:
    input_dir = resolve_path(args.input_dir)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rules = ScreeningRules(
        research_min_rank_ic=args.research_min_rank_ic,
        portfolio_min_rank_ic=args.portfolio_min_rank_ic,
        min_oos_rank_ic=args.min_oos_rank_ic,
        min_residual_retention=args.min_residual_retention,
        exposure_corr_threshold=args.exposure_corr_threshold,
        redundancy_corr_threshold=args.redundancy_corr_threshold,
    )
    inputs = load_screening_inputs(input_dir)
    board = build_candidate_board(inputs, enabled_specs([args.label]), rules)
    board.to_csv(output_dir / "factor_candidate_board.csv", index=False, encoding="utf-8-sig")
    write_screening_report(board, output_dir / "factor_screening_report.md", input_dir, rules)
    print(f"Factor screening V3.3 outputs written to {output_dir}", flush=True)
    return output_dir


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
