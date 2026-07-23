from __future__ import annotations

import hashlib
import json
import sys
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from factor_research.factor_library import BASE_FIELDS
from factor_research.report import markdown_table


FIELD_TO_WIND = {
    "$open": "S_DQ_OPEN",
    "$high": "S_DQ_HIGH",
    "$low": "S_DQ_LOW",
    "$close": "S_DQ_CLOSE",
    "$volume": "S_DQ_VOLUME",
    "$amount": "S_DQ_AMOUNT",
}


@dataclass(frozen=True)
class Alpha101SourceConfig:
    provider_uri: str
    market: str
    start: str
    end: str
    max_instruments: int | None
    source_local_path: Path
    source_commit: str
    source_file: str
    source_module: str
    license: str
    selected_smoke_factors: tuple[str, ...]
    metadata_catalog: Path
    catalog_stage: str
    catalog_enabled: bool
    catalog_runnable: bool
    labels: tuple[str, ...]
    output_dir: Path
    refresh: bool = False


def cache_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def factor_frame_cache_path(config: Alpha101SourceConfig) -> Path:
    payload = {
        "provider_uri": str(config.provider_uri).replace("\\", "/"),
        "market": config.market,
        "start": config.start,
        "end": config.end,
        "max_instruments": config.max_instruments,
        "source_commit": config.source_commit,
        "selected_smoke_factors": list(config.selected_smoke_factors),
        "version": 2,
    }
    return config.output_dir / f"factor_frame_{cache_digest(payload)}.pkl"


def import_ref_alpha101(source_local_path: Path):
    if not source_local_path.exists():
        raise FileNotFoundError(f"Missing KunQuant source repository: {source_local_path}")
    repo = str(source_local_path)
    tests = str(source_local_path / "tests")
    for path in [repo, tests]:
        if path not in sys.path:
            sys.path.insert(0, path)
    from KunTestUtil import ref_alpha101

    return ref_alpha101


def load_qlib_ohlcva(config: Alpha101SourceConfig) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=config.provider_uri, region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    universe = D.instruments(config.market)
    instruments = D.list_instruments(universe, start_time=config.start, end_time=config.end, as_list=True)
    instruments = sorted(str(item).upper() for item in instruments)
    if config.max_instruments is not None:
        instruments = instruments[: int(config.max_instruments)]
    data = D.features(
        instruments,
        BASE_FIELDS,
        start_time=config.start,
        end_time=config.end,
        freq="day",
    )
    frame = data.reset_index().sort_values(["instrument", "datetime"]).reset_index(drop=True)
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame


