from __future__ import annotations

from pathlib import Path

from research_validation.stage_output import StageOutputPublisher


def test_blocked_publish_removes_old_runtime_and_publishes_empty_schema(tmp_path: Path) -> None:
    output = tmp_path / "stage"
    runtime = output / "runtime" / "scores.parquet"
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"old")
    with StageOutputPublisher(output, ["contract_status.csv", "runtime/scores.parquet"]) as publisher:
        publisher.path("contract_status.csv").write_text("status\nblocked\n", encoding="utf-8")
        publisher.publish()
    assert (output / "contract_status.csv").is_file()
    assert not runtime.exists()


def test_failed_staging_does_not_replace_active_output(tmp_path: Path) -> None:
    output = tmp_path / "stage"
    output.mkdir()
    active = output / "result.csv"
    active.write_text("old", encoding="utf-8")
    try:
        with StageOutputPublisher(output, ["result.csv"]) as publisher:
            publisher.path("result.csv").write_text("partial", encoding="utf-8")
            raise RuntimeError("failed")
    except RuntimeError:
        pass
    assert active.read_text(encoding="utf-8") == "old"
