"""Research-grade model protocol primitives.

This package intentionally contains no model trainer.  PR #5A freezes and
validates inputs, preprocessing, metrics, lineage, and release contracts only.
"""

from .gates import (
    ModelScopeBlockedError,
    assert_research_model_entry_artifact,
    assert_research_model_entry_file,
    assert_model_scope_allowed,
    model_scope_blockers,
)

__all__ = [
    "ModelScopeBlockedError",
    "assert_research_model_entry_artifact",
    "assert_research_model_entry_file",
    "assert_model_scope_allowed",
    "model_scope_blockers",
]
