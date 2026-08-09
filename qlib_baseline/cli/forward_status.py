from __future__ import annotations

import argparse
import json
from pathlib import Path

from qlib_baseline.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show prospective forward status")
    parser.add_argument("--project-config", type=Path)
    parser.add_argument("--status", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.project_config)
    path = args.status or settings.outputs_dir / "forward/status.json"
    if not path.is_file():
        raise SystemExit(f"forward status does not exist: {path}")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
