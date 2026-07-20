from __future__ import annotations

import pytest

from research_validation.profiles import (
    Profile,
    ProfileType,
    assert_profiles_compatible,
    profile_mix_status,
    resolve_profile,
)


def test_profile_type_is_explicit_and_consistent() -> None:
    profile = resolve_profile({"profile": "local_reference", "profile_name": "local_reference", "profile_type": "reference"})
    assert profile == Profile("local_reference", ProfileType.REFERENCE)
    with pytest.raises(ValueError, match="explicitly define"):
        resolve_profile({"profile": "local_reference"})
    with pytest.raises(ValueError, match="implies"):
        resolve_profile({"profile": "local_reference", "profile_type": "full_research"})


def test_reference_gate_allows_controlled_smoke_reference_mix() -> None:
    profiles = [Profile("local_smoke", ProfileType.SMOKE), Profile("local_reference", ProfileType.REFERENCE)]
    assert_profiles_compatible(profiles, "reference")
    assert profile_mix_status(profiles) == "reference_only"


def test_full_and_core_gates_reject_reference_artifacts() -> None:
    profiles = [Profile("local_reference", ProfileType.REFERENCE)]
    with pytest.raises(ValueError, match="rejected"):
        assert_profiles_compatible(profiles, "full_research")
    with pytest.raises(ValueError, match="rejected"):
        assert_profiles_compatible(profiles, "core_model")
