from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.expression_adapter import ExpressionFrameConfig, build_expression_frame  # noqa: E402
from factor_research.report import markdown_table  # noqa: E402


DEFAULT_CONFIG = Path("configs/alpha360_expression_adapter_smoke_v1.yaml")


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: Path) -> ExpressionFrameConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    selection = data.get("selection", {})
    cache = data.get("cache", {})
    return ExpressionFrameConfig(
        provider_uri=str(data["provider_uri"]),
        market=str(data["market"]),
        start=str(data["start"]),
        end=str(data["end"]),
        max_instruments=data.get("max_instruments"),
        catalog_path=resolve_path(data["catalog_path"]),
        inventory_path=resolve_path(data["inventory_path"]),
        output_dir=resolve_path(data["output_dir"]),
        enabled_only=bool(selection.get("enabled_only", False)),
        runnable_only=bool(selection.get("runnable_only", False)),
        stages=tuple(str(item) for item in selection.get("stages", [])),
        names=tuple(str(item) for item in selection.get("names", [])),
        max_factors=selection.get("max_factors"),
        batch_size=(data.get("expression", {}) or {}).get("batch_size"),
        refresh=bool(cache.get("refresh", False)),
    )


def write_report(config: ExpressionFrameConfig, expression_table: pd.DataFrame, summary: pd.DataFrame, output: Path) -> None:
    coverage = summary[["factor", "coverage", "missing_rate", "valid_rows", "total_rows"]].copy()
    lines = [
        "# Alpha360 Expression Frame Smoke V1",
        "",
        f"- Provider: `{config.provider_uri}`",
        f"- Market: `{config.market}`",
        f"- Date range: `{config.start}` to `{config.end}`",
        f"- Max instruments: `{config.max_instruments}`",
        f"- Factor count: `{len(expression_table)}`",
        f"- Catalog: `{config.catalog_path.as_posix()}`",
        f"- Inventory: `{config.inventory_path.as_posix()}`",
        "",
        "## Expression Table",
        "",
        markdown_table(expression_table[["catalog_name", "factor_name", "family", "lag", "category", "expression"]]),
        "",
        "## Coverage",
        "",
        markdown_table(coverage),
        "",
        "## Boundary",
        "",
        "- This is an adapter smoke run only.",
        "- Catalog entries stay disabled/non-runnable until V4 evaluation and promotion pass.",
        "- Downstream evaluation must keep data_quality and tradability as mandatory prefilters.",
        "",
        "## Output Files",
        "",
        "- `factor_frame.pkl`",
        "- `expression_table.csv`",
        "- `expression_frame_summary.csv`",
        "- `expression_frame_sample.csv`",
        "- `expression_frame_manifest.json`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    config = load_config(resolve_path(args.config))
    frame, expression_table, frame_path = build_expression_frame(config)
    summary = pd.read_csv(config.output_dir / "expression_frame_summary.csv")
    write_report(config, expression_table, summary, config.output_dir / "expression_frame_report.md")
    print(f"Alpha360 expression frame written to {frame_path}", flush=True)
    print(f"Rows: {len(frame):,}; factors: {len(expression_table)}", flush=True)
    return config.output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Qlib Alpha360 expression frame smoke V1.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
