from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import (  # noqa: E402
    Alpha101SourceConfig,
    run_alpha101_adapter_smoke,
)


DEFAULT_CONFIG = Path("configs/alpha101_factor_adapter_smoke_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> Alpha101SourceConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source = data.get("source", {})
    alpha101 = data.get("alpha101", {})
    catalog = data.get("catalog", {})
    cache = data.get("cache", {})
    return Alpha101SourceConfig(
        provider_uri=str(data["provider_uri"]),
        market=str(data["market"]),
        start=str(data["start"]),
        end=str(data["end"]),
        max_instruments=data.get("max_instruments"),
        source_local_path=resolve_path(source["local_path"]),
        source_commit=str(source["source_commit"]),
        source_file=str(source["source_file"]),
        source_module=str(source["source_module"]),
        license=str(source["license"]),
        selected_smoke_factors=tuple(str(item) for item in alpha101.get("selected_smoke_factors", [])),
        metadata_catalog=resolve_path(alpha101["metadata_catalog"]),
        catalog_stage=str(catalog.get("stage", "alpha101_adapter_smoke_generated")),
        catalog_enabled=bool(catalog.get("enabled", False)),
        catalog_runnable=bool(catalog.get("runnable", False)),
        labels=tuple(str(item) for item in catalog.get("labels", [])),
        output_dir=resolve_path(data.get("output_dir", "outputs/alpha101_factor_adapter_v1/smoke")),
        refresh=bool(cache.get("refresh", False)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a KunQuant Alpha101 factor source adapter smoke frame.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(resolve_path(build_parser().parse_args().config))
    outputs = run_alpha101_adapter_smoke(config)
    print(f"Alpha101 adapter smoke outputs written to {outputs['output_dir']}", flush=True)


if __name__ == "__main__":
    main()
