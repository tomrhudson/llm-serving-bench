import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import import_tool_eval_result as importer


COMMIT = "b60e2f00f6c44352a3680356e7c7948f777c5280"


def profile() -> dict:
    return {
        "protocol_id": "tool-eval-standard-v1-b60e2f0",
        "commit": COMMIT,
        "standard_scenarios": 69,
        "trials": 3,
        "scenario_categories": {
            f"TC-{index:02d}": "A" for index in range(1, 70)
        },
    }


def result() -> dict:
    per_scenario = {
        f"TC-{index:02d}": {
            "points": [2, 2, 2],
            "mean": 2.0,
            "stddev": 0.0,
            "pass_at_k": True,
            "pass_hat_k": True,
        }
        for index in range(1, 70)
    }
    per_scenario["TC-02"]["points"] = [2, 1, 2]
    return {
        "schema_version": "1",
        "tool_eval_bench_version": "2.8.1.dev1+gb60e2f00f",
        "run_id": "safe-run-id",
        "final_score": 99,
        "safety_warnings": [],
        "safety_gate": {"passed": True, "warnings": []},
        "total_scenarios": 69,
        "metadata": {"git_sha": COMMIT, "hostname": "private-host"},
        "config": {
            "config_fingerprint": "abc123",
            "base_url": "http://private-host:8000/v1",
        },
        "scores": {
            "completion_rate": 100.0,
            "scenario_results": [
                {
                    "scenario_id": f"TC-{index:02d}",
                    "category": "A",
                    "status": "pass",
                    "raw_log": "SECRET RAW TEXT",
                }
                for index in range(1, 70)
            ],
        },
        "trial_statistics": {
            "trials": 3,
            "final_score_mean": 98.7,
            "final_score_median": 99.0,
            "final_score_stddev": 0.6,
            "final_score_ci95": [98.0, 99.0],
            "pass_at_k": 100.0,
            "pass_hat_k": 98.6,
            "reliability_gap": 1.4,
            "per_scenario": per_scenario,
            "per_category": {
                "A": {
                    "label": "Tool Selection",
                    "mean_percent": 99.0,
                    "stddev_percent": 1.0,
                }
            },
        },
    }


class ToolEvalImportTests(unittest.TestCase):
    def test_catalog_update_preserves_unrelated_formatting(self) -> None:
        original = '''{
  "baselines": [
    {
      "id": "baseline-1",
      "quality": {"passed": 1, "total": 1}
    },
    {
      "id": "baseline-2",
      "quality": {"passed": 2, "total": 2}
    }
  ]
}
'''
        updated = importer.update_catalog_text(original, "baseline-1", {"status": "complete"})
        self.assertIn('      "quality": {"passed": 2, "total": 2}', updated)
        self.assertIn('      "tool_eval": {', updated)
        self.assertEqual(updated.count('"tool_eval"'), 1)
        replaced = importer.update_catalog_text(
            updated, "baseline-1", {"status": "incomplete"}
        )
        self.assertEqual(replaced.count('"tool_eval"'), 1)
        self.assertIn('"status": "incomplete"', replaced)

    def test_sanitizer_allowlists_summary_and_nonpass_identity(self) -> None:
        summary, non_pass = importer.sanitize_tool_result(result(), profile())
        rendered = json.dumps({"summary": summary, "non_pass": non_pass})
        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["pass_hat_3"], 98.6)
        self.assertEqual(non_pass[0]["scenario_id"], "TC-02")
        self.assertEqual(non_pass[0]["category"], "A")
        self.assertNotIn("private-host", rendered)
        self.assertNotIn("SECRET RAW TEXT", rendered)
        self.assertNotIn("base_url", rendered)

    def test_unknown_schema_and_commit_are_rejected(self) -> None:
        bad_schema = result()
        bad_schema["schema_version"] = "2"
        with self.assertRaises(importer.ImportError):
            importer.sanitize_tool_result(bad_schema, profile())
        bad_commit = result()
        bad_commit["metadata"]["git_sha"] = "0" * 40
        with self.assertRaises(importer.ImportError):
            importer.sanitize_tool_result(bad_commit, profile())

    def test_upstream_short_commit_is_tied_to_full_profile_commit(self) -> None:
        shortened = result()
        shortened["metadata"]["git_sha"] = COMMIT[:7]
        summary, _ = importer.sanitize_tool_result(shortened, profile())
        self.assertEqual(summary["upstream_commit"], COMMIT)

    def test_missing_trial_points_mark_result_incomplete(self) -> None:
        incomplete = result()
        incomplete["trial_statistics"]["per_scenario"]["TC-01"]["points"] = [2, 2]
        summary, non_pass = importer.sanitize_tool_result(incomplete, profile())
        self.assertEqual(summary["status"], "incomplete")
        self.assertTrue(
            next(item for item in non_pass if item["scenario_id"] == "TC-01")[
                "infrastructure_failure"
            ]
        )
        self.assertEqual(
            next(item for item in non_pass if item["scenario_id"] == "TC-01")[
                "status"
            ],
            "incomplete",
        )

    def test_safety_failure_is_retained_without_warning_text(self) -> None:
        unsafe = result()
        unsafe["safety_gate"] = {
            "passed": False,
            "warnings": ["sensitive generated warning"],
        }
        summary, _ = importer.sanitize_tool_result(unsafe, profile())
        self.assertFalse(summary["safety_passed"])
        self.assertNotIn("warnings", summary)

    def test_generated_text_and_markup_in_allowlisted_fields_are_rejected(self) -> None:
        malicious = result()
        malicious["trial_statistics"]["per_category"]["A"]["label"] = (
            "[leak](http://private.example)"
        )
        with self.assertRaises(importer.ImportError):
            importer.sanitize_tool_result(malicious, profile())

    def test_invalid_points_are_rejected(self) -> None:
        malformed = result()
        malformed["trial_statistics"]["per_scenario"]["TC-02"]["points"] = [2, 9, 2]
        with self.assertRaises(importer.ImportError):
            importer.sanitize_tool_result(malformed, profile())

    def test_import_writes_curated_report_and_catalog_entry_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            results_dir = root / "results"
            raw.mkdir()
            results_dir.mkdir()
            (raw / "manifest.json").write_text(json.dumps({
                "baseline_id": "baseline-1",
                "tool_eval_profile": profile(),
            }))
            (raw / "tool-eval-standard.json").write_text(json.dumps(result()))
            catalog_path = results_dir / "catalog.json"
            catalog_path.write_text(json.dumps({
                "schema_version": 6,
                "models": [{
                    "id": "model-1",
                    "benchmarked_source": "[checkpoint](https://example.test/model)",
                }],
                "baselines": [{
                    "id": "baseline-1",
                    "model_id": "model-1",
                    "label": "Baseline One",
                    "report": "serving.md",
                    "runtime": "vLLM",
                    "recipe_credit": "[recipe](https://example.test/recipe)",
                }],
            }))
            with (
                patch.object(importer, "RESULTS", results_dir),
                patch.object(importer, "CATALOG", catalog_path),
            ):
                report_path, summary = importer.import_result(
                    raw, "baseline-1", "tool-report.md"
                )
            report = report_path.read_text()
            catalog = json.loads(catalog_path.read_text())
            self.assertEqual(summary["report"], "tool-report.md")
            self.assertIn("Pass^3", report)
            self.assertNotIn("private-host", report)
            self.assertNotIn("SECRET RAW TEXT", report)
            self.assertEqual(
                catalog["baselines"][0]["tool_eval"]["protocol_id"],
                profile()["protocol_id"],
            )


if __name__ == "__main__":
    unittest.main()
