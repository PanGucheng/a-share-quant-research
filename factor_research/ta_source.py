from __future__ import annotations

import hashlib
import json
import sys
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml

from factor_research.factor_library import BASE_FIELDS
from factor_research.report import markdown_table


BASE_COLUMNS = ["datetime", "instrument", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class TaSourceConfig:
    provider_uri: str
    market: str
    start: str
    end: str
    max_instruments: int | None
    source_local_path: Path
    source_commit: str
    source_file: str
    source_function: str
    license: str
    colprefix: str
    fillna: bool
    vectorized: bool
    exclude_prefixes: tuple[str, ...]
    selected_smoke_factors: tuple[str, ...]
    catalog_stage: str
    catalog_enabled: bool
    catalog_runnable: bool
    labels: tuple[str, ...]
    output_dir: Path
    refresh: bool = False


def cache_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def factor_frame_cache_path(config: TaSourceConfig) -> Path:
    payload = {
        "provider_uri": str(config.provider_uri).replace("\\", "/"),
        "market": config.market,
        "start": config.start,
        "end": config.end,
        "max_instruments": config.max_instruments,
        "source_commit": config.source_commit,
        "fillna": config.fillna,
        "vectorized": config.vectorized,
        "exclude_prefixes": list(config.exclude_prefixes),
        "version": 1,
    }
    return config.output_dir / f"factor_frame_{cache_digest(payload)}.pkl"


def import_ta_wrapper(source_local_path: Path) -> Callable[..., pd.DataFrame]:
    if not source_local_path.exists():
        raise FileNotFoundError(f"Missing ta source repository: {source_local_path}")
    source_path = str(source_local_path)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    from ta.wrapper import add_all_ta_features

    return add_all_ta_features


def load_qlib_ohlcv(config: TaSourceConfig) -> pd.DataFrame:
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
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return frame.rename(
        columns={
            "$open": "open",
            "$high": "high",
            "$low": "low",
            "$close": "close",
            "$volume": "volume",
        }
    )


def compute_ta_features(config: TaSourceConfig, ohlcv: pd.DataFrame) -> pd.DataFrame:
    add_all_ta_features = import_ta_wrapper(config.source_local_path)
    frames = []
    for instrument, group in ohlcv.groupby("instrument", sort=True):
        source = group[BASE_COLUMNS].sort_values("datetime").copy()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning, module=r"ta\.")
            computed = add_all_ta_features(
                source,
                open="open",
                high="high",
                low="low",
                close="close",
                volume="volume",
                fillna=config.fillna,
                colprefix=config.colprefix,
                vectorized=config.vectorized,
            )
        computed["instrument"] = instrument
        frames.append(computed)
    if not frames:
        return pd.DataFrame(columns=["datetime", "instrument"])
    result = pd.concat(frames, ignore_index=True)
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str).str.upper()
    return result.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def column_category(column: str, colprefix: str) -> str:
    value = column.removeprefix(colprefix)
    return value.split("_", maxsplit=1)[0] if "_" in value else "unknown"


def column_exclusion_reason(column: str, config: TaSourceConfig) -> str:
    for prefix in config.exclude_prefixes:
        if column.startswith(prefix):
            if prefix == f"{config.colprefix}trend_visual_ichimoku":
                return "excluded_visual_ichimoku_forward_shift"
            if prefix == f"{config.colprefix}others_":
                return "excluded_return_label_overlap"
            if prefix in {f"{config.colprefix}volume_vpt", f"{config.colprefix}volume_nvi"}:
                return "excluded_pct_change_default_fill_method_warning"
            return f"excluded_prefix:{prefix}"
    return ""


