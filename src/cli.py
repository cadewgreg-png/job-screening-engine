"""Command-line interface for local job-screening criteria checks."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .candidate import JobCandidate, JobCandidateError, load_candidate
from .criteria import Criteria, CriteriaError, load_criteria
from .scoring import FitScore, rank_candidates, score_candidate
from .screening import ScreeningDecision, screen_candidate, screen_candidate_batch


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "criteria.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-screening-engine",
        description="Validate criteria and screen local job records.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("validate", "screen", "screen-batch", "score", "rank-batch"),
        default="validate",
        help="operation to perform (default: validate)",
    )
    parser.add_argument(
        "candidates",
        nargs="*",
        type=Path,
        help="local candidate files for screening or scoring commands",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="path to the JSON-compatible YAML criteria file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        criteria = load_criteria(args.config)
    except CriteriaError as exc:
        print(f"Criteria validation failed: {exc}")
        return 1

    if args.command == "validate":
        if args.candidates:
            print("Criteria validation failed: validate does not accept a candidate file")
            return 1
        _print_criteria_summary(criteria, args.config)
        return 0

    if args.command in {"screen", "score"} and len(args.candidates) != 1:
        print(
            f"Candidate validation failed: {args.command} requires exactly one "
            "candidate file"
        )
        return 1
    if args.command in {"screen-batch", "rank-batch"} and not args.candidates:
        print(f"Candidate validation failed: {args.command} requires candidate files")
        return 1

    candidates = []
    try:
        for candidate_path in args.candidates:
            candidates.append(load_candidate(candidate_path))
    except JobCandidateError as exc:
        print(f"Candidate validation failed: {exc}")
        return 1

    if args.command == "screen":
        decision = screen_candidate(candidates[0], criteria)
        _print_screening_decision(candidates[0], decision)
        print("No live job search was performed.")
        return 0 if decision.accepted else 2

    if args.command == "score":
        decision = screen_candidate(candidates[0], criteria)
        if not decision.accepted:
            _print_screening_decision(candidates[0], decision)
            print("No fit score was produced for a hard-filter rejection.")
            print("No live job search was performed.")
            return 2
        _print_fit_score("SCORE", candidates[0], score_candidate(candidates[0], criteria))
        print("No live job search was performed.")
        return 0

    if args.command == "screen-batch":
        decisions = screen_candidate_batch(candidates, criteria)
        for candidate, decision in zip(candidates, decisions, strict=True):
            _print_screening_decision(candidate, decision)
        passed = sum(decision.accepted for decision in decisions)
        rejected = len(decisions) - passed
        print(f"Batch summary: {passed} passed, {rejected} rejected")
        print("No live job search was performed.")
        return 0 if rejected == 0 else 2

    assessments = rank_candidates(candidates, criteria)
    ranked = 0
    rejected = 0
    for assessment in assessments:
        if assessment.score is not None and assessment.rank is not None:
            ranked += 1
            _print_fit_score(
                f"RANK {assessment.rank}", assessment.candidate, assessment.score
            )
        else:
            rejected += 1
            _print_screening_decision(assessment.candidate, assessment.decision)
    print(f"Ranking summary: {ranked} ranked, {rejected} rejected")
    print("No live job search was performed.")
    return 0 if rejected == 0 else 2


def _print_screening_decision(
    candidate: JobCandidate, decision: ScreeningDecision
) -> None:
    outcome = "PASS" if decision.accepted else "REJECT"
    print(f"{outcome}: {candidate.company} — {candidate.title}")
    if decision.accepted:
        print("All hard criteria passed.")
    else:
        for failure in decision.failures:
            print(f"- [{failure.code}] {failure.message}")


def _print_fit_score(prefix: str, candidate: JobCandidate, score: FitScore) -> None:
    print(
        f"{prefix}: {score.total:.1f} [{score.band}] — "
        f"{candidate.company} — {candidate.title}"
    )
    print(f"- Required skills: {score.required_skills:.1f}")
    print(f"- Seniority: {score.seniority:.1f}")
    print(f"- Compensation: {score.compensation:.1f}")
    print(f"- Location/culture: {score.location_culture:.1f}")


def _print_criteria_summary(criteria: Criteria, _config_path: Path) -> None:
    print("Criteria valid.")
    print(f"Target role families: {len(criteria.target_roles)}")
    print("Guaranteed base salary floor: configured")
    print(f"Allowed locations: {len(criteria.allowed_locations)} configured")
    print("No live job search was performed.")
