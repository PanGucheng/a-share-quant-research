from __future__ import annotations

import json
from pathlib import Path

import pytest

from qlib_baseline.io import atomic_output_path, atomic_write_json, atomic_write_text


def test_atomic_text_and_json_replace_existing_targets(tmp_path: Path) -> None:
    text_path = tmp_path / "nested/value.txt"
    text_path.parent.mkdir()
    text_path.write_text("old", encoding="utf-8")
    assert atomic_write_text(text_path, "new") == text_path
    assert text_path.read_text(encoding="utf-8") == "new"

    json_path = tmp_path / "state.json"
    atomic_write_json(json_path, {"b": 2, "a": 1})
    assert json.loads(json_path.read_text(encoding="utf-8")) == {"a": 1, "b": 2}
    assert json_path.read_text(encoding="utf-8").endswith("\n")


def test_atomic_output_cleans_temporary_file_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "result.csv"
    target.write_text("preserved", encoding="utf-8")
    with pytest.raises(RuntimeError, match="stop"):
        with atomic_output_path(target) as temporary:
            temporary.write_text("partial", encoding="utf-8")
            raise RuntimeError("stop")
    assert target.read_text(encoding="utf-8") == "preserved"
    assert list(tmp_path.glob(".*.tmp")) == []
