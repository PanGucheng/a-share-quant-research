from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pandas as pd

from .point_in_time_fields import PIT_COLUMNS, current_spot_to_pit


def collect_a_share_spot() -> tuple[pd.DataFrame, pd.DataFrame]:
    collected_at = pd.Timestamp(datetime.now(timezone.utc)).tz_convert(None)
    try:
        import akshare as ak
        raw = ak.stock_zh_a_spot_em()
        digest = hashlib.sha256(raw.to_csv(index=False).encode("utf-8")).hexdigest()[:16]
        snapshot_id = f"akshare_spot_{collected_at:%Y%m%dT%H%M%S}_{digest}"
        fields = current_spot_to_pit(raw, collected_at, snapshot_id)
        manifest = pd.DataFrame([{"raw_snapshot_id": snapshot_id, "source": "akshare.stock_zh_a_spot_em", "collected_at": collected_at, "status": "pass", "row_count": len(raw), "content_sha256": digest, "error": ""}])
        return fields, manifest
    except Exception as exc:
        manifest = pd.DataFrame([{"raw_snapshot_id": "", "source": "akshare.stock_zh_a_spot_em", "collected_at": collected_at, "status": "blocked", "row_count": 0, "content_sha256": "", "error": f"{type(exc).__name__}: {str(exc)[:1000]}"}])
        return pd.DataFrame(columns=PIT_COLUMNS), manifest
