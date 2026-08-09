from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from daily_update.features import (  # noqa: F401 - compatibility facade
    ALPHA158_TABLE,
    ALPHA360_TABLE,
    PREPROCESSING,
    _expression_features,
    compute_frozen_snapshot,
)
from daily_update.provider import (  # noqa: F401 - compatibility facade
    PROJECT_ROOT,
    _community_anchor,
    _load_raw,
    bridge_baostock_to_community,
    build_fallback_provider,
)
from daily_update.sources.baostock import (  # noqa: F401 - compatibility facade
    baostock_release_window_open,
    collect_baostock_factor_once,
    collect_baostock_range,
    collect_daily_adjust_factor,
    collect_daily_all,
)
from daily_update.sources.community import (  # noqa: F401 - compatibility facade
    COMMUNITY_REPOSITORY,
    CommunityRelease,
    _request,
    _sha256,
    community_daily,
    ensure_community_provider,
    latest_community_release,
)
from daily_update.validation import (
    NotReady,
    compatibility_smoke,
    load_frozen_universe,
    validate_baostock_target,
)


@dataclass(frozen=True)
class DailyUpdateConfig:
    target_date: date
    cache_dir: Path
    output_dir: Path
    universe_file: Path
    qlib_source: Path
    min_coverage: float = 0.95
    warmup_calendar_days: int = 450


def run(config: DailyUpdateConfig) -> dict[str, object]:
    release = latest_community_release()
    universe = load_frozen_universe(config.universe_file)
    target_dir = config.output_dir / config.target_date.isoformat()
    source = "community" if release.target_trade_date >= config.target_date else "baostock"
    readiness: dict[str, object] = {}
    raw_snapshot_first_seen_at: str | None = None

    if source == "baostock":
        if not baostock_release_window_open(config.target_date):
            raise NotReady(
                "BaoStock publication window is not complete; "
                "retry after 18:00 Asia/Shanghai"
            )
        raw, failures = collect_baostock_range(
            release.target_trade_date + timedelta(days=1),
            config.target_date,
        )
        raw_snapshot_first_seen_at = datetime.now(timezone.utc).isoformat()
        factor_frame, factor_status = collect_baostock_factor_once(config.target_date)
        if factor_status != "success":
            raise NotReady(f"BaoStock adjustment factor is not ready: {factor_status}")
        target_codes = (
            raw.loc[
                raw["date"].astype(str).eq(config.target_date.isoformat()),
                "code",
            ]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.upper()
            .unique()
        )
        expected = sorted(set(universe).intersection(target_codes))
        if not expected:
            raise NotReady(
                "BaoStock target daily batch does not overlap the frozen "
                "Strategy V1 universe"
            )
        readiness = validate_baostock_target(
            raw,
            config.target_date,
            expected,
            config.min_coverage,
        )
        readiness["published_sh_sz_market_instruments"] = len(set(target_codes))
        readiness["adjustment_factor_event_rows"] = len(factor_frame)
        readiness["request_failures"] = len(failures)
        if failures:
            raise NotReady(f"BaoStock returned {len(failures)} request failures")
        provider = ensure_community_provider(release, config.cache_dir)
        anchor = _community_anchor(provider, expected, release.target_trade_date)
        bridged = bridge_baostock_to_community(raw, anchor)
        provider = build_fallback_provider(
            provider,
            bridged,
            config.target_date,
            release,
            config.cache_dir,
            config.qlib_source,
        )
        daily = bridged.loc[
            bridged["date"].eq(pd.Timestamp(config.target_date))
        ].copy()
        snapshot = compute_frozen_snapshot(
            provider,
            config.target_date,
            expected,
            config.warmup_calendar_days,
        )
    else:
        provider = ensure_community_provider(release, config.cache_dir)
        daily = community_daily(provider, config.target_date, universe)
        raw_snapshot_first_seen_at = datetime.now(timezone.utc).isoformat()
        expected = sorted(daily["symbol"].unique())
        snapshot = compute_frozen_snapshot(
            provider,
            config.target_date,
            expected,
            config.warmup_calendar_days,
        )
        readiness = {
            "expected_instruments": len(expected),
            "complete_instruments": len(expected),
            "normal_trading_instruments": len(expected),
            "suspended_or_nontrading_instruments": 0,
            "missing_ohlcva_while_trading": 0,
            "coverage": 1.0,
            "ohlcva_complete": True,
        }

    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = "baostock" if source == "baostock" else "community"
    daily.to_csv(
        target_dir / f"{suffix}_qlib_daily.csv",
        index=False,
        encoding="utf-8-sig",
    )
    snapshot.to_csv(
        target_dir / f"feature_snapshot_{suffix}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    comparison = None
    fallback_daily_path = target_dir / "baostock_qlib_daily.csv"
    fallback_feature_path = target_dir / "feature_snapshot_baostock.csv"
    if (
        source == "community"
        and fallback_daily_path.is_file()
        and fallback_feature_path.is_file()
    ):
        comparison = compatibility_smoke(
            pd.read_csv(fallback_daily_path),
            daily,
            pd.read_csv(fallback_feature_path, parse_dates=["datetime"]),
            snapshot,
        )
        (target_dir / "factor_bridge_compatibility_smoke.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if comparison["status"] != "pass":
            (target_dir / "feature_snapshot.csv").unlink(missing_ok=True)
            blocked = {
                "status": "blocked_material_difference",
                "target_date": config.target_date.isoformat(),
                "source": source,
                "compatibility_smoke": comparison,
            }
            (target_dir / "summary.json").write_text(
                json.dumps(blocked, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(
                "Factor bridge compatibility smoke found a material difference"
            )

    snapshot.to_csv(
        target_dir / "feature_snapshot.csv",
        index=False,
        encoding="utf-8-sig",
    )
    feature_snapshot_created_at = datetime.now(timezone.utc).isoformat()
    result = {
        "status": "ready",
        "target_date": config.target_date.isoformat(),
        "source": source,
        "community_release": release.tag,
        "community_trade_date": release.target_trade_date.isoformat(),
        "provider_uri": str(provider),
        "feature_snapshot": str(target_dir / "feature_snapshot.csv"),
        "feature_rows": len(snapshot),
        "factor_count": len(snapshot.columns) - 2,
        "raw_snapshot_first_seen_at": raw_snapshot_first_seen_at,
        "feature_snapshot_created_at": feature_snapshot_created_at,
        "coverage": readiness,
        "compatibility_smoke": comparison,
    }
    (target_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
