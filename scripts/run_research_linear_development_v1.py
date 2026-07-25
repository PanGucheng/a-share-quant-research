from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.linear_models import (  # noqa: E402
    load_linear_config,
    run_linear_development,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run staged Ridge/Elastic Net development without test reads."
    )
    parser.add_argument(
        "--config",
        default="configs/research_linear_models_v1.yaml",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--splits", nargs="+", required=True)
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["ridge", "elastic_net"],
        required=True,
    )
    parser.add_argument("--factor-limit", type=int)
    parser.add_argument("--train-date-limit", type=int)
    parser.add_argument("--validation-date-limit", type=int)
    parser.add_argument("--candidate-limit", type=int)
    parser.add_argument("--full-scope", action="store_true")
    args = parser.parse_args()
    config = load_linear_config(resolve(args.config))
    result = run_linear_development(
        config,
        output_dir=resolve(args.output_dir),
        runtime_dir=resolve(args.runtime_dir),
        split_ids=args.splits,
        methods=args.methods,
        factor_limit=args.factor_limit,
        train_date_limit=args.train_date_limit,
        validation_date_limit=args.validation_date_limit,
        candidate_limit=args.candidate_limit,
        full_scope=args.full_scope,
        command=" ".join(shlex.quote(value) for value in sys.argv),
    )
    print(
        "Linear development passed: "
        f"candidate_fits={result['candidate_fit_count']}; "
        f"final_refits={result['final_refit_count']}; "
        f"freezes={result['freeze_count']}; "
        f"test_reads={result['test_read_count']}; "
        f"peak_rss_mb={result['peak_rss_mb']:.1f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
