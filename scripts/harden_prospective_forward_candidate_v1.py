from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.forward_hardening import harden_forward_candidate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harden prospective boundaries and durably rebind candidate."
    )
    parser.add_argument(
        "--config",
        default="configs/prospective_forward_confirmation_v1.yaml",
    )
    args = parser.parse_args()
    command = (
        "python scripts/harden_prospective_forward_candidate_v1.py "
        f"--config {args.config}"
    )
    print(
        json.dumps(
            harden_forward_candidate(args.config, command=command),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
