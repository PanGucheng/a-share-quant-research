from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from model_research.full_execution import qualified_full_execution_profile
from model_research.lightgbm_models import run_lightgbm_development
from model_research.protocol import PROJECT_ROOT


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Full LightGBM with an exact-qualified MT execution profile"
    )
    parser.add_argument(
        "--profile", default="configs/research_lightgbm_full_exact_mt_v2.yaml"
    )
    parser.add_argument("--splits", nargs="+", default=["split_001"])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runtime-dir", required=True)
    args = parser.parse_args()
    config, summary = qualified_full_execution_profile(_resolve(args.profile))
    result = run_lightgbm_development(
        config,
        output_dir=_resolve(args.output_dir),
        runtime_dir=_resolve(args.runtime_dir),
        split_ids=[str(value) for value in args.splits],
        command=" ".join(shlex.quote(value) for value in sys.argv),
    )
    print(
        "Exact-qualified Full MT passed: "
        f"threads={config['determinism']['num_threads']}; "
        f"splits={','.join(result['split_ids'])}; "
        f"qualification={summary['summary_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
