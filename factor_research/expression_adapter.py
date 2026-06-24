from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from factor_research.catalog import FactorCatalogEntry, load_factor_catalog, select_entries


@dataclass(frozen=True)
class ExpressionFrameConfig:
    provider_uri: str
    market: str
    start: str
    end: str
    catalog_path: Path
    inventory_path: Path
    output_dir: Path
    enabled_only: bool = False
    runnable_only: bool = False
    stages: tuple[str, ...] = ("alpha158_first_batch_adapter_pending",)
    names: tuple[str, ...] = ()
    max_factors: int | None = None
    batch_size: int | None = None
    refresh: bool = False


def cache_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def load_alpha158_inventory(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing Alpha158 inventory: {path}")
    inventory = pd.read_csv(path)
    required = ["catalog_name", "factor_name", "expression", "field_status"]
    missing = [column for column in required if column not in inventory.columns]
    if missing:
        raise ValueError(f"Alpha158 inventory missing columns: {missing}")
    return inventory


def select_expression_entries(config: ExpressionFrameConfig) -> list[FactorCatalogEntry]:
    entries = load_factor_catalog(config.catalog_path)
    selected = select_entries(
        entries,
        enabled_only=config.enabled_only,
        runnable_only=config.runnable_only,
        stages=config.stages or None,
        names=config.names or None,
        max_factors=config.max_factors,
    )
    if not selected:
        raise ValueError("No expression catalog entries selected")
    return selected


def build_expression_table(entries: list[FactorCatalogEntry], inventory: pd.DataFrame) -> pd.DataFrame:
    selected = pd.DataFrame({"catalog_name": [entry.name for entry in entries]})
    table = selected.merge(inventory, on="catalog_name", how="left")
    missing = table[table["expression"].isna()]
    if not missing.empty:
        raise ValueError(f"Selected entries missing expressions: {missing['catalog_name'].tolist()}")
    unavailable = table[table["field_status"].ne("available")]
    if not unavailable.empty:
        raise ValueError(f"Selected entries have unavailable fields: {unavailable['catalog_name'].tolist()}")
    return table


def expression_frame_cache_path(config: ExpressionFrameConfig, expression_table: pd.DataFrame) -> Path:
    payload = {
        "provider_uri": str(config.provider_uri).replace("\\", "/"),
        "market": config.market,
        "start": config.start,
        "end": config.end,
        "catalog_path": config.catalog_path.as_posix(),
        "inventory_path": config.inventory_path.as_posix(),
        "catalog_names": expression_table["catalog_name"].tolist(),
        "expressions": expression_table["expression"].tolist(),
        "version": 1,
    }
    return config.output_dir / f"factor_frame_{cache_digest(payload)}.pkl"


def expression_chunk_cache_path(config: ExpressionFrameConfig, expression_table: pd.DataFrame, chunk_index: int) -> Path:
    payload = {
        "provider_uri": str(config.provider_uri).replace("\\", "/"),
        "market": config.market,
        "start": config.start,
        "end": config.end,
        "catalog_path": config.catalog_path.as_posix(),
        "inventory_path": config.inventory_path.as_posix(),
        "catalog_names": expression_table["catalog_name"].tolist(),
        "expressions": expression_table["expression"].tolist(),
        "chunk_index": chunk_index,
        "version": "chunk_v1",
    }
    return config.output_dir / f"factor_frame_chunk_{chunk_index:03d}_{cache_digest(payload)}.pkl"


def normalize_qlib_expression_output(data: pd.DataFrame, expression_table: pd.DataFrame) -> pd.DataFrame:
    expressions = expression_table["expression"].tolist()
    names = expression_table["catalog_name"].tolist()
    frame = data.rename(columns=dict(zip(expressions, names))).reset_index()
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame = frame.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    return frame[["datetime", "instrument", *names]]


def compute_qlib_expression_frame(config: ExpressionFrameConfig, expression_table: pd.DataFrame) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=config.provider_uri, region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    instruments = D.instruments(config.market)
    batch_size = config.batch_size or len(expression_table)
    batch_size = max(1, int(batch_size))
    total_chunks = (len(expression_table) + batch_size - 1) // batch_size
    chunks: list[pd.DataFrame] = []
    for chunk_index, start in enumerate(range(0, len(expression_table), batch_size), start=1):
        chunk_table = expression_table.iloc[start : start + batch_size].reset_index(drop=True)
        chunk_cache = expression_chunk_cache_path(config, chunk_table, chunk_index)
        if chunk_cache.exists() and not config.refresh:
            print(f"Loading expression chunk {chunk_index}/{total_chunks}: {chunk_cache.name}", flush=True)
            chunk_frame = pd.read_pickle(chunk_cache)
        else:
            names = ", ".join(chunk_table["catalog_name"].tolist())
            print(f"Computing expression chunk {chunk_index}/{total_chunks}: {names}", flush=True)
            data = D.features(
                instruments,
                chunk_table["expression"].tolist(),
                start_time=config.start,
                end_time=config.end,
                freq="day",
            )
            chunk_frame = normalize_qlib_expression_output(data, chunk_table)
            chunk_frame.to_pickle(chunk_cache)
            print(f"Wrote expression chunk {chunk_index}/{total_chunks}: rows={len(chunk_frame):,}", flush=True)
        chunks.append(chunk_frame)
    result = chunks[0]
    for chunk in chunks[1:]:
        result = result.merge(chunk, on=["datetime", "instrument"], how="outer", validate="one_to_one")
    names = expression_table["catalog_name"].tolist()
    result = result.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    return result[["datetime", "instrument", *names]]


def summarize_expression_frame(frame: pd.DataFrame, factor_columns: list[str]) -> pd.DataFrame:
    rows = []
    total = len(frame)
    for factor in factor_columns:
        numeric = pd.to_numeric(frame[factor], errors="coerce")
        valid = numeric.notna()
        rows.append(
            {
                "factor": factor,
                "valid_rows": int(valid.sum()),
                "total_rows": int(total),
                "coverage": float(valid.sum() / total) if total else 0.0,
                "missing_rate": float(1 - valid.sum() / total) if total else 1.0,
                "min": float(numeric.min()) if valid.any() else pd.NA,
                "max": float(numeric.max()) if valid.any() else pd.NA,
                "mean": float(numeric.mean()) if valid.any() else pd.NA,
            }
        )
    return pd.DataFrame(rows)


def manifest_payload(
    config: ExpressionFrameConfig,
    expression_table: pd.DataFrame,
    frame: pd.DataFrame,
    frame_path: Path,
) -> dict:
    return {
        "config": {
            **asdict(config),
            "catalog_path": config.catalog_path.as_posix(),
            "inventory_path": config.inventory_path.as_posix(),
            "output_dir": config.output_dir.as_posix(),
            "stages": list(config.stages),
            "names": list(config.names),
        },
        "factor_count": int(len(expression_table)),
        "row_count": int(len(frame)),
        "date_min": str(frame["datetime"].min()) if not frame.empty else "",
        "date_max": str(frame["datetime"].max()) if not frame.empty else "",
        "instrument_count": int(frame["instrument"].nunique()) if not frame.empty else 0,
        "factor_frame_path": frame_path.as_posix(),
        "factors": expression_table[["catalog_name", "factor_name", "category", "expression"]].to_dict(orient="records"),
    }


def build_expression_frame(config: ExpressionFrameConfig) -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    inventory = load_alpha158_inventory(config.inventory_path)
    entries = select_expression_entries(config)
    expression_table = build_expression_table(entries, inventory)
    factor_columns = expression_table["catalog_name"].tolist()
    cache_path = expression_frame_cache_path(config, expression_table)
    final_path = config.output_dir / "factor_frame.pkl"
    if cache_path.exists() and not config.refresh:
        frame = pd.read_pickle(cache_path)
    else:
        frame = compute_qlib_expression_frame(config, expression_table)
        frame.to_pickle(cache_path)
    frame.to_pickle(final_path)
    expression_table.to_csv(config.output_dir / "expression_table.csv", index=False, encoding="utf-8-sig")
    summary = summarize_expression_frame(frame, factor_columns)
    summary.to_csv(config.output_dir / "expression_frame_summary.csv", index=False, encoding="utf-8-sig")
    frame.head(200).to_csv(config.output_dir / "expression_frame_sample.csv", index=False, encoding="utf-8-sig")
    manifest = manifest_payload(config, expression_table, frame, final_path)
    (config.output_dir / "expression_frame_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return frame, expression_table, final_path
