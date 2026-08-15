"""Transparent, evidence-backed fit scoring for screened candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .candidate import JobCandidate
from .criteria import Criteria
from .screening import ScreeningDecision, screen_candidate, screen_candidate_batch


SCORE_WEIGHTS = {
    "required_skills": 0.40,
    "seniority": 0.20,
    "compensation": 0.20,
    "location_culture": 0.20,
}

FIT_RATING_SCORES = {
    "strong": 100.0,
    "acceptable": 70.0,
    "weak": 30.0,
    "unknown": 0.0,
}

COMPENSATION_AT_FLOOR_SCORE = 70.0
COMPENSATION_FULL_SCORE_MULTIPLIER = 1.20
LOCATION_SHARE = 0.60
CULTURE_SHARE = 0.40


class ScoringError(ValueError):
    """Raised when a candidate cannot be scored safely."""


@dataclass(frozen=True)
class FitScore:
    """Weighted fit score with visible component values."""

    required_skills: float
    seniority: float
    compensation: float
    location_culture: float
    total: float
    band: str


@dataclass(frozen=True)
class RankedAssessment:
    """A candidate's screening decision and optional ranked fit score."""

    candidate: JobCandidate
    decision: ScreeningDecision
    score: FitScore | None
    rank: int | None


def score_candidate(candidate: JobCandidate, criteria: Criteria) -> FitScore:
    """Score one candidate only after every hard filter passes."""

    decision = screen_candidate(candidate, criteria)
    if not decision.accepted:
        codes = ", ".join(decision.failure_codes)
        raise ScoringError(f"candidate failed hard screening: {codes}")

    required_skills = _required_skills_score(candidate)
    seniority = FIT_RATING_SCORES[candidate.seniority_fit]
    compensation = _compensation_score(candidate, criteria)
    location_culture = _location_culture_score(candidate, criteria)
    total = round(
        required_skills * SCORE_WEIGHTS["required_skills"]
        + seniority * SCORE_WEIGHTS["seniority"]
        + compensation * SCORE_WEIGHTS["compensation"]
        + location_culture * SCORE_WEIGHTS["location_culture"],
        1,
    )

    return FitScore(
        required_skills=round(required_skills, 1),
        seniority=round(seniority, 1),
        compensation=round(compensation, 1),
        location_culture=round(location_culture, 1),
        total=total,
        band=_score_band(total),
    )


def rank_candidates(
    candidates: Iterable[JobCandidate], criteria: Criteria
) -> tuple[RankedAssessment, ...]:
    """Screen, score, and rank accepted candidates; retain rejected candidates."""

    candidate_list = tuple(candidates)
    decisions = screen_candidate_batch(candidate_list, criteria)
    scored: list[tuple[int, JobCandidate, ScreeningDecision, FitScore]] = []
    rejected: list[RankedAssessment] = []

    for index, (candidate, decision) in enumerate(
        zip(candidate_list, decisions, strict=True)
    ):
        if decision.accepted:
            scored.append((index, candidate, decision, score_candidate(candidate, criteria)))
        else:
            rejected.append(
                RankedAssessment(
                    candidate=candidate,
                    decision=decision,
                    score=None,
                    rank=None,
                )
            )

    scored.sort(
        key=lambda item: (
            -item[3].total,
            item[1].company.casefold(),
            item[1].title.casefold(),
            item[0],
        )
    )
    ranked = tuple(
        RankedAssessment(
            candidate=candidate,
            decision=decision,
            score=score,
            rank=rank,
        )
        for rank, (_, candidate, decision, score) in enumerate(scored, start=1)
    )
    return ranked + tuple(rejected)


def _required_skills_score(candidate: JobCandidate) -> float:
    return 100.0 * len(candidate.matched_required_skills) / len(
        candidate.required_skills
    )


def _compensation_score(candidate: JobCandidate, criteria: Criteria) -> float:
    floor = criteria.minimum_guaranteed_base_salary_usd
    full_score_salary = floor * COMPENSATION_FULL_SCORE_MULTIPLIER
    progress = (candidate.guaranteed_base_salary_usd - floor) / (
        full_score_salary - floor
    )
    bounded_progress = min(max(progress, 0.0), 1.0)
    return COMPENSATION_AT_FLOOR_SCORE + bounded_progress * (
        100.0 - COMPENSATION_AT_FLOOR_SCORE
    )


def _location_culture_score(candidate: JobCandidate, criteria: Criteria) -> float:
    location_score = 100.0 if candidate.location_category in criteria.allowed_locations else 0.0
    culture_score = FIT_RATING_SCORES[candidate.culture_fit]
    return location_score * LOCATION_SHARE + culture_score * CULTURE_SHARE


def _score_band(total: float) -> str:
    if total >= 85.0:
        return "strong"
    if total >= 70.0:
        return "competitive"
    return "marginal"
