"""Configurable, local-first job screening and fit scoring."""

from .candidate import JobCandidate, JobCandidateError, load_candidate
from .criteria import Criteria, CriteriaError, load_criteria
from .screening import (
    ScreeningDecision,
    ScreeningFailure,
    screen_candidate,
    screen_candidate_batch,
)
from .scoring import (
    FitScore,
    RankedAssessment,
    ScoringError,
    rank_candidates,
    score_candidate,
)

__all__ = [
    "Criteria",
    "CriteriaError",
    "JobCandidate",
    "JobCandidateError",
    "FitScore",
    "RankedAssessment",
    "ScoringError",
    "ScreeningDecision",
    "ScreeningFailure",
    "load_candidate",
    "load_criteria",
    "screen_candidate",
    "screen_candidate_batch",
    "rank_candidates",
    "score_candidate",
]
