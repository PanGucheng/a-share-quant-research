from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class ProfileType(str, Enum):
    SMOKE = "smoke"
    REFERENCE = "reference"
    FULL_RESEARCH = "full_research"


PROFILE_NAME_TYPES: dict[str, ProfileType] = {
    "synthetic_smoke": ProfileType.SMOKE,
    "local_smoke": ProfileType.SMOKE,
    "local_reference": ProfileType.REFERENCE,
    "gated_reference": ProfileType.REFERENCE,
    "full_research": ProfileType.FULL_RESEARCH,
}


@dataclass(frozen=True)
class Profile:
    name: str
    type: ProfileType

    def as_dict(self) -> dict[str, str]:
        return {"profile_name": self.name, "profile_type": self.type.value}


def resolve_profile(config: Mapping[str, Any], *, require_explicit_type: bool = True) -> Profile:
    legacy_name = config.get("profile")
    profile_name = config.get("profile_name", legacy_name)
    if not profile_name:
        raise ValueError("configuration must define profile_name")
    if legacy_name is not None and str(legacy_name) != str(profile_name):
        raise ValueError("legacy profile must equal profile_name during the compatibility window")

    explicit_type = config.get("profile_type")
    inferred_type = PROFILE_NAME_TYPES.get(str(profile_name))
    if explicit_type is None:
        if require_explicit_type:
            raise ValueError("configuration must explicitly define profile_type")
        if inferred_type is None:
            raise ValueError(f"cannot infer profile_type for profile_name={profile_name!r}")
        profile_type = inferred_type
    else:
        try:
            profile_type = ProfileType(str(explicit_type))
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ProfileType)
            raise ValueError(f"invalid profile_type={explicit_type!r}; expected one of {allowed}") from exc

    if inferred_type is not None and inferred_type != profile_type:
        raise ValueError(
            f"profile_name={profile_name!r} implies {inferred_type.value!r}, not {profile_type.value!r}"
        )
    return Profile(str(profile_name), profile_type)


def profile_mix_status(profiles: Iterable[Profile]) -> str:
    types = {profile.type for profile in profiles}
    if not types:
        return "empty"
    if len(types) == 1:
        return "homogeneous"
    if types <= {ProfileType.SMOKE, ProfileType.REFERENCE}:
        return "reference_only"
    return "incompatible"


def incompatible_profiles(profiles: Iterable[Profile], gate: str) -> list[Profile]:
    values = list(profiles)
    if gate == "smoke":
        allowed = {ProfileType.SMOKE}
    elif gate == "reference":
        allowed = {ProfileType.SMOKE, ProfileType.REFERENCE}
    elif gate in {"full_research", "core_model", "model_comparison"}:
        allowed = {ProfileType.FULL_RESEARCH}
    else:
        raise ValueError(f"unknown profile gate: {gate}")
    return [profile for profile in values if profile.type not in allowed]


def assert_profiles_compatible(profiles: Iterable[Profile], gate: str) -> None:
    values = list(profiles)
    rejected = incompatible_profiles(values, gate)
    if rejected:
        detail = ", ".join(f"{item.name}:{item.type.value}" for item in rejected)
        raise ValueError(f"profile gate {gate!r} rejected: {detail}")
    if gate in {"full_research", "core_model", "model_comparison"} and profile_mix_status(values) != "homogeneous":
        raise ValueError(f"profile gate {gate!r} requires one homogeneous full_research profile")
