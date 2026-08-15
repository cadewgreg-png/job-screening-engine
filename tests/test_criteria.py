from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.criteria import CriteriaError, load_criteria, validate_criteria


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "config" / "criteria.yaml"


class CriteriaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_repository_config_loads(self) -> None:
        criteria = load_criteria(CONFIG_PATH)

        self.assertEqual(criteria.minimum_guaranteed_base_salary_usd, 60_000)
        self.assertEqual(len(criteria.target_roles), 3)
        self.assertTrue(criteria.exclude_commission_only)
        self.assertTrue(criteria.exclude_active_license_required)

    def test_rejects_negative_salary_floor(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["minimum_guaranteed_base_salary_usd"] = -1

        with self.assertRaisesRegex(CriteriaError, "non-negative integer"):
            validate_criteria(data)

    def test_rejects_nonboolean_license_exclusion(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["excluded_role_attributes"]["requires_active_license"] = "yes"

        with self.assertRaisesRegex(CriteriaError, "must be a boolean"):
            validate_criteria(data)

    def test_rejects_empty_target_roles(self) -> None:
        data = copy.deepcopy(self.valid_data)
        data["target_roles"] = []

        with self.assertRaisesRegex(CriteriaError, "non-empty list"):
            validate_criteria(data)

    def test_rejects_malformed_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "criteria.yaml"
            path.write_text("not: [valid", encoding="utf-8")

            with self.assertRaisesRegex(CriteriaError, "JSON-compatible YAML"):
                load_criteria(path)


if __name__ == "__main__":
    unittest.main()