def to_wind_wide(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    result = {}
    for qlib_field, wind_name in FIELD_TO_WIND.items():
        wide = frame.pivot(index="datetime", columns="instrument", values=qlib_field)
        result[wind_name] = wide.sort_index().sort_index(axis=1)
    return result


def mask_raw_to_pit_membership(
    raw: pd.DataFrame,
    membership_keys: pd.DataFrame,
    *,
    membership_start: object,
) -> pd.DataFrame:
    """Mask factor inputs outside the dated PIT universe.

    Pre-universe warmup rows remain available. From ``membership_start`` onward,
    every OHLCVA field is NaN outside the exact date-instrument membership so
    pandas cross-sectional operators cannot see lifecycle-illegal or
    out-of-universe instruments.
    """

    keys = membership_keys[["datetime", "instrument"]].copy()
    keys["datetime"] = pd.to_datetime(keys["datetime"])
    keys["instrument"] = keys["instrument"].astype(str).str.upper()
    keys["_pit_member"] = True
    if keys.duplicated(["datetime", "instrument"]).any():
        raise ValueError("membership keys must be unique")
    result = raw.copy()
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()
    result = result.merge(keys, on=["datetime", "instrument"], how="left", validate="many_to_one")
    mask = result["datetime"].ge(pd.Timestamp(membership_start)) & result["_pit_member"].ne(True)
    result.loc[mask, BASE_FIELDS] = np.nan
    return result.drop(columns="_pit_member")


def load_metadata_catalog(path: Path) -> pd.DataFrame:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = []
    for item in payload.get("factors", []):
        rows.append(
            {
                "factor": item["name"],
                "registry_name": item.get("registry_name", item["name"]),
                "category": item.get("category", "alpha101"),
                "required_fields": ",".join(item.get("required_fields", [])),
                "source_function": item.get("source_function", ""),
            }
        )
    return pd.DataFrame(rows)


def compute_alpha101_features(config: Alpha101SourceConfig, raw: pd.DataFrame) -> pd.DataFrame:
    ref_alpha101 = import_ref_alpha101(config.source_local_path)
    wide = to_wind_wide(raw)
    reference = wide["S_DQ_CLOSE"]
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The default fill_method='pad' in DataFrame.pct_change is deprecated",
            category=FutureWarning,
        )
        stock = ref_alpha101.Alphas(wide)
    # The vendored pandas reference relies on the deprecated pct_change
    # default (forward-fill). Override it so PIT membership gaps cannot carry
    # stale closes into Alpha101 returns.
    stock.returns = stock.close.pct_change(fill_method=None)
    metadata = load_metadata_catalog(config.metadata_catalog).set_index("factor")
    output_frames = []
    for factor in config.selected_smoke_factors:
        if factor not in metadata.index:
            raise ValueError(f"Selected factor missing from metadata catalog: {factor}")
        method_name = str(metadata.loc[factor, "registry_name"])
        if not hasattr(stock, method_name):
            raise ValueError(f"KunQuant reference missing method: {method_name}")
        values = getattr(stock, method_name)()
        if not isinstance(values, pd.DataFrame):
            raise TypeError(f"KunQuant reference method {method_name} returned {type(values).__name__}, expected DataFrame")
        values = values.copy()
        assert_alpha101_axes(values, reference, method_name)
        values = values.sort_index().sort_index(axis=1)
        series = values.stack(future_stack=True).rename(factor)
        output_frames.append(series)
    combined = pd.concat(output_frames, axis=1).reset_index()
    combined = combined.rename(columns={"level_0": "datetime", "level_1": "instrument"})
    combined["datetime"] = pd.to_datetime(combined["datetime"])
    combined["instrument"] = combined["instrument"].astype(str).str.upper()
    for factor in config.selected_smoke_factors:
        combined[factor] = pd.to_numeric(combined[factor], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return combined.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def assert_alpha101_axes(
    values: pd.DataFrame,
    reference: pd.DataFrame,
    method_name: str,
) -> None:
    """Reject positional relabeling even when axis lengths happen to match."""

    if not values.index.equals(reference.index):
        raise ValueError(
            f"Alpha101 {method_name} index mismatch; positional relabel is forbidden"
        )
    if not values.columns.equals(reference.columns):
        raise ValueError(
            f"Alpha101 {method_name} columns mismatch; positional relabel is forbidden"
        )


def build_inventory(config: Alpha101SourceConfig, frame: pd.DataFrame) -> pd.DataFrame:
    metadata = load_metadata_catalog(config.metadata_catalog).set_index("factor")
    rows = []
    total_rows = len(frame)
    for factor in config.selected_smoke_factors:
        numeric = pd.to_numeric(frame[factor], errors="coerce").replace([np.inf, -np.inf], np.nan)
        valid_rows = int(numeric.notna().sum())
        rows.append(
            {
                "factor": factor,
                "registry_name": metadata.loc[factor, "registry_name"] if factor in metadata.index else factor,
                "category": metadata.loc[factor, "category"] if factor in metadata.index else "alpha101",
                "eligible": bool(valid_rows > 0),
                "exclusion_reason": "" if valid_rows > 0 else "zero_valid_rows",
                "valid_rows": valid_rows,
                "total_rows": int(total_rows),
                "coverage": float(valid_rows / total_rows) if total_rows else 0.0,
                "missing_rate": float(1 - valid_rows / total_rows) if total_rows else 1.0,
                "min": float(numeric.min()) if numeric.notna().any() else pd.NA,
                "max": float(numeric.max()) if numeric.notna().any() else pd.NA,
                "mean": float(numeric.mean()) if numeric.notna().any() else pd.NA,
                "source_project": "kunquant_alpha101",
                "source_function": metadata.loc[factor, "source_function"] if factor in metadata.index else factor,
                "source_commit": config.source_commit,
                "license": config.license,
                "required_fields": metadata.loc[factor, "required_fields"] if factor in metadata.index else "",
            }
        )
    return pd.DataFrame(rows).sort_values("factor")


def catalog_payload(config: Alpha101SourceConfig, inventory: pd.DataFrame) -> dict[str, Any]:
    factors = []
    for row in inventory.itertuples(index=False):
        factors.append(
            {
                "name": row.factor,
                "registry_name": row.registry_name,
                "category": row.category,
                "source_project": "kunquant_alpha101",
                "source_file": config.source_file,
                "source_function": row.source_function,
                "source_commit": config.source_commit,
                "license": config.license,
                "expected_direction": "watch",
                "required_fields": str(row.required_fields).split(",") if row.required_fields else list(FIELD_TO_WIND),
                "labels": list(config.labels),
                "stage": config.catalog_stage,
                "enabled": bool(config.catalog_enabled),
                "runnable": bool(config.catalog_runnable),
                "compute_adapter": "factor_research.alpha101_source.compute_alpha101_features",
                "notes": f"Generated from KunQuant pandas reference adapter; coverage={row.coverage:.6f}",
            }
        )
    return {
        "version": 1,
        "updated": "2026-06-28",
        "policy": {
            "purpose": "Temporary KunQuant Alpha101 adapter catalog before V4 promotion.",
            "principle": [
                "Formula definitions are sourced from KunQuant reference code.",
                "Entries remain disabled/non-runnable until V4 evaluation passes.",
                "Use data_quality and tradability filters before evaluation.",
            ],
            "required_prefilter": ["data_quality", "tradability"],
        },
        "factors": factors,
    }


def manifest_payload(
    config: Alpha101SourceConfig,
    raw: pd.DataFrame,
    frame: pd.DataFrame,
    inventory: pd.DataFrame,
    factor_frame_path: Path,
) -> dict[str, Any]:
    return {
        "config": {
            **asdict(config),
            "source_local_path": config.source_local_path.as_posix(),
            "metadata_catalog": config.metadata_catalog.as_posix(),
            "output_dir": config.output_dir.as_posix(),
            "selected_smoke_factors": list(config.selected_smoke_factors),
            "labels": list(config.labels),
        },
        "loaded_from_cache": bool(raw.empty),
        "raw_rows": int(len(raw)) if not raw.empty else None,
        "factor_frame_rows": int(len(frame)),
        "instrument_count": int(frame["instrument"].nunique()) if not frame.empty else 0,
        "date_min": str(frame["datetime"].min()) if not frame.empty else "",
        "date_max": str(frame["datetime"].max()) if not frame.empty else "",
        "factor_count": int(len(inventory)),
        "factor_frame_path": factor_frame_path.as_posix(),
    }


def write_report(config: Alpha101SourceConfig, inventory: pd.DataFrame, output: Path) -> None:
    lines = [
        "# Alpha101 Adapter Run V1",
        "",
        f"- Source: `{config.source_local_path.as_posix()}`",
        f"- Source file: `{config.source_file}`",
        f"- Source module: `{config.source_module}`",
        f"- Source commit: `{config.source_commit}`",
        f"- Selected factors: `{len(config.selected_smoke_factors)}`",
        "",
        "## Inventory",
        "",
        markdown_table(inventory),
        "",
        "## Boundary",
        "",
        "- This adapter run uses KunQuant's pandas reference implementation.",
        "- Catalog entries are disabled/non-runnable until V4 evaluation and promotion pass.",
        "- Ginkgo_Alpha101 remains a metadata reference because no local formula implementation is available.",
        "",
        "## Output Files",
        "",
        "- `factor_frame.pkl`",
        "- `alpha101_factor_inventory.csv`",
        "- `alpha101_selected_smoke_factors.csv`",
        "- `alpha101_factor_catalog_smoke.yaml`",
        "- `alpha101_adapter_manifest.json`",
        "- `alpha101_adapter_report.md`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_alpha101_adapter_smoke(config: Alpha101SourceConfig) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    factor_frame_path = factor_frame_cache_path(config)
    if factor_frame_path.exists() and not config.refresh:
        frame = pd.read_pickle(factor_frame_path)
        raw = pd.DataFrame()
    else:
        raw = load_qlib_ohlcva(config)
        frame = compute_alpha101_features(config, raw)
        frame.to_pickle(factor_frame_path)
    frame.to_pickle(config.output_dir / "factor_frame.pkl")
    inventory = build_inventory(config, frame)
    inventory.to_csv(config.output_dir / "alpha101_factor_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"factor": list(config.selected_smoke_factors)}).to_csv(
        config.output_dir / "alpha101_selected_smoke_factors.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (config.output_dir / "alpha101_factor_catalog_smoke.yaml").write_text(
        yaml.safe_dump(catalog_payload(config, inventory), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    manifest = manifest_payload(config, raw, frame, inventory, factor_frame_path)
    (config.output_dir / "alpha101_adapter_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    frame.head(2000).to_csv(config.output_dir / "alpha101_factor_frame_sample.csv", index=False, encoding="utf-8-sig")
    write_report(config, inventory, config.output_dir / "alpha101_adapter_report.md")
    return {"output_dir": config.output_dir, "factor_frame": factor_frame_path}
