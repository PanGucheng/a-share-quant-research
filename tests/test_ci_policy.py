from __future__ import annotations

from pathlib import Path

from scripts.ci.check_docs import markdown_link_issues
from scripts.ci.classify_changes import classify_paths


def test_docs_only_change_uses_fast_path() -> None:
    result = classify_paths(
        ["docs/PROJECT_CONTEXT_SUMMARY.md", "README.md"]
    )
    assert result["docs_changed"]
    assert result["docs_only"]
    assert not result["research_code_changed"]
    assert not result["qlib_changed"]


def test_outputs_markdown_is_machine_evidence_not_docs_fast_path() -> None:
    result = classify_paths(["outputs/stage/current/report.md"])
    assert not result["docs_only"]
    assert result["research_code_changed"]


def test_research_code_skips_qlib_runtime() -> None:
    result = classify_paths(["factor_research/evaluator.py", "tests/test_factor.py"])
    assert result["research_code_changed"]
    assert not result["qlib_changed"]


def test_qlib_execution_change_runs_both_heavy_tiers() -> None:
    result = classify_paths(["qlib_integration/exchange_adapter.py"])
    assert result["research_code_changed"]
    assert result["qlib_changed"]


def test_workflow_or_dependency_change_runs_all_tiers() -> None:
    for path in [
        ".github/workflows/research-validation-ci.yml",
        "requirements-research-validation.txt",
        "scripts/check_quality.py",
    ]:
        result = classify_paths([path])
        assert result["research_code_changed"]
        assert result["qlib_changed"]


def test_machine_config_and_manifest_run_research_validation() -> None:
    result = classify_paths(
        [
            "configs/research_model_protocol_v1.yaml",
            "outputs/example/current/artifact_manifest.json",
        ]
    )
    assert result["research_code_changed"]
    assert not result["qlib_changed"]


def test_markdown_local_link_checker(tmp_path: Path, monkeypatch) -> None:
    import scripts.ci.check_docs as check_docs

    monkeypatch.setattr(check_docs, "PROJECT_ROOT", tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    target = docs / "target.md"
    target.write_text("# Target\n", encoding="utf-8")
    source = docs / "source.md"
    source.write_text("[ok](target.md)\n", encoding="utf-8")
    assert markdown_link_issues(source) == []
    source.write_text("[bad](missing.md)\n", encoding="utf-8")
    assert "missing local link" in markdown_link_issues(source)[0]