def build_inventory(config: TaSourceConfig, frame: pd.DataFrame) -> pd.DataFrame:
    factor_columns = [column for column in frame.columns if column.startswith(config.colprefix)]
    rows = []
    total_rows = len(frame)
    for column in factor_columns:
        numeric = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        reason = column_exclusion_reason(column, config)
        rows.append(
            {
                "factor": column,
                "category": column_category(column, config.colprefix),
                "eligible": reason == "",
                "exclusion_reason": reason,
                "valid_rows": int(numeric.notna().sum()),
                "total_rows": int(total_rows),
                "coverage": float(numeric.notna().sum() / total_rows) if total_rows else 0.0,
                "missing_rate": float(1 - numeric.notna().sum() / total_rows) if total_rows else 1.0,
                "min": float(numeric.min()) if numeric.notna().any() else pd.NA,
                "max": float(numeric.max()) if numeric.notna().any() else pd.NA,
                "mean": float(numeric.mean()) if numeric.notna().any() else pd.NA,
                "source_project": "ta",
                "source_function": config.source_function,
                "source_commit": config.source_commit,
                "license": config.license,
            }
        )
    return pd.DataFrame(rows).sort_values(["eligible", "category", "factor"], ascending=[False, True, True])


def eligible_factor_columns(inventory: pd.DataFrame) -> list[str]:
    return inventory[inventory["eligible"]]["factor"].tolist()


