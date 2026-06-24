from __future__ import annotations

import importlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ALPHA158_SOURCE_FILE = "qlib/contrib/data/loader.py"
ALPHA158_SOURCE_FUNCTION = "Alpha158DL.get_feature_config"
FIELD_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True)
class Alpha158Formula:
    name: str
    expression: str
    category: str
    required_fields: tuple[str, ...]


def qlib_source_commit(qlib_source: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(qlib_source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"


def load_alpha158_feature_config(qlib_source: Path) -> tuple[list[str], list[str]]:
    source = str(qlib_source)
    if source not in sys.path:
        sys.path.insert(0, source)
    module = importlib.import_module("qlib.contrib.data.loader")
    fields, names = module.Alpha158DL.get_feature_config()
    if len(fields) != len(names):
        raise ValueError(f"Alpha158 fields/names length mismatch: {len(fields)} != {len(names)}")
    return list(fields), list(names)


def infer_alpha158_category(name: str) -> str:
    if name in {"KMID", "KLEN", "KMID2", "KUP", "KUP2", "KLOW", "KLOW2", "KSFT", "KSFT2"}:
        return "kbar"
    if re.fullmatch(r"(OPEN|HIGH|LOW|CLOSE|VWAP|VOLUME)\d+", name):
        return "price_volume_lag"
    if re.fullmatch(r"(ROC|MA|STD|BETA|RSQR|RESI|MAX|MIN|QTLU|QTLD|RANK|RSV|IMAX|IMIN|IMXD)\d+", name):
        return "rolling_price"
    if re.fullmatch(r"(CORR|CORD)\d+", name):
        return "price_volume_correlation"
    if re.fullmatch(r"(CNTP|CNTN|CNTD|SUMP|SUMN|SUMD)\d+", name):
        return "price_momentum_balance"
    if re.fullmatch(r"(VMA|VSTD|WVMA|VSUMP|VSUMN|VSUMD)\d+", name):
        return "volume_liquidity"
    return "other"


def extract_required_fields(expression: str) -> tuple[str, ...]:
    return tuple(sorted({f"${match.group(1).lower()}" for match in FIELD_RE.finditer(expression)}))


def build_alpha158_formulas(qlib_source: Path) -> list[Alpha158Formula]:
    fields, names = load_alpha158_feature_config(qlib_source)
    return [
        Alpha158Formula(
            name=name,
            expression=expression,
            category=infer_alpha158_category(name),
            required_fields=extract_required_fields(expression),
        )
        for expression, name in zip(fields, names)
    ]


def collect_provider_fields(provider_uri: Path) -> pd.DataFrame:
    feature_root = provider_uri / "features"
    instrument_dirs = sorted(path for path in feature_root.iterdir() if path.is_dir())
    rows = []
    for instrument_dir in instrument_dirs:
        fields = {path.name.rsplit(".", 2)[0].lower() for path in instrument_dir.glob("*.day.bin")}
        for field in fields:
            rows.append({"instrument": instrument_dir.name, "field": field})
    if not rows:
        return pd.DataFrame(columns=["field", "instrument_count", "feature_instrument_count", "file_presence_rate"])
    frame = pd.DataFrame(rows)
    total = len(instrument_dirs)
    result = frame.groupby("field").size().reset_index(name="instrument_count")
    result["feature_instrument_count"] = total
    result["file_presence_rate"] = result["instrument_count"] / total if total else 0.0
    return result.sort_values("field").reset_index(drop=True)


def build_formula_inventory(
    formulas: list[Alpha158Formula],
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
                "catalog_name": f"alpha158_{formula.name}",
                "category": formula.category,
                "expression": formula.expression,
                "required_fields": ",".join(formula.required_fields),
                "missing_fields": ",".join(missing),
                "field_status": "available" if not missing else "missing",
                "source_project": "qlib_alpha158",
                "source_file": ALPHA158_SOURCE_FILE,
                "source_function": ALPHA158_SOURCE_FUNCTION,
                "source_commit": source_commit,
                "source_path": (qlib_source / ALPHA158_SOURCE_FILE).as_posix(),
            }
        )
    return pd.DataFrame(rows)


def alpha158_catalog_payload(inventory: pd.DataFrame, *, enabled: bool, runnable: bool, stage: str) -> dict:
    factors = []
    for row in inventory.itertuples(index=False):
        factors.append(
            {
                "name": row.catalog_name,
                "registry_name": row.catalog_name,
                "category": f"alpha158_{row.category}",
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
                "notes": f"Qlib Alpha158 expression: {row.expression}",
            }
        )
    return {
        "version": 1,
        "updated": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "policy": {
            "purpose": "Generated Qlib Alpha158 catalog supplement.",
            "principle": [
                "Expressions are copied from the local Qlib source via Alpha158DL.get_feature_config.",
                "Entries are not runnable until the Qlib expression adapter is audited.",
            ],
        },
        "factors": factors,
    }
