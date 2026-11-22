import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_capability_benchmarks as capabilities
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

    def test_full_workflow_requires_tokenizer_and_context(self) -> None:
        args = combined.build_parser().parse_args([
            "--base-url", "https://model.example/v1", "--model", "served-model",
            "--baseline-id", "baseline", "--suite", "configs/qwen-native-standard.json",
            "--label", "test",
        ])
        self.assertFalse(args.serving_and_tools_only)
        with self.assertRaisesRegex(combined.CombinedRunError, "--tokenizer and --context-window"):
            combined.capability_settings(args)
        args.serving_and_tools_only = True
        self.assertIsNone(combined.capability_settings(args))

    def test_context_settings_reserve_headroom(self) -> None:
        self.args.serving_and_tools_only = False
        self.args.context_window = 131072
        self.args.disable_capability_thinking = True
        self.args.ruler_essays = None
        with tempfile.TemporaryDirectory() as directory:
            self.args.tokenizer = Path(directory) / "tokenizer.json"
            self.args.tokenizer.write_text("{}")
            profile = combined.capability_settings(self.args)
        self.assertEqual(profile["ruler_lengths"], [4096, 32768])
        self.assertEqual(profile["longbench_prompt_cap"], 130816)
        self.assertEqual(profile["extra_body"], {"chat_template_kwargs": {"enable_thinking": False}})

    def test_incomplete_tool_grades_still_lead_to_capabilities(self) -> None:
        self.args.tool_eval_profile = combined.DEFAULT_PROFILE
        self.args.tool_eval_bin = None
        profile = {"protocol_id": capabilities.PROTOCOL}
        metadata = {"git_sha": self.profile["commit"]}
        commands = []

        def fake_run(command, *, cwd, env, log_path):
            name = log_path.name
            commands.append(name)
            if name == "serving.log":
                output = Path(command[command.index("--output") + 1])
                result = {"scenarios": [{"summary": {"failed_requests": 0}}]}
            elif name == "tool-eval-smoke.log":
                output = cwd / "tool-eval-smoke.json"
                result = {
                    "metadata": metadata,
                    "total_scenarios": 15,
                    "scores": {"scenario_results": [{} for _ in range(15)]},
                }
            else:
                self.assertEqual(name, "tool-eval-standard.log")
                output = cwd / "tool-eval-standard.json"
                result = {
                    "metadata": metadata,
                    "trial_statistics": {
                        "trials": 3,
                        "per_scenario": {
                            scenario: {"points": [0, 2, 2]}
                            for scenario in self.profile["scenario_categories"]
                            if scenario != "TC-64"
                        },
                    },
                }
            capabilities.write_json(output, result)

        def fake_capabilities(args, raw_dir, settings, key):
            self.assertEqual(settings, profile)
            self.assertEqual(key, "example-key")
            self.assertTrue((raw_dir / "tool-eval-standard.json").is_file())
            return False, "capabilities-test"

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(combined, "RAW_ROOT", Path(directory)),
            patch.object(combined, "capability_settings", return_value=profile),
            patch.object(combined.shutil, "which", return_value="mock-command"),
            patch.object(combined, "validate_baseline"),
            patch.object(combined, "preflight_endpoint"),
            patch.object(combined, "ensure_tool_eval", return_value=Path("mock-tool")),
            patch.object(combined, "_run_logged", side_effect=fake_run),
            patch.object(combined, "run_capabilities", side_effect=fake_capabilities),
            patch.dict(combined.os.environ, {"MODEL_API_KEY": "example-key"}),
            patch("builtins.print"),
        ):
            raw = combined.execute(self.args)
            manifest = combined.load_json(raw / "manifest.json")
        self.assertEqual(commands, ["serving.log", "tool-eval-smoke.log", "tool-eval-standard.log"])
        self.assertEqual(manifest["status"], "tool-eval-incomplete")
        self.assertEqual(manifest["tool_eval_completion"], 98.6)
        self.assertEqual(manifest["capability_artifacts"], "capabilities-test")
        self.assertNotIn("example-key", json.dumps(manifest))

    def test_resume_rejects_an_endpoint_or_suite_change(self) -> None:
        profile = {"protocol_id": capabilities.PROTOCOL}
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory).resolve()
            raw = raw_root / "run"
            raw.mkdir()
            self.args.suite = raw_root / "suite.json"
            self.args.suite.write_text("{}")
            capabilities.write_json(raw / "serving.json", {
                "scenarios": [{"summary": {"failed_requests": 0}}],
            })
            with patch.object(combined, "RAW_ROOT", raw_root):
                combined._write_manifest(raw, self.args, self.profile, "failed", profile)
                combined._validate_resume(raw, self.args, self.profile, profile)
                self.args.base_url = "https://different.example/v1"
                with self.assertRaisesRegex(combined.CombinedRunError, "run identity"):
                    combined._validate_resume(raw, self.args, self.profile, profile)
                self.args.base_url = "https://model.example"
                self.args.suite.write_text('{"changed": true}')
                with self.assertRaisesRegex(combined.CombinedRunError, "run identity"):
                    combined._validate_resume(raw, self.args, self.profile, profile)

    def test_context_setup_cannot_read_endpoint_key_and_bad_responses_are_errors(self) -> None:
        connection = {"base_url": self.args.base_url, "model": self.args.model}

        def fake_longbench(source, work, settings, request):
            self.assertNotIn("LLM_SERVING_BENCH_ENDPOINT_KEY", combined.os.environ)
            self.assertEqual(request("example", 0, 128), {"error": "invalid completion message"})
            self.assertEqual(request("example", 0, 128)["prediction"], "")
            return {"complete": False}

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(combined.os.environ, {"LLM_SERVING_BENCH_ENDPOINT_KEY": "example-key"}),
            patch("llm_serving_bench.client.OpenAIClient") as client,
            patch.object(capabilities, "run_longbench", side_effect=fake_longbench),
        ):
            client.return_value.chat_completion.side_effect = [
                {"choices": [{"message": None}]},
                {"choices": [{"message": {"reasoning_content": "only reasoning"}}]},
            ]
            capabilities.context_evaluation(
                "longbench", Path(directory), {"timeout": 900, "extra_body": {}}, connection
            )
            client.assert_called_once_with(self.args.base_url, self.args.model, "example-key", 900)

    def test_capability_failure_keeps_later_stages_and_credentials_are_scoped(self) -> None:
        self.args.ruler_essays = None
        observed = []

        def fake_run(command, *, cwd, env, log_path):
            name = log_path.stem
            self.assertNotIn("example-key", command)
            self.assertNotIn("MODEL_API_KEY", env)
            if name in {"context-venv", "context-install", "tau2-install"}:
                self.assertNotIn("OPENAI_API_KEY", env)
                self.assertNotIn("LLM_SERVING_BENCH_ENDPOINT_KEY", env)
                return
            observed.append(name)
            if name.startswith("tau2"):
                self.assertEqual(env.get("OPENAI_API_KEY"), "example-key")
                self.assertNotIn("LLM_SERVING_BENCH_ENDPOINT_KEY", env)
            else:
                self.assertEqual(env.get("LLM_SERVING_BENCH_ENDPOINT_KEY"), "example-key")
                self.assertNotIn("OPENAI_API_KEY", env)
            if name == "ruler":
                raise combined.CombinedRunError("mock stage failure")
            capabilities.write_json(cwd / f"{name}-summary.json", {"complete": True})

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(combined, "checkout_source"),
            patch.object(combined, "_run_logged", side_effect=fake_run),
            patch.dict(combined.os.environ, {"MODEL_API_KEY": "example-key"}),
            patch("builtins.print"),
        ):
            root = Path(directory)
            self.args.tokenizer = root / "tokenizer.json"
            self.args.tokenizer.write_text("{}")
            profile = {"tokenizer_sha256": capabilities.sha256(self.args.tokenizer),
                       "ruler_lengths": list(capabilities.RULER_LENGTHS)}
            complete, folder = combined.run_capabilities(self.args, root, profile, "example-key")
            summary = capabilities.read_json(root / folder / "summary.json")
        self.assertEqual(observed, ["ruler", "longbench", "tau2-airline", "tau2-retail", "tau2-telecom"])
        self.assertFalse(complete)
        self.assertFalse(summary["ruler"]["complete"])
        self.assertTrue(summary["tau2"]["complete"])

    def test_tau_graded_zero_differs_from_timeout_and_missing_grade(self) -> None:
        simulations = [
            {"task_id": "1", "termination_reason": "user_stop", "reward_info": {"reward": 1}},
            {"task_id": "2", "termination_reason": "max_steps", "reward_info": {"reward": 0}},
            {"task_id": "3", "termination_reason": "timeout", "reward_info": {"reward": 0}},
        ]
        partial = capabilities.summarize_tau(simulations, ["1", "2", "3"])
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["graded"], 2)
        self.assertEqual(partial["full_reward"], 1)
        simulations[2]["termination_reason"] = "agent_stop"
        self.assertTrue(capabilities.summarize_tau(simulations, ["1", "2", "3"])["complete"])
        simulations[2]["reward_info"] = None
        self.assertFalse(capabilities.summarize_tau(simulations, ["1", "2", "3"])["complete"])


if __name__ == "__main__":
    unittest.main()
