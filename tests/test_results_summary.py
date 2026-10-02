import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ResultsSummaryTests(unittest.TestCase):
    def test_generated_results_summary_is_current(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/generate_results_summary.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_model_guide_covers_every_catalog_family(self) -> None:
        catalog = json.loads((ROOT / "results/catalog.json").read_text())
        guide = (ROOT / "results/MODEL-GUIDE.md").read_text()
        baselines = {item["id"]: item for item in catalog["baselines"]}

        for model in catalog["models"]:
            self.assertIn(f'<a id="{model["id"]}"></a>', guide)
            self.assertIn(f'## {model["name"]}', guide)
            selected = baselines[model["tested_choice"]]
            self.assertEqual(selected["model_id"], model["id"])
            self.assertIn(f']({selected["report"]})', guide)


if __name__ == "__main__":
    unittest.main()
