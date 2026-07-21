from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

from research_validation.input_provenance import (
    git_repo_receipt,
    inventory_tree_hash,
    normalized_required_fields,
    provider_file_inventory,
    raw_parquet_receipt,
    verify_file_inventory,
)


def test_provider_inventory_hash_detects_external_mutation(tmp_path: Path) -> None:
    provider = tmp_path / "provider"
    (provider / "calendars").mkdir(parents=True)
    (provider / "instruments").mkdir()
    (provider / "features/sh600000").mkdir(parents=True)
    (provider / "calendars/day.txt").write_text("2024-01-02\n", encoding="utf-8")
    (provider / "instruments/all.txt").write_text("sh600000\t2024-01-02\t2024-01-02\n", encoding="utf-8")
    (provider / "features/sh600000/close.day.bin").write_bytes(b"close")
    inventory = provider_file_inventory(
        provider,
        ["SH600000"],
        ["$close"],
        calendar_files=["calendars/day.txt"],
        instrument_files=["instruments/all.txt"],
        workers=1,
    )
    assert inventory["exists"].all()
    assert len(inventory_tree_hash(inventory)) == 64
    csv_path = tmp_path / "inventory.csv"
    inventory.to_csv(csv_path, index=False)
    assert inventory_tree_hash(pd.read_csv(csv_path)) == inventory_tree_hash(inventory)
    assert verify_file_inventory(provider, inventory, workers=1)["current_match"].all()

    (provider / "features/sh600000/close.day.bin").write_bytes(b"mutated")

    verified = verify_file_inventory(provider, inventory, workers=1)
    assert int((~verified["current_match"]).sum()) == 1


def test_raw_parquet_receipt_freezes_schema_keys_and_instruments(tmp_path: Path) -> None:
    path = tmp_path / "raw.parquet"
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "instrument": ["SH600000", "SZ000001"],
            "$close": [10.0, 20.0],
        }
    )
    frame.to_parquet(path, index=False)

    receipt, schema = raw_parquet_receipt(path, ["datetime", "instrument", "$close"])

    assert receipt["row_count"] == 2
    assert receipt["instrument_count"] == 2
    assert receipt["duplicate_key_count"] == 0
    assert receipt["missing_required_columns"] == []
    assert schema["column_order"] == ["datetime", "instrument", "$close"]


def test_git_receipt_only_blocks_dirty_dependency_closure(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "used.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "unrelated.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    receipt = git_repo_receipt(tmp_path, ["used.py"])

    assert receipt["repo_clean"] is False
    assert receipt["dependency_dirty_paths"] == []


def test_required_fields_are_normalized_and_deduplicated() -> None:
    assert normalized_required_fields(["$close,$open", "$close", pd.NA]) == ["$close", "$open"]
