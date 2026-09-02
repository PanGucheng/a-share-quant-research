from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_research.protocol import PROJECT_ROOT
from model_research.thread_determinism import run_thread_determinism_audit


def _resolve(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit real LightGBM workloads across thread counts"
    )
    parser.add_argument(
        "--config", default="configs/lightgbm_thread_determinism_audit_v1.yaml"
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--cache-root", default="tmp/thread_determinism_audit/projection_spool_cache"
    )
    parser.add_argument(
        "--runtime-root", default="tmp/thread_determinism_audit/runtime"
    )
    args = parser.parse_args()
    summary = run_thread_determinism_audit(
        config_path=_resolve(args.config),
        output_dir=_resolve(args.output_dir),
        cache_root=_resolve(args.cache_root),
        runtime_root=_resolve(args.runtime_root),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
