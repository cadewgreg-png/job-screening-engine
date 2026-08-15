from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from src.candidate import JobCandidateError, validate_candidate
from src.criteria import load_criteria
from src.screening import screen_candidate, screen_candidate_batch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "config" / "criteria.yaml"
SAMPLE_PATH = REPOSITORY_ROOT / "examples" / "sample-job.json"


class ScreeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.criteria = load_criteria(CONFIG_PATH)
        self.valid_data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))

    def test_valid_candidate_passes(self) -> None:
        decision = screen_candidate(
            validate_candidate(self.valid_data), self.criteria
        )

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.failure_codes, ())

    def test_each_hard_filter_has_an_explainable_failure(self) -> None:
        cases = {
            "target_role": {
                "target_role_family": "Enterprise Software Sales Engineer"
            },
            "base_salary": {"guaranteed_base_salary_usd": 59_999},
            "commission_only": {"commission_only": True},
            "active_license": {"requires_active_license": True},
            "location": {"location_category": "Onsite"},
            "posting_live": {"posting_verified_live": False},
            "seniority": {"title": "Director of Relationship Management"},
            "role_category": {
                "role_category": "Door-to-door sales"
            },
        }

        for expected_code, changes in cases.items():
            with self.subTest(expected_code=expected_code):
                data = copy.deepcopy(self.valid_data)
                data.update(changes)
                decision = screen_candidate(validate_candidate(data), self.criteria)

                self.assertFalse(decision.accepted)
                self.assertIn(expected_code, decision.failure_codes)

    def test_reports_all_failures_in_one_decision(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data.update(
            {
                "title": "Executive Account Lead",
                "guaranteed_base_salary_usd": 50_000,
                "commission_only": True,
            }
        )

        decision = screen_candidate(validate_candidate(data), self.criteria)

        self.assertEqual(
            decision.failure_codes,
            ("base_salary", "commission_only", "seniority"),
        )

    def test_excluded_title_is_detected_case_insensitively(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["title"] = "director of customer success"

        decision = screen_candidate(validate_candidate(data), self.criteria)

        self.assertIn("seniority", decision.failure_codes)

    def test_candidate_schema_rejects_unknown_fields(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["fit_score"] = 100

        with self.assertRaisesRegex(JobCandidateError, "unknown fields: fit_score"):
            validate_candidate(data)

    def test_candidate_parses_date_found(self) -> None:
        candidate = validate_candidate(self.valid_data)

        self.assertEqual(candidate.date_found.isoformat(), "2026-08-15")

    def test_candidate_rejects_invalid_date_found(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["date_found"] = "08/15/2026"

        with self.assertRaisesRegex(JobCandidateError, "YYYY-MM-DD"):
            validate_candidate(data)

    def test_candidate_rejects_relative_source_url(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["source_url"] = "/jobs/relationship-manager"

        with self.assertRaisesRegex(JobCandidateError, "absolute HTTP or HTTPS"):
            validate_candidate(data)

    def test_batch_rejects_duplicate_source_url(self) -> None:
        first = validate_candidate(self.valid_data)
        duplicate_data = copy.deepcopy(self.valid_data)
        duplicate_data["company"] = "Different Display Name"
        duplicate = validate_candidate(duplicate_data)

        decisions = screen_candidate_batch((first, duplicate), self.criteria)

        self.assertTrue(decisions[0].accepted)
        self.assertIn("duplicate", decisions[1].failure_codes)

    def test_batch_rejects_normalized_identity_duplicate(self) -> None:
        first = validate_candidate(self.valid_data)
        duplicate_data = copy.deepcopy(self.valid_data)
        duplicate_data["company"] = "  EXAMPLE   COMPANY "
        duplicate_data["title"] = "customer success manager"
        duplicate_data["source_url"] = "https://jobs.example.org/alternate-source"
        duplicate = validate_candidate(duplicate_data)

        decisions = screen_candidate_batch((first, duplicate), self.criteria)

        self.assertTrue(decisions[0].accepted)
        self.assertIn("duplicate", decisions[1].failure_codes)

    def test_matched_skills_must_come_from_required_skills(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["matched_required_skills"].append("Unsupported skill")

        with self.assertRaisesRegex(JobCandidateError, "Unsupported skill"):
            validate_candidate(data)

    def test_fit_rating_rejects_unknown_label(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["seniority_fit"] = "excellent"

        with self.assertRaisesRegex(JobCandidateError, "seniority_fit must be one of"):
            validate_candidate(data)

    def test_fit_rating_requires_explanatory_evidence(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["culture_fit_evidence"] = []

        with self.assertRaisesRegex(JobCandidateError, "non-empty list"):
            validate_candidate(data)


if __name__ == "__main__":
    unittest.main()
