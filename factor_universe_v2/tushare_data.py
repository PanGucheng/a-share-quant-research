from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def tushare_client(environment_variable: str = "TUSHARE_TOKEN") -> Any:
    token = os.environ.get(environment_variable)
    if not token:
        raise RuntimeError(f"{environment_variable} is required")
    import tushare as ts

    return ts.pro_api(token)


def classify_probe_error(exc: Exception) -> str:
    message = str(exc).lower()
    if any(word in message for word in ("权限", "积分", "permission", "抱歉")):
        return "permission_denied"
    if any(word in message for word in ("每分钟", "频率", "rate limit", "too many")):
        return "rate_limited"
    return "request_failed"


def probe_tushare(pro: Any, probes: list[dict[str, Any]], *, interval_seconds: float = 0.35) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for probe in probes:
        api = str(probe["api"])
        parameters = dict(probe.get("parameters") or {})
        started = time.perf_counter()
        try:
            frame = pro.query(api, **parameters)
            status = "accessible_nonempty" if not frame.empty else "accessible_empty"
            rows.append(
                {
                    "api": api,
                    "probe_status": status,
                    "probe_rows": len(frame),
                    "probe_columns": ",".join(str(column) for column in frame.columns),
                    "probe_elapsed_seconds": round(time.perf_counter() - started, 3),
                    "error_class": "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "api": api,
                    "probe_status": classify_probe_error(exc),
                    "probe_rows": 0,
                    "probe_columns": "",
                    "probe_elapsed_seconds": round(time.perf_counter() - started, 3),
                    "error_class": type(exc).__name__,
                }
            )
        time.sleep(interval_seconds)
    return pd.DataFrame(rows)


class TushareSegmentStore:
    """Small append/cache primitive for deterministic, restartable Tushare segments."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def paths(self, api: str, segment: str) -> tuple[Path, Path]:
        safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in segment)
        directory = self.root / api
        return directory / f"{safe}.parquet", directory / f"{safe}.receipt.json"

    def missing_segments(self, api: str, segments: list[str]) -> list[str]:
        return [
            segment
            for segment in segments
            if not all(path.is_file() for path in self.paths(api, segment))
        ]

    def validate(
        self,
        *,
        api: str,
        segment: str,
        required_columns: set[str] | None = None,
        public_parameters: dict[str, Any] | None = None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Load one cached segment only after receipt and content verification."""
        data_path, receipt_path = self.paths(api, segment)
        if not data_path.is_file() or not receipt_path.is_file():
            raise FileNotFoundError(f"missing cached segment: {api}:{segment}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
        if receipt.get("data_sha256") != digest:
            raise ValueError(f"cached segment hash mismatch: {api}:{segment}")
        if receipt.get("api") != api or receipt.get("segment") != segment:
            raise ValueError(f"cached segment receipt identity mismatch: {api}:{segment}")
        if public_parameters is not None and receipt.get("parameters") != public_parameters:
            raise ValueError(f"cached segment parameters mismatch: {api}:{segment}")
        frame = pd.read_parquet(data_path)
        missing = sorted(set(required_columns or ()) - set(frame.columns))
        if missing:
            raise ValueError(f"cached {api}:{segment} missing columns: {missing}")
        if int(receipt.get("row_count", -1)) != len(frame):
            raise ValueError(f"cached segment row-count mismatch: {api}:{segment}")
        return frame, receipt

    def fetch(
        self,
        *,
        api: str,
        segment: str,
        request: Callable[[], pd.DataFrame],
        required_columns: set[str],
        sort_columns: list[str],
        public_parameters: dict[str, Any] | None = None,
        attempts: int = 3,
        backoff_seconds: float = 1.0,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        public_parameters = dict(public_parameters or {})
        sensitive = [key for key in public_parameters if "token" in key.lower() or "secret" in key.lower()]
        if sensitive:
            raise ValueError(f"receipt parameters contain sensitive keys: {sensitive}")
        data_path, receipt_path = self.paths(api, segment)
        if data_path.is_file() and receipt_path.is_file():
            return self.validate(
                api=api,
                segment=segment,
                required_columns=required_columns,
                public_parameters=public_parameters,
            )
        frame: pd.DataFrame | None = None
        for attempt in range(attempts):
            try:
                frame = request()
                break
            except Exception:
                if attempt + 1 == attempts:
                    raise
                time.sleep(backoff_seconds * (2**attempt))
        if frame is None:
            raise RuntimeError(f"{api}:{segment} returned no frame")
        missing = sorted(required_columns - set(frame.columns))
        if missing:
            raise ValueError(f"{api}:{segment} missing columns: {missing}")
        normalized = frame.drop_duplicates().sort_values(sort_columns).reset_index(drop=True)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = data_path.with_suffix(".tmp.parquet")
        normalized.to_parquet(temporary, index=False)
        temporary.replace(data_path)
        digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
        receipt = {
            "api": api,
            "segment": segment,
            "parameters": public_parameters,
            "retrieval_time_utc": datetime.now(timezone.utc).isoformat(),
            "row_count": len(normalized),
            "columns": list(normalized.columns),
            "data_sha256": digest,
            "status": "pass",
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return normalized, receipt
