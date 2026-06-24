from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.catalog import FactorCatalogEntry, load_factor_catalog  # noqa: E402


DEFAULT_ALL_CATALOG = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_all.yaml")
DEFAULT_FIRST20_RUNNABLE = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml")
DEFAULT_REMAINING_OUTPUT = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_pending.yaml")
DEFAULT_MIXED_OUTPUT = Path("outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_mixed.yaml")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def entry_mapping(entry: FactorCatalogEntry, *, stage: str | None = None, enabled: bool | None = None, runnable: bool | None = None) -> dict:
    payload = asdict(entry)
    payload["required_fields"] = list(entry.required_fields)
    payload["labels"] = list(entry.labels)
    if stage is not None:
        payload["stage"] = stage
    if enabled is not None:
        payload["enabled"] = enabled
    if runnable is not None:
        payload["runnable"] = runnable
    if payload["stage"].startswith("alpha158_full_"):
        payload["compute_adapter"] = "qlib_expression_frame_v1"
    return payload


def catalog_payload(factors: list[dict], purpose: str, source_catalogs: list[Path]) -> dict:
    return {
        "version": 1,
        "updated": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "policy": {
            "purpose": purpose,
            "principle": [
                "First20 results are reused instead of rerunning completed evaluation batches.",
                "Remaining Alpha158 entries stay non-runnable until expression validation and V4 batch evaluation pass.",
                "Metric definitions remain in the external evaluator outputs.",
            ],
            "source_catalogs": [path.as_posix() for path in source_catalogs],
        },
        "factors": factors,
    }


def run(args: argparse.Namespace) -> tuple[Path, Path]:
    all_catalog = resolve_path(args.all_catalog)
    first20_catalog = resolve_path(args.first20_runnable)
    remaining_output = resolve_path(args.remaining_output)
    mixed_output = resolve_path(args.mixed_output)
    all_entries = load_factor_catalog(all_catalog)
    first20_entries = load_factor_catalog(first20_catalog)
    first20_names = {entry.name for entry in first20_entries}
    remaining_entries = [entry for entry in all_entries if entry.name not in first20_names]
    remaining_factors = [
        entry_mapping(entry, stage=args.remaining_stage, enabled=False, runnable=False) for entry in remaining_entries
    ]
    mixed_factors = [entry_mapping(entry) for entry in first20_entries] + remaining_factors
    remaining_output.parent.mkdir(parents=True, exist_ok=True)
    remaining_output.write_text(
        yaml.safe_dump(
            catalog_payload(
                remaining_factors,
                "Pending catalog for Alpha158 entries not covered by the first20 smoke.",
                [all_catalog, first20_catalog],
            ),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    mixed_output.write_text(
        yaml.safe_dump(
            catalog_payload(
                mixed_factors,
                "Mixed Alpha158 catalog: first20 runnable entries plus remaining pending entries.",
                [all_catalog, first20_catalog],
            ),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    print(f"Remaining Alpha158 entries: {len(remaining_factors)} -> {remaining_output}", flush=True)
    print(f"Mixed Alpha158 entries: {len(mixed_factors)} -> {mixed_output}", flush=True)
    return remaining_output, mixed_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Alpha158 full-stage catalogs.")
    parser.add_argument("--all-catalog", type=Path, default=DEFAULT_ALL_CATALOG)
    parser.add_argument("--first20-runnable", type=Path, default=DEFAULT_FIRST20_RUNNABLE)
    parser.add_argument("--remaining-output", type=Path, default=DEFAULT_REMAINING_OUTPUT)
    parser.add_argument("--mixed-output", type=Path, default=DEFAULT_MIXED_OUTPUT)
    parser.add_argument("--remaining-stage", default="alpha158_full_remaining_pending")
    return parser


def main() -> None:
    freeze_support()
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
