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
        from scripts.generate_results_summary import _fmt_dgx_spark

        catalog = json.loads((ROOT / "results/catalog.json").read_text())
        guide = (ROOT / "results/MODEL-GUIDE.md").read_text()
        baselines = {item["id"]: item for item in catalog["baselines"]}

        for model in catalog["models"]:
            self.assertIn(f'<a id="{model["id"]}"></a>', guide)
            self.assertIn(f'## {model["name"]}', guide)
            hardware = _fmt_dgx_spark(model)
            self.assertIn(hardware, guide)
            selected = baselines[model["tested_choice"]]
            self.assertEqual(selected["model_id"], model["id"])
            self.assertIn(f']({selected["report"]})', guide)
            self.assertIn(model["benchmarked_source"], guide)
            self.assertIn(model["upstream_source"], guide)
            self.assertIn(model["alternative_source"], guide)

    def test_checkpoint_sources_cover_every_catalog_family(self) -> None:
        catalog = json.loads((ROOT / "results/catalog.json").read_text())
        summary = (ROOT / "results/README.md").read_text()

        self.assertIn("## Model checkpoints", summary)
        self.assertIn("not published benchmark results", summary)
        for model in catalog["models"]:
            self.assertIn(model["benchmarked_source"], summary)
            self.assertIn(model["upstream_source"], summary)
            self.assertIn(model["alternative_source"], summary)

    def test_summary_names_dgx_spark_memory_per_system(self) -> None:
        summary = (ROOT / "results/README.md").read_text()
        self.assertIn("2x NVIDIA DGX Spark (128GB each)", summary)

    def test_single_system_footprint_uses_singular_grammar(self) -> None:
        from scripts.generate_results_summary import _fmt_dgx_spark

        self.assertEqual(
            _fmt_dgx_spark(
                {"dgx_spark_count": 1, "dgx_spark_memory_gb_each": 128}
            ),
            "1 system / 1 GPU · 128GB each · 128GB aggregate",
        )

    def test_hardware_summary_supports_mixed_node_counts(self) -> None:
        from scripts.generate_results_summary import _hardware_footprint_markdown

        summary = _hardware_footprint_markdown(
            [
                {"dgx_spark_count": 1, "dgx_spark_memory_gb_each": 128},
                {"dgx_spark_count": 2, "dgx_spark_memory_gb_each": 128},
            ]
        )
        self.assertIn("1× DGX Spark, 2× DGX Spark", summary)
        self.assertIn("128GB of unified memory per system", summary)


if __name__ == "__main__":
    unittest.main()