def build_factor_frame(frame: pd.DataFrame, factors: list[str]) -> pd.DataFrame:
    result = frame[["datetime", "instrument", *factors]].copy()
    for factor in factors:
        result[factor] = pd.to_numeric(result[factor], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return result.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def required_fields_for_factor(factor: str) -> list[str]:
    category = factor.split("_", maxsplit=2)[1] if factor.startswith("ta_") and factor.count("_") >= 2 else "unknown"
    if category in {"volume", "momentum"}:
        return ["$open", "$high", "$low", "$close", "$volume"]
    if category in {"volatility", "trend"}:
        return ["$open", "$high", "$low", "$close"]
    return ["$open", "$high", "$low", "$close", "$volume"]


def catalog_payload(config: TaSourceConfig, inventory: pd.DataFrame) -> dict:
    factors = []
    for row in inventory[inventory["eligible"]].itertuples(index=False):
        factors.append(
            {
                "name": row.factor,
                "registry_name": row.factor,
                "category": f"ta_{row.category}",
                "source_project": "ta",
                "source_file": config.source_file,
                "source_function": config.source_function,
                "source_commit": config.source_commit,
                "license": config.license,
                "expected_direction": "watch",
                "required_fields": required_fields_for_factor(str(row.factor)),
                "labels": list(config.labels),
                "stage": config.catalog_stage,
                "enabled": bool(config.catalog_enabled),
                "runnable": bool(config.catalog_runnable),
                "compute_adapter": "factor_research.ta_source.compute_ta_features",
                "notes": f"Generated from ta wrapper smoke; coverage={row.coverage:.6f}",
            }
        )
    return {
        "version": 1,
        "updated": "2026-06-26",
        "policy": {
            "purpose": "Temporary TA adapter smoke catalog before V4 promotion.",
            "principle": [
                "Formula definitions stay in the upstream ta project.",
                "Visual Ichimoku and return-label overlap columns are excluded before evaluation.",
                "Entries remain disabled/non-runnable until V4 evaluation and context checks pass.",
            ],
            "required_prefilter": ["data_quality", "tradability"],
        },
        "factors": factors,
    }


def manifest_payload(
    config: TaSourceConfig,
    raw: pd.DataFrame,
    frame: pd.DataFrame,
    inventory: pd.DataFrame,
    factor_frame_path: Path,
) -> dict:
    return {
        "config": {
            **asdict(config),
            "source_local_path": config.source_local_path.as_posix(),
            "output_dir": config.output_dir.as_posix(),
            "exclude_prefixes": list(config.exclude_prefixes),
            "selected_smoke_factors": list(config.selected_smoke_factors),
            "labels": list(config.labels),
        },
        "raw_rows": int(len(raw)),
        "factor_frame_rows": int(len(frame)),
        "instrument_count": int(frame["instrument"].nunique()) if not frame.empty else 0,
        "date_min": str(frame["datetime"].min()) if not frame.empty else "",
        "date_max": str(frame["datetime"].max()) if not frame.empty else "",
        "eligible_factor_count": int(inventory["eligible"].sum()) if not inventory.empty else 0,
        "excluded_factor_count": int((~inventory["eligible"]).sum()) if not inventory.empty else 0,
        "factor_frame_path": factor_frame_path.as_posix(),
    }


def write_report(config: TaSourceConfig, inventory: pd.DataFrame, output: Path) -> None:
    eligible = inventory[inventory["eligible"]].copy()
    excluded = inventory[~inventory["eligible"]].copy()
    category_counts = eligible.groupby("category").size().reset_index(name="eligible_count") if not eligible.empty else pd.DataFrame()
    smoke = inventory[inventory["factor"].isin(config.selected_smoke_factors)].copy()
    lines = [
        "# TA Factor Adapter Smoke V1",
        "",
        f"- Source: `{config.source_local_path.as_posix()}`",
        f"- Commit: `{config.source_commit}`",
        f"- License: `{config.license}`",
        f"- Date range: `{config.start}` to `{config.end}`",
        f"- Max instruments: `{config.max_instruments}`",
        f"- fillna: `{str(config.fillna).lower()}`",
        f"- vectorized: `{str(config.vectorized).lower()}`",
        f"- Eligible factors: `{len(eligible)}`",
        f"- Excluded factors: `{len(excluded)}`",
        "",
        "## Category Counts",
        "",
        markdown_table(category_counts),
        "",
        "## Selected Smoke Factors",
        "",
        markdown_table(smoke[["factor", "category", "eligible", "coverage", "missing_rate", "exclusion_reason"]]),
        "",
        "## Excluded Columns",
        "",
        markdown_table(excluded[["factor", "category", "exclusion_reason"]]),
        "",
        "## Notes",
        "",
        "- Upstream `ta` formulas are called directly from the local reference repository.",
        "- `fillna=false` keeps warm-up NaN values instead of silently imputing them.",
        "- `ta_trend_visual_ichimoku_*` is excluded because upstream `visual=True` shifts values forward.",
        "- `ta_others_*` is excluded because return-like outputs overlap with project labels and basic return factors.",
        "- `ta_volume_vpt` and `ta_volume_nvi` are excluded because the upstream implementation currently relies on pandas pct_change default fill behavior.",
        "- The generated catalog is disabled/non-runnable until V4 smoke evaluation promotes selected factors.",
        "",
        "## Output Files",
        "",
        "- `factor_frame.pkl`",
        "- `ta_factor_inventory.csv`",
        "- `ta_factor_catalog_smoke.yaml`",
        "- `ta_factor_frame_summary.csv`",
        "- `ta_factor_frame_sample.csv`",
        "- `ta_selected_smoke_factors.csv`",
        "- `ta_adapter_manifest.json`",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ta_adapter_smoke(config: TaSourceConfig) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = factor_frame_cache_path(config)
    final_path = config.output_dir / "factor_frame.pkl"
    if cache_path.exists() and not config.refresh:
        raw = pd.DataFrame()
        factor_frame = pd.read_pickle(cache_path)
        inventory = pd.read_csv(config.output_dir / "ta_factor_inventory.csv")
    else:
        raw = load_qlib_ohlcv(config)
        computed = compute_ta_features(config, raw)
        inventory = build_inventory(config, computed)
        factors = eligible_factor_columns(inventory)
        factor_frame = build_factor_frame(computed, factors)
        factor_frame.to_pickle(cache_path)
    factor_frame.to_pickle(final_path)
    inventory.to_csv(config.output_dir / "ta_factor_inventory.csv", index=False, encoding="utf-8-sig")
    factor_frame.head(200).to_csv(config.output_dir / "ta_factor_frame_sample.csv", index=False, encoding="utf-8-sig")
    inventory[inventory["eligible"]].to_csv(
        config.output_dir / "ta_factor_frame_summary.csv", index=False, encoding="utf-8-sig"
    )
    selected = inventory[inventory["factor"].isin(config.selected_smoke_factors)].copy()
    selected.to_csv(config.output_dir / "ta_selected_smoke_factors.csv", index=False, encoding="utf-8-sig")
    catalog = catalog_payload(config, inventory)
    (config.output_dir / "ta_factor_catalog_smoke.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    manifest = manifest_payload(config, raw, factor_frame, inventory, final_path)
    (config.output_dir / "ta_adapter_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(config, inventory, config.output_dir / "ta_adapter_report.md")
    return {
        "output_dir": config.output_dir,
        "factor_frame": final_path,
        "catalog": config.output_dir / "ta_factor_catalog_smoke.yaml",
        "report": config.output_dir / "ta_adapter_report.md",
    }
