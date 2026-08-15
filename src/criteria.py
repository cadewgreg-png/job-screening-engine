"""Load and validate configurable job-screening criteria."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOP_LEVEL_FIELDS = frozenset(
    {
        "version",
        "target_roles",
        "minimum_guaranteed_base_salary_usd",
        "allowed_locations",
        "excluded_role_attributes",
    }
)

EXCLUSION_FIELDS = frozenset(
    {
        "commission_only",
        "requires_active_license",
        "seniority_titles",
        "role_categories",
    }
)


class CriteriaError(ValueError):
    """Raised when the criteria file is missing or malformed."""


@dataclass(frozen=True)
class Criteria:
    """Validated hard criteria used for deterministic screening."""

    version: int
    target_roles: tuple[str, ...]
    minimum_guaranteed_base_salary_usd: int
    allowed_locations: tuple[str, ...]
    exclude_commission_only: bool
    exclude_active_license_required: bool
    excluded_seniority_titles: tuple[str, ...]
    excluded_role_categories: tuple[str, ...]


def load_criteria(path: str | Path) -> Criteria:
    """Load JSON-compatible YAML from *path* and validate its schema."""

    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CriteriaError(f"cannot read {config_path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CriteriaError(
            f"{config_path} is not valid JSON-compatible YAML: "
            f"line {exc.lineno}, column {exc.colno}"
        ) from exc

    return validate_criteria(data)


def validate_criteria(data: Any) -> Criteria:
    """Validate parsed configuration data and return an immutable model."""

    root = _require_mapping(data, "criteria")
    _require_exact_fields(root, TOP_LEVEL_FIELDS, "criteria")

    version = root["version"]
    if type(version) is not int or version != 1:
        raise CriteriaError("criteria.version must be the integer 1")

    target_roles = _require_string_list(root["target_roles"], "target_roles")

    salary = root["minimum_guaranteed_base_salary_usd"]
    if type(salary) is not int or salary < 0:
        raise CriteriaError(
            "minimum_guaranteed_base_salary_usd must be a non-negative integer"
        )

    locations = _require_string_list(root["allowed_locations"], "allowed_locations")

    exclusions = _require_mapping(
        root["excluded_role_attributes"], "excluded_role_attributes"
    )
    _require_exact_fields(exclusions, EXCLUSION_FIELDS, "excluded_role_attributes")

    exclude_commission_only = _require_boolean(
        exclusions["commission_only"], "excluded_role_attributes.commission_only"
    )
    exclude_active_license = _require_boolean(
        exclusions["requires_active_license"],
        "excluded_role_attributes.requires_active_license",
    )

    seniority = _require_string_list(
        exclusions["seniority_titles"], "excluded_role_attributes.seniority_titles"
    )

    categories = _require_string_list(
        exclusions["role_categories"], "excluded_role_attributes.role_categories"
    )
    return Criteria(
        version=version,
        target_roles=target_roles,
        minimum_guaranteed_base_salary_usd=salary,
        allowed_locations=locations,
        exclude_commission_only=exclude_commission_only,
        exclude_active_license_required=exclude_active_license,
        excluded_seniority_titles=seniority,
        excluded_role_categories=categories,
    )


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CriteriaError(f"{field} must be a mapping with string keys")
    return value


def _require_exact_fields(
    mapping: dict[str, Any], expected: frozenset[str], field: str
) -> None:
    actual = set(mapping)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise CriteriaError(f"{field} is missing fields: {', '.join(missing)}")
    if unknown:
        raise CriteriaError(f"{field} has unknown fields: {', '.join(unknown)}")


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CriteriaError(f"{field} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise CriteriaError(f"{field} must contain only non-empty strings")

    normalized = tuple(item.strip() for item in value)
    if len(set(normalized)) != len(normalized):
        raise CriteriaError(f"{field} cannot contain duplicates")
    return normalized


def _require_boolean(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise CriteriaError(f"{field} must be a boolean")
    return value
