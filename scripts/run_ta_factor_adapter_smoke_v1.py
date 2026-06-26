from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.ta_source import TaSourceConfig, run_ta_adapter_smoke  # noqa: E402


DEFAULT_CONFIG = Path("configs/ta_factor_adapter_smoke_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> TaSourceConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    source = data.get("source", {})
    ta = data.get("ta", {})
    catalog = data.get("catalog", {})
    cache = data.get("cache", {})
    return TaSourceConfig(
        provider_uri=str(data["provider_uri"]),
        market=str(data["market"]),
        start=str(data["start"]),
        end=str(data["end"]),
        max_instruments=data.get("max_instruments"),
        source_local_path=resolve_path(source["local_path"]),
        source_commit=str(source["source_commit"]),
        source_file=str(source["source_file"]),
        source_function=str(source["source_function"]),
        license=str(source["license"]),
        colprefix=str(ta.get("colprefix", "ta_")),
        fillna=bool(ta.get("fillna", False)),
        vectorized=bool(ta.get("vectorized", False)),
        exclude_prefixes=tuple(str(item) for item in ta.get("exclude_prefixes", [])),
        selected_smoke_factors=tuple(str(item) for item in ta.get("selected_smoke_factors", [])),
        catalog_stage=str(catalog.get("stage", "ta_adapter_smoke_generated")),
        catalog_enabled=bool(catalog.get("enabled", False)),
        catalog_runnable=bool(catalog.get("runnable", False)),
        labels=tuple(str(item) for item in catalog.get("labels", [])),
        output_dir=resolve_path(data.get("output_dir", "outputs/ta_factor_adapter_v1/smoke")),
        refresh=bool(cache.get("refresh", False)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a TA factor source adapter smoke frame.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    config = load_config(resolve_path(build_parser().parse_args().config))
    outputs = run_ta_adapter_smoke(config)
    print(f"TA adapter smoke outputs written to {outputs['output_dir']}", flush=True)


if __name__ == "__main__":
    main()
