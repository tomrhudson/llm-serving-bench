import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_combined_benchmark as combined


ROOT = Path(__file__).resolve().parents[1]


class CombinedBenchmarkTests(unittest.TestCase):
    def test_runner_is_invocable_by_filename_from_repo_root(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/run_combined_benchmark.py", "--help"],
            cwd=combined.ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def setUp(self) -> None:
        self.profile = combined.load_profile(
            ROOT / "configs" / "tool-eval-standard-v1.json"
        )
        self.args = argparse.Namespace(
            base_url="https://model.example/v1",
            model="served-model",
            baseline_id="baseline",
            suite=Path("configs/qwen-native-standard.json"),
            label="test run",
            server_label="redacted-direct-endpoint",
            api_key_env="MODEL_API_KEY",
            monitor_host=["rank0=user@example"],
            monitor_interval=5.0,
            serving_timeout=900.0,
            resume_raw_dir=None,
        )

    def test_profile_pins_protocol_and_three_serial_trials(self) -> None:
        self.assertEqual(
            self.profile["commit"],
            "b60e2f00f6c44352a3680356e7c7948f777c5280",
        )
        self.assertEqual(self.profile["standard_scenarios"], 69)
        self.assertEqual(len(self.profile["scenario_categories"]), 69)
        self.assertEqual(self.profile["scenario_categories"]["TC-64"], "O")
        self.assertEqual(self.profile["trials"], 3)
        self.assertEqual(self.profile["parallel"], 1)
        self.assertFalse(self.profile["hard_mode"])

    def test_serving_command_passes_key_name_not_secret(self) -> None:
        command = combined.serving_command(self.args, Path("raw/serving.json"))
        self.assertIn("MODEL_API_KEY", command)
        self.assertNotIn("secret-value", command)
        self.assertEqual(command.count("--monitor-host"), 1)

    def test_tool_commands_are_smoke_then_standard_three_trials(self) -> None:
        smoke = combined.tool_eval_command(
            Path("/bin/tool-eval"), self.profile, self.args,
            "smoke.json", smoke=True,
        )
        standard = combined.tool_eval_command(
            Path("/bin/tool-eval"), self.profile, self.args,
            "standard.json", smoke=False,
        )
        self.assertIn("--short", smoke)
        self.assertNotIn("--trials", smoke)
        self.assertNotIn("--short", standard)
        self.assertEqual(
            standard[standard.index("--trials") + 1], "3"
        )
        self.assertEqual(standard[standard.index("--parallel") + 1], "1")
        self.assertNotIn("MODEL_API_KEY", standard)

    def test_serving_transport_errors_stop_tool_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "serving.json"
            path.write_text(json.dumps({
                "scenarios": [
                    {"summary": {"failed_requests": 0}},
                    {"summary": {"failed_requests": 2}},
                ]
            }))
            with self.assertRaises(combined.CombinedRunError):
                combined._validate_serving_result(path)

    def test_model_mismatch_aborts_preflight(self) -> None:
        with patch("llm_serving_bench.client.OpenAIClient") as client:
            client.return_value.models.return_value = {
                "data": [{"id": "different-model"}]
            }
            with self.assertRaises(combined.CombinedRunError):
                combined.preflight_endpoint(
                    "https://model.example/v1", "served-model", None
                )

    def test_malformed_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.json"
            path.write_text("{not-json")
            with self.assertRaises(combined.CombinedRunError):
                combined.load_json(path)

    def test_tool_identity_must_be_exact_pinned_commit(self) -> None:
        good = {"metadata": {"git_sha": self.profile["commit"]}}
        combined._validate_tool_identity(good, self.profile)
        shortened_upstream_identity = {"metadata": {"git_sha": "b60e2f0"}}
        combined._validate_tool_identity(shortened_upstream_identity, self.profile)
        with self.assertRaises(combined.CombinedRunError):
            combined._validate_tool_identity(
                {"metadata": {"git_sha": "0" * 40}}, self.profile
            )

    def test_smoke_completion_uses_graded_scenario_coverage(self) -> None:
        result = {
            "total_scenarios": 2,
            "scores": {"scenario_results": [
                {"scenario_id": "TC-01", "is_infrastructure_failure": False},
                {"scenario_id": "TC-02", "is_infrastructure_failure": True},
            ]},
        }
        self.assertEqual(combined._completion_rate(result), 50.0)

    def test_standard_completion_counts_every_trial_scenario(self) -> None:
        result = {
            "trial_statistics": {
                "trials": 3,
                "per_scenario": {
                    f"TC-{index:02d}": {"points": [2, 2, 2]}
                    for index in range(1, 70)
                },
            }
        }
        self.assertEqual(combined._standard_completion_rate(result, self.profile), 100.0)
        result["trial_statistics"]["per_scenario"]["TC-64"]["points"] = []
        self.assertEqual(combined._standard_completion_rate(result, self.profile), 98.6)

    def test_standard_completion_rejects_unknown_scenarios(self) -> None:
        result = {
            "trial_statistics": {
                "trials": 3,
                "per_scenario": {"TC-70": {"points": [2, 2, 2]}},
            }
        }
        with self.assertRaises(combined.CombinedRunError):
            combined._standard_completion_rate(result, self.profile)

    def test_raw_run_directory_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text()
        self.assertIn(".bench-runs/", ignored)


if __name__ == "__main__":
    unittest.main()
