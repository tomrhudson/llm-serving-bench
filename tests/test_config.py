import json
import unittest
from pathlib import Path


class ConfigTests(unittest.TestCase):
    def test_standard_suite_has_unique_scenarios_and_safe_canary_budgets(self):
        root = Path(__file__).resolve().parents[1]
        suite = json.loads(
            (root / "configs" / "qwen-native-standard.json").read_text()
        )
        names = [scenario["name"] for scenario in suite["scenarios"]]
        self.assertEqual(len(names), len(set(names)))
        for scenario in suite["scenarios"]:
            if scenario.get("kind") == "canary":
                self.assertTrue(
                    all(case["output_tokens"] >= 128 for case in scenario["cases"])
                )


if __name__ == "__main__":
    unittest.main()
