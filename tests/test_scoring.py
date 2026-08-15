from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from src.candidate import validate_candidate
from src.criteria import load_criteria
from src.scoring import SCORE_WEIGHTS, ScoringError, rank_candidates, score_candidate


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "config" / "criteria.yaml"
SAMPLE_PATH = REPOSITORY_ROOT / "examples" / "sample-job.json"


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.criteria = load_criteria(CONFIG_PATH)
        self.valid_data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))

    def test_score_weights_total_one(self) -> None:
        self.assertEqual(sum(SCORE_WEIGHTS.values()), 1.0)

    def test_sample_score_exposes_all_weighted_components(self) -> None:
        score = score_candidate(validate_candidate(self.valid_data), self.criteria)

        self.assertEqual(score.required_skills, 100.0)
        self.assertEqual(score.seniority, 100.0)
        self.assertEqual(score.compensation, 100.0)
        self.assertEqual(score.location_culture, 88.0)
        self.assertEqual(score.total, 97.6)
        self.assertEqual(score.band, "strong")

    def test_compensation_scores_seventy_at_floor(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["guaranteed_base_salary_usd"] = 60_000

        score = score_candidate(validate_candidate(data), self.criteria)

        self.assertEqual(score.compensation, 70.0)

    def test_compensation_score_caps_at_one_hundred(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["guaranteed_base_salary_usd"] = 150_000

        score = score_candidate(validate_candidate(data), self.criteria)

        self.assertEqual(score.compensation, 100.0)

    def test_unknown_fit_ratings_do_not_receive_assumed_credit(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data.update(
            {
                "seniority_fit": "unknown",
                "seniority_fit_evidence": ["The posting does not state a level"],
                "culture_fit": "unknown",
                "culture_fit_evidence": ["No culture evidence has been reviewed"],
            }
        )

        score = score_candidate(validate_candidate(data), self.criteria)

        self.assertEqual(score.seniority, 0.0)
        self.assertEqual(score.location_culture, 60.0)
        self.assertEqual(score.band, "competitive")

    def test_hard_filter_rejection_cannot_be_scored(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["commission_only"] = True

        with self.assertRaisesRegex(ScoringError, "commission_only"):
            score_candidate(validate_candidate(data), self.criteria)

    def test_ranking_sorts_scores_and_leaves_duplicates_unscored(self) -> None:
        strongest = validate_candidate(self.valid_data)

        second_data = copy.deepcopy(self.valid_data)
        second_data.update(
            {
                "company": "Another Company",
                "title": "Account Manager",
                "source_url": "https://careers.example.org/jobs/client-relationships",
                "matched_required_skills": ["Account management"],
                "seniority_fit": "acceptable",
                "seniority_fit_evidence": ["The role is within the target level"],
            }
        )
        second = validate_candidate(second_data)
        duplicate = validate_candidate(copy.deepcopy(self.valid_data))

        assessments = rank_candidates(
            (second, duplicate, strongest),
            self.criteria,
        )

        self.assertEqual(assessments[0].candidate.company, "Example Company")
        self.assertEqual(assessments[0].rank, 1)
        self.assertIsNotNone(assessments[0].score)
        self.assertEqual(assessments[1].candidate.company, "Another Company")
        self.assertEqual(assessments[1].rank, 2)
        self.assertIsNotNone(assessments[1].score)
        self.assertIsNone(assessments[2].rank)
        self.assertIsNone(assessments[2].score)
        self.assertIn("duplicate", assessments[2].decision.failure_codes)


if __name__ == "__main__":
    unittest.main()
