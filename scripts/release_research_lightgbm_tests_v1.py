from __future__ import annotations

import shlex
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_research.lightgbm_models import (  # noqa: E402
    load_lightgbm_config,
)
from model_research.lightgbm_test_release import (  # noqa: E402
    release_lightgbm_tests,
)
from model_research.protocol import resolve  # noqa: E402


def main() -> int:
    config = load_lightgbm_config(
        resolve("configs/research_lightgbm_v1.yaml")
    )
    result = release_lightgbm_tests(
        config,
        output_dir=resolve("outputs/research_lightgbm_v1/current"),
        runtime_dir=resolve(
            "outputs/research_lightgbm_v1/runtime/test_predictions"
        ),
        command=" ".join(shlex.quote(value) for value in sys.argv),
    )
    print(
        "LightGBM historical test release passed: "
        f"releases={result['release_count']}; "
        f"prediction_rows={result['prediction_row_count']}; "
        f"minimum_coverage={result['minimum_prediction_coverage']:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
