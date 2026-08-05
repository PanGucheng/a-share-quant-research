from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Show prospective forward status")
    parser.add_argument("--status", default="outputs/forward/status.json")
    args = parser.parse_args()
    path = Path(args.status)
    if not path.is_file():
        raise SystemExit(f"forward status does not exist: {path}")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()
