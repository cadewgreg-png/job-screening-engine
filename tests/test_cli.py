from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.cli import main


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_default_config_validates_without_searching(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["validate"])

        self.assertEqual(exit_code, 0)
        summary = output.getvalue()
        self.assertIn("Criteria valid.", summary)
        self.assertIn("Guaranteed base salary floor: configured", summary)
        self.assertIn("Allowed locations: 2 configured", summary)
        self.assertIn("No live job search was performed.", summary)
        self.assertNotIn("$60,000", summary)
        self.assertNotIn("Remote (United States)", summary)
        self.assertNotIn(str(REPOSITORY_ROOT), summary)

    def test_missing_config_returns_failure(self) -> None:
        output = io.StringIO()
        missing = REPOSITORY_ROOT / "config" / "missing.yaml"

        with contextlib.redirect_stdout(output):
            exit_code = main(["validate", "--config", str(missing)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Criteria validation failed:", output.getvalue())

    def test_sample_candidate_passes(self) -> None:
        output = io.StringIO()
        candidate = REPOSITORY_ROOT / "examples" / "sample-job.json"

        with contextlib.redirect_stdout(output):
            exit_code = main(["screen", str(candidate)])

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "PASS: Example Company — Customer Success Manager", output.getvalue()
        )
        self.assertIn("All hard criteria passed.", output.getvalue())

    def test_screen_requires_candidate_file(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["screen"])

        self.assertEqual(exit_code, 1)
        self.assertIn("screen requires exactly one candidate file", output.getvalue())

    def test_rejected_candidate_returns_exit_code_two(self) -> None:
        sample = REPOSITORY_ROOT / "examples" / "sample-job.json"
        candidate_data = json.loads(sample.read_text(encoding="utf-8"))
        candidate_data["guaranteed_base_salary_usd"] = 50_000
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.json"
            candidate.write_text(json.dumps(candidate_data), encoding="utf-8")
            with contextlib.redirect_stdout(output):
                exit_code = main(["screen", str(candidate)])

        self.assertEqual(exit_code, 2)
        self.assertIn(
            "REJECT: Example Company — Customer Success Manager", output.getvalue()
        )
        self.assertIn("[base_salary]", output.getvalue())

    def test_batch_rejects_duplicate_candidate(self) -> None:
        sample = REPOSITORY_ROOT / "examples" / "sample-job.json"
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["screen-batch", str(sample), str(sample)])

        self.assertEqual(exit_code, 2)
        self.assertIn("[duplicate] Duplicates candidate 1", output.getvalue())
        self.assertIn("Batch summary: 1 passed, 1 rejected", output.getvalue())

    def test_batch_requires_candidate_files(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["screen-batch"])

        self.assertEqual(exit_code, 1)
        self.assertIn("screen-batch requires candidate files", output.getvalue())

    def test_sample_candidate_scores(self) -> None:
        sample = REPOSITORY_ROOT / "examples" / "sample-job.json"
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["score", str(sample)])

        self.assertEqual(exit_code, 0)
        self.assertIn("SCORE: 97.6 [strong]", output.getvalue())
        self.assertIn("Required skills: 100.0", output.getvalue())

    def test_hard_rejection_is_not_scored(self) -> None:
        sample = REPOSITORY_ROOT / "examples" / "sample-job.json"
        candidate_data = json.loads(sample.read_text(encoding="utf-8"))
        candidate_data["commission_only"] = True
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.json"
            candidate.write_text(json.dumps(candidate_data), encoding="utf-8")
            with contextlib.redirect_stdout(output):
                exit_code = main(["score", str(candidate)])

        self.assertEqual(exit_code, 2)
        self.assertIn("[commission_only]", output.getvalue())
        self.assertIn("No fit score was produced", output.getvalue())

    def test_rank_batch_keeps_duplicate_unscored(self) -> None:
        sample = REPOSITORY_ROOT / "examples" / "sample-job.json"
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["rank-batch", str(sample), str(sample)])

        self.assertEqual(exit_code, 2)
        self.assertIn("RANK 1: 97.6 [strong]", output.getvalue())
        self.assertIn("[duplicate]", output.getvalue())
        self.assertIn("Ranking summary: 1 ranked, 1 rejected", output.getvalue())


if __name__ == "__main__":
    unittest.main()
