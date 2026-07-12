from __future__ import annotations


def test_research_validation_imports() -> None:
    import research_validation
    from research_validation import schemas

    assert callable(research_validation.validate_factor_frame)
    assert callable(schemas.validate_universe_intervals)
