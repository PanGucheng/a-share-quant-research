from __future__ import annotations

import ast
from pathlib import Path

from model_research import (
    forward_binding,
    forward_labels,
    forward_pipeline,
    forward_prediction,
    forward_state,
)


def test_forward_pipeline_preserves_compatibility_reexports() -> None:
    expected = {
        "CandidateBundle": forward_binding.CandidateBundle,
        "derive_label_window": forward_state.derive_label_window,
        "finalize_prediction_commit": forward_binding.finalize_prediction_commit,
        "initial_forward_state": forward_state.initial_forward_state,
        "load_candidate_bundle": forward_binding.load_candidate_bundle,
        "load_forward_state": forward_state.load_forward_state,
        "load_trading_calendar": forward_state.load_trading_calendar,
        "record_forward_failure": forward_state.record_forward_failure,
        "run_single_day_prediction": forward_prediction.run_single_day_prediction,
        "update_mature_forward_labels": forward_labels.update_mature_forward_labels,
    }
    for name, implementation in expected.items():
        assert getattr(forward_pipeline, name) is implementation


def test_forward_pipeline_is_an_import_only_facade() -> None:
    path = Path(forward_pipeline.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    definitions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert definitions == []
