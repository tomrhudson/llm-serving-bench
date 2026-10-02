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
            hardware = (
                f'{model["dgx_spark_count"]} systems / '
                f'{model["dgx_spark_count"]} GPUs · '
                f'{model["dgx_spark_memory_gb_each"]}GB each'
            )
            self.assertIn(hardware, guide)
            selected = baselines[model["tested_choice"]]
            self.assertEqual(selected["model_id"], model["id"])
            self.assertIn(f']({selected["report"]})', guide)

    def test_summary_names_dgx_spark_memory_per_system(self) -> None:
        summary = (ROOT / "results/README.md").read_text()
        self.assertIn("2x NVIDIA DGX Spark (128GB each)", summary)


if __name__ == "__main__":
    unittest.main()
