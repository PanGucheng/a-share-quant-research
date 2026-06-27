from __future__ import annotations

import importlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from factor_research.qlib_alpha158 import collect_provider_fields, extract_required_fields, qlib_source_commit


ALPHA360_SOURCE_FILE = "qlib/contrib/data/loader.py"
ALPHA360_SOURCE_FUNCTION = "Alpha360DL.get_feature_config"
ALPHA360_FIELD_ORDER = ("CLOSE", "OPEN", "HIGH", "LOW", "VWAP", "VOLUME")
ALPHA360_NAME_RE = re.compile(r"^(CLOSE|OPEN|HIGH|LOW|VWAP|VOLUME)(\d+)$")


@dataclass(frozen=True)
class Alpha360Formula:
    name: str
    expression: str
    family: str
    lag: int
    category: str
    required_fields: tuple[str, ...]


def load_alpha360_feature_config(qlib_source: Path) -> tuple[list[str], list[str]]:
    source = str(qlib_source)
    if source not in sys.path:
        sys.path.insert(0, source)
    module = importlib.import_module("qlib.contrib.data.loader")
    fields, names = module.Alpha360DL.get_feature_config()
    if len(fields) != len(names):
        raise ValueError(f"Alpha360 fields/names length mismatch: {len(fields)} != {len(names)}")
    return list(fields), list(names)


def infer_alpha360_metadata(name: str) -> tuple[str, int, str]:
    match = ALPHA360_NAME_RE.fullmatch(name)
    if not match:
        return "UNKNOWN", -1, "alpha360_other"
    family = match.group(1)
    lag = int(match.group(2))
    return family, lag, f"alpha360_{family.lower()}_window"


def build_alpha360_formulas(qlib_source: Path) -> list[Alpha360Formula]:
    fields, names = load_alpha360_feature_config(qlib_source)
    formulas: list[Alpha360Formula] = []
    for expression, name in zip(fields, names):
        family, lag, category = infer_alpha360_metadata(name)
        formulas.append(
            Alpha360Formula(
                name=name,
                expression=expression,
                family=family,
                lag=lag,
                category=category,
                required_fields=extract_required_fields(expression),
            )
        )
    return formulas


def build_formula_inventory(
    formulas: list[Alpha360Formula],
    provider_fields: pd.DataFrame,
    qlib_source: Path,
    source_commit: str,
) -> pd.DataFrame:
    available_fields = {f"${field}" for field in provider_fields["field"].tolist()} if not provider_fields.empty else set()
    rows = []
    for formula in formulas:
        required = set(formula.required_fields)
        missing = sorted(required - available_fields)
        rows.append(
            {
                "factor_name": formula.name,
                "catalog_name": f"alpha360_{formula.name}",
                "family": formula.family,
                "lag": formula.lag,
                "category": formula.category,
                "expression": formula.expression,
                "required_fields": ",".join(formula.required_fields),
                "missing_fields": ",".join(missing),
                "field_status": "available" if not missing else "missing",
                "source_project": "qlib_alpha360",
                "source_file": ALPHA360_SOURCE_FILE,
                "source_function": ALPHA360_SOURCE_FUNCTION,
                "source_commit": source_commit,
                "source_path": (qlib_source / ALPHA360_SOURCE_FILE).as_posix(),
            }
        )
    return pd.DataFrame(rows)


def select_smoke_inventory(
    inventory: pd.DataFrame,
    *,
    smoke_fields: tuple[str, ...],
    smoke_lags: tuple[int, ...],
) -> pd.DataFrame:
    desired_names = [f"alpha360_{family.upper()}{int(lag)}" for family in smoke_fields for lag in smoke_lags]
    desired_order = {name: index for index, name in enumerate(desired_names)}
    selected = inventory[
        inventory["catalog_name"].isin(desired_names) & inventory["field_status"].eq("available")
    ].copy()
    selected["smoke_order"] = selected["catalog_name"].map(desired_order)
    return selected.sort_values("smoke_order").drop(columns=["smoke_order"]).reset_index(drop=True)


def alpha360_catalog_payload(inventory: pd.DataFrame, *, enabled: bool, runnable: bool, stage: str) -> dict:
    factors = []
    for row in inventory.itertuples(index=False):
        factors.append(
            {
                "name": row.catalog_name,
                "registry_name": row.catalog_name,
                "category": row.category,
                "source_project": row.source_project,
                "source_file": row.source_file,
                "source_function": row.source_function,
                "source_commit": row.source_commit,
                "license": "MIT",
                "expected_direction": "watch",
                "required_fields": [field for field in str(row.required_fields).split(",") if field],
                "labels": ["label_10d_t1", "label_20d_t1"],
                "stage": stage,
                "enabled": enabled,
                "runnable": runnable,
                "compute_adapter": "qlib_expression_adapter_pending",
                "notes": f"Qlib Alpha360 expression: {row.expression}",
            }
        )
    return {
        "version": 1,
        "updated": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "policy": {
            "purpose": "Generated Qlib Alpha360 catalog supplement.",
            "principle": [
                "Expressions are copied from the local Qlib source via Alpha360DL.get_feature_config.",
                "Entries are not runnable until the Qlib expression adapter and V4 evaluation pass.",
                "Use data_quality and tradability filters before evaluation.",
            ],
            "required_prefilter": ["data_quality", "tradability"],
        },
        "factors": factors,
    }


__all__ = [
    "ALPHA360_FIELD_ORDER",
    "ALPHA360_SOURCE_FILE",
    "ALPHA360_SOURCE_FUNCTION",
    "Alpha360Formula",
    "alpha360_catalog_payload",
    "build_alpha360_formulas",
    "build_formula_inventory",
    "collect_provider_fields",
    "qlib_source_commit",
    "select_smoke_inventory",
]
