"""Local job-candidate data model and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


CANDIDATE_FIELDS = frozenset(
    {
        "company",
        "culture_fit",
        "culture_fit_evidence",
        "date_found",
        "title",
        "target_role_family",
        "guaranteed_base_salary_usd",
        "commission_only",
        "requires_active_license",
        "location_category",
        "matched_required_skills",
        "posting_verified_live",
        "required_skills",
        "role_category",
        "seniority_fit",
        "seniority_fit_evidence",
        "source_url",
    }
)

FIT_RATINGS = frozenset({"strong", "acceptable", "weak", "unknown"})


class JobCandidateError(ValueError):
    """Raised when local candidate data is missing or malformed."""


@dataclass(frozen=True)
class JobCandidate:
    """Facts required to evaluate a job against the configured hard filters."""

    company: str
    culture_fit: str
    culture_fit_evidence: tuple[str, ...]
    date_found: date
    title: str
    target_role_family: str
    guaranteed_base_salary_usd: int
    commission_only: bool
    requires_active_license: bool
    location_category: str
    matched_required_skills: tuple[str, ...]
    posting_verified_live: bool
    required_skills: tuple[str, ...]
    role_category: str
    seniority_fit: str
    seniority_fit_evidence: tuple[str, ...]
    source_url: str


def load_candidate(path: str | Path) -> JobCandidate:
    """Load a candidate from a local JSON-compatible YAML file."""

    candidate_path = Path(path)
    try:
        raw_text = candidate_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JobCandidateError(f"cannot read {candidate_path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise JobCandidateError(
            f"{candidate_path} is not valid JSON-compatible YAML: "
            f"line {exc.lineno}, column {exc.colno}"
        ) from exc

    return validate_candidate(data)


def validate_candidate(data: Any) -> JobCandidate:
    """Validate parsed candidate data and return an immutable model."""

    if not isinstance(data, dict) or not all(isinstance(key, str) for key in data):
        raise JobCandidateError("candidate must be a mapping with string keys")

    actual_fields = set(data)
    missing = sorted(CANDIDATE_FIELDS - actual_fields)
    unknown = sorted(actual_fields - CANDIDATE_FIELDS)
    if missing:
        raise JobCandidateError(f"candidate is missing fields: {', '.join(missing)}")
    if unknown:
        raise JobCandidateError(f"candidate has unknown fields: {', '.join(unknown)}")

    strings = {
        field: _require_string(data[field], field)
        for field in (
            "company",
            "title",
            "target_role_family",
            "location_category",
            "role_category",
            "source_url",
        )
    }

    date_found = _require_date(data["date_found"])
    _require_url(strings["source_url"])
    required_skills = _require_string_list(data["required_skills"], "required_skills")
    matched_required_skills = _require_string_list(
        data["matched_required_skills"],
        "matched_required_skills",
        allow_empty=True,
    )
    _require_subset(
        matched_required_skills,
        required_skills,
        "matched_required_skills",
        "required_skills",
    )
    seniority_fit = _require_fit_rating(data["seniority_fit"], "seniority_fit")
    seniority_fit_evidence = _require_string_list(
        data["seniority_fit_evidence"], "seniority_fit_evidence"
    )
    culture_fit = _require_fit_rating(data["culture_fit"], "culture_fit")
    culture_fit_evidence = _require_string_list(
        data["culture_fit_evidence"], "culture_fit_evidence"
    )

    salary = data["guaranteed_base_salary_usd"]
    if type(salary) is not int or salary < 0:
        raise JobCandidateError(
            "guaranteed_base_salary_usd must be a non-negative integer"
        )

    commission_only = _require_boolean(data["commission_only"], "commission_only")
    active_license = _require_boolean(data["requires_active_license"], "requires_active_license")
    posting_verified_live = _require_boolean(
        data["posting_verified_live"], "posting_verified_live"
    )

    return JobCandidate(
        company=strings["company"],
        culture_fit=culture_fit,
        culture_fit_evidence=culture_fit_evidence,
        date_found=date_found,
        title=strings["title"],
        target_role_family=strings["target_role_family"],
        guaranteed_base_salary_usd=salary,
        commission_only=commission_only,
        requires_active_license=active_license,
        location_category=strings["location_category"],
        matched_required_skills=matched_required_skills,
        posting_verified_live=posting_verified_live,
        required_skills=required_skills,
        role_category=strings["role_category"],
        seniority_fit=seniority_fit,
        seniority_fit_evidence=seniority_fit_evidence,
        source_url=strings["source_url"],
    )


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JobCandidateError(f"{field} must be a non-empty string")
    return value.strip()


def _require_boolean(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise JobCandidateError(f"{field} must be a boolean")
    return value


def _require_date(value: Any) -> date:
    if not isinstance(value, str):
        raise JobCandidateError("date_found must be an ISO date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise JobCandidateError(
            "date_found must be an ISO date in YYYY-MM-DD format"
        ) from exc


def _require_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        raise JobCandidateError("source_url must be an absolute HTTP or HTTPS URL")


def _require_string_list(
    value: Any, field: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise JobCandidateError(f"{field} must be {qualifier}")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise JobCandidateError(f"{field} must contain only non-empty strings")

    normalized = tuple(item.strip() for item in value)
    folded = tuple(item.casefold() for item in normalized)
    if len(set(folded)) != len(folded):
        raise JobCandidateError(f"{field} cannot contain duplicates")
    return normalized


def _require_subset(
    subset: tuple[str, ...],
    superset: tuple[str, ...],
    subset_field: str,
    superset_field: str,
) -> None:
    allowed = {item.casefold() for item in superset}
    unknown = sorted(item for item in subset if item.casefold() not in allowed)
    if unknown:
        raise JobCandidateError(
            f"{subset_field} contains values not present in {superset_field}: "
            + ", ".join(unknown)
        )


def _require_fit_rating(value: Any, field: str) -> str:
    if not isinstance(value, str) or value.casefold() not in FIT_RATINGS:
        allowed = ", ".join(sorted(FIT_RATINGS))
        raise JobCandidateError(f"{field} must be one of: {allowed}")
    return value.casefold()
