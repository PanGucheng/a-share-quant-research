from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from daily_update import features, pipeline, provider, validation
from daily_update.sources import baostock, community


# Compact regression input: CI must not depend on ignored Forward runtime state.
FROZEN_FEATURES_FIXTURE = (
    Path(__file__).parent / "fixtures" / "daily_update_frozen_feature_names.json"
)


def _frozen_feature_names() -> list[str]:
    return list(
        json.loads(FROZEN_FEATURES_FIXTURE.read_text(encoding="utf-8"))[
            "feature_names"
        ]
    )


def test_pipeline_preserves_compatibility_reexports() -> None:
    expected = {
        "CommunityRelease": community.CommunityRelease,
        "NotReady": validation.NotReady,
        "baostock_release_window_open": baostock.baostock_release_window_open,
        "latest_community_release": community.latest_community_release,
        "ensure_community_provider": community.ensure_community_provider,
        "load_frozen_universe": validation.load_frozen_universe,
        "collect_baostock_range": baostock.collect_baostock_range,
        "collect_baostock_factor_once": baostock.collect_baostock_factor_once,
        "validate_baostock_target": validation.validate_baostock_target,
        "bridge_baostock_to_community": provider.bridge_baostock_to_community,
        "build_fallback_provider": provider.build_fallback_provider,
        "compute_frozen_snapshot": features.compute_frozen_snapshot,
        "community_daily": community.community_daily,
        "compatibility_smoke": validation.compatibility_smoke,
    }
    for name, implementation in expected.items():
        assert getattr(pipeline, name) is implementation


def test_frozen_daily_defaults_and_feature_order_are_unchanged() -> None:
    feature_names = _frozen_feature_names()

    assert pipeline.DailyUpdateConfig.__dataclass_fields__["min_coverage"].default == 0.95
    assert (
        pipeline.DailyUpdateConfig.__dataclass_fields__["warmup_calendar_days"].default
        == 450
    )
    assert len(feature_names) == 52
    assert pipeline.PREPROCESSING == features.PREPROCESSING
    assert pipeline.ALPHA158_TABLE == features.ALPHA158_TABLE
    assert pipeline.ALPHA360_TABLE == features.ALPHA360_TABLE


def test_pipeline_community_orchestration_writes_only_configured_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    feature_names = _frozen_feature_names()
    universe = tmp_path / "universe.txt"
    universe.write_text("SH600000\n", encoding="utf-8")
    provider_path = tmp_path / "provider"
    release = community.CommunityRelease(
        tag="test-release",
        target_trade_date=date(2026, 8, 7),
        manifest_url="https://example.invalid/manifest",
        archive_url="https://example.invalid/archive",
        archive_size=1,
        archive_sha256="0" * 64,
    )
    daily = pd.DataFrame(
        [
            {
                "date": "2026-08-07",
                "symbol": "SH600000",
                "raw_open": 10.0,
                "raw_high": 10.5,
                "raw_low": 9.8,
                "raw_close": 10.2,
                "raw_volume": 10000.0,
                "raw_amount": 102000.0,
                "factor": 0.1,
            }
        ]
    )
    snapshot = pd.DataFrame(
        [
            {
                "datetime": pd.Timestamp("2026-08-07"),
                "instrument": "SH600000",
                **{name: float(index) for index, name in enumerate(feature_names)},
            }
        ]
    )
    monkeypatch.setattr(pipeline, "latest_community_release", lambda: release)
    monkeypatch.setattr(
        pipeline,
        "ensure_community_provider",
        lambda _release, _cache: provider_path,
    )
    monkeypatch.setattr(
        pipeline,
        "community_daily",
        lambda _provider, _target, _instruments: daily,
    )
    monkeypatch.setattr(
        pipeline,
        "compute_frozen_snapshot",
        lambda _provider, _target, _instruments, _warmup: snapshot,
    )
    config = pipeline.DailyUpdateConfig(
        target_date=date(2026, 8, 7),
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "output",
        universe_file=universe,
        qlib_source=tmp_path / "qlib-source",
    )

    result = pipeline.run(config)

    target = config.output_dir / "2026-08-07"
    written = pd.read_csv(target / "feature_snapshot.csv")
    assert result["status"] == "ready"
    assert result["source"] == "community"
    assert result["factor_count"] == 52
    assert list(written.columns) == ["datetime", "instrument", *feature_names]
    assert (target / "community_qlib_daily.csv").is_file()
    assert not (tmp_path / "outputs").exists()
