"""Research-grade model protocol primitives.

PR #5A freezes and validates inputs, preprocessing, metrics, lineage, and
release contracts. PR #5B adds scoped research-only linear model trainers.
"""

from .gates import (
    ModelScopeBlockedError,
    assert_research_model_entry_artifact,
    assert_research_model_entry_file,
    assert_model_scope_allowed,
    model_scope_blockers,
)
from .linear_models import load_linear_config, run_solver_canary

__all__ = [
    "ModelScopeBlockedError",
    "assert_research_model_entry_artifact",
    "assert_research_model_entry_file",
    "assert_model_scope_allowed",
    "model_scope_blockers",
    "load_linear_config",
    "run_solver_canary",
]
