"""Deterministic hard-filter screening for local job candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from .candidate import JobCandidate
from .criteria import Criteria


@dataclass(frozen=True)
class ScreeningFailure:
    """One stable, explainable reason a candidate failed screening."""

    code: str
    message: str


@dataclass(frozen=True)
class ScreeningDecision:
    """The complete hard-filter decision for one candidate."""

    failures: tuple[ScreeningFailure, ...]

    @property
    def accepted(self) -> bool:
        return not self.failures

    @property
    def failure_codes(self) -> tuple[str, ...]:
        return tuple(failure.code for failure in self.failures)


def screen_candidate(candidate: JobCandidate, criteria: Criteria) -> ScreeningDecision:
    """Evaluate every hard filter and return all rejection reasons."""

    failures: list[ScreeningFailure] = []

    if candidate.target_role_family not in criteria.target_roles:
        failures.append(
            ScreeningFailure(
                "target_role",
                f"Role family is not approved: {candidate.target_role_family}",
            )
        )

    if (
        candidate.guaranteed_base_salary_usd
        < criteria.minimum_guaranteed_base_salary_usd
    ):
        failures.append(
            ScreeningFailure(
                "base_salary",
                "Guaranteed base salary "
                f"${candidate.guaranteed_base_salary_usd:,} is below the "
                f"${criteria.minimum_guaranteed_base_salary_usd:,} floor",
            )
        )

    if criteria.exclude_commission_only and candidate.commission_only:
        failures.append(
            ScreeningFailure("commission_only", "Commission-only roles are excluded")
        )

    if (
        criteria.exclude_active_license_required
        and candidate.requires_active_license
    ):
        failures.append(
            ScreeningFailure(
                "active_license",
                "Roles requiring an active license are excluded",
            )
        )

    if candidate.location_category not in criteria.allowed_locations:
        failures.append(
            ScreeningFailure(
                "location",
                f"Location category is not allowed: {candidate.location_category}",
            )
        )

    if not candidate.posting_verified_live:
        failures.append(
            ScreeningFailure(
                "posting_live",
                "The posting has not been explicitly verified as live",
            )
        )

    excluded_title = _find_excluded_title(
        candidate.title, criteria.excluded_seniority_titles
    )
    if excluded_title is not None:
        failures.append(
            ScreeningFailure(
                "seniority",
                f"Title contains excluded seniority: {excluded_title}",
            )
        )

    excluded_categories = {
        category.casefold(): category for category in criteria.excluded_role_categories
    }
    matched_category = excluded_categories.get(candidate.role_category.casefold())
    if matched_category is not None:
        failures.append(
            ScreeningFailure(
                "role_category",
                f"Role category is excluded: {matched_category}",
            )
        )

    return ScreeningDecision(failures=tuple(failures))


def screen_candidate_batch(
    candidates: Iterable[JobCandidate], criteria: Criteria
) -> tuple[ScreeningDecision, ...]:
    """Screen candidates in order and flag repeated sources or job identities."""

    decisions: list[ScreeningDecision] = []
    seen_urls: dict[str, int] = {}
    seen_identities: dict[tuple[str, str, str], int] = {}

    for index, candidate in enumerate(candidates):
        decision = screen_candidate(candidate, criteria)
        failures = list(decision.failures)
        canonical_url = _canonical_source_url(candidate.source_url)
        identity = _candidate_identity(candidate)

        duplicate_of = seen_urls.get(canonical_url)
        if duplicate_of is None:
            duplicate_of = seen_identities.get(identity)

        if duplicate_of is not None:
            failures.append(
                ScreeningFailure(
                    "duplicate",
                    f"Duplicates candidate {duplicate_of + 1} in this batch",
                )
            )
        else:
            seen_urls[canonical_url] = index
            seen_identities[identity] = index

        decisions.append(ScreeningDecision(failures=tuple(failures)))

    return tuple(decisions)


def _find_excluded_title(title: str, exclusions: tuple[str, ...]) -> str | None:
    for exclusion in exclusions:
        patterns = [rf"\b{re.escape(exclusion)}\b"]
        if exclusion.casefold() == "vp":
            patterns.append(r"\bvice\s+president\b")
        if any(re.search(pattern, title, flags=re.IGNORECASE) for pattern in patterns):
            return exclusion
    return None


def _canonical_source_url(source_url: str) -> str:
    parsed = urlsplit(source_url)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (parsed.scheme.casefold(), parsed.netloc.casefold(), path, parsed.query, "")
    )


def _candidate_identity(candidate: JobCandidate) -> tuple[str, str, str]:
    return (
        _normalize_identity_part(candidate.company),
        _normalize_identity_part(candidate.title),
        _normalize_identity_part(candidate.location_category),
    )


def _normalize_identity_part(value: str) -> str:
    return " ".join(value.casefold().split())
