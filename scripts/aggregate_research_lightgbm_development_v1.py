from __future__ import annotations

import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.lightgbm_aggregate import (  # noqa: E402
    aggregate_lightgbm_development,
)
from model_research.lightgbm_models import (  # noqa: E402
    load_lightgbm_config,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    config = load_lightgbm_config(
        resolve("configs/research_lightgbm_v1.yaml")
    )
    result = aggregate_lightgbm_development(
        config,
        output_dir=resolve(
            "outputs/research_lightgbm_v1/development"
        ),
        command=" ".join(shlex.quote(value) for value in sys.argv),
    )
    print(
        "LightGBM development aggregate passed: "
        f"models={result['model_count']}; "
        f"freezes={result['freeze_count']}; "
        f"test_reads={result['test_read_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
