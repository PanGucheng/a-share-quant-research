from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.candidate_pool_v3 import (
    CandidatePoolMetadata,
    build_candidate_pool,
    load_candidate_board,
    write_pool_outputs,
)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a versioned factor candidate pool from screening outputs.")
    parser.add_argument(
        "--candidate-board",
        type=Path,
        default=Path("outputs/factor_screening_v3/liquid2000_core/factor_candidate_board.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/factor_candidate_pool_v3/liquid2000_core"))
    parser.add_argument("--pool-name", default="liquid2000_core_v3_4")
    parser.add_argument("--label", default="label_20d_t1")
    return parser


def run(args: argparse.Namespace) -> Path:
    board_path = resolve_path(args.candidate_board)
    output_dir = resolve_path(args.output_dir)
    metadata = CandidatePoolMetadata(
        pool_name=args.pool_name,
        source_board=str(board_path),
        label=args.label,
    )
    board = load_candidate_board(board_path)
    pool = build_candidate_pool(board, metadata)
    write_pool_outputs(pool, metadata, output_dir)
    print(f"Factor candidate pool V3 outputs written to {output_dir}", flush=True)
    return output_dir


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
