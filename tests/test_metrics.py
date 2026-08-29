import unittest

from llm_serving_bench.metrics import metric_delta, parse_selected_metrics


class MetricsTests(unittest.TestCase):
    def test_parse_selected_and_sum_counters(self):
        text = """
# HELP ignored nope
sglang:num_running_reqs 3
sglang:prompt_tokens_total{model=\"a\"} 10
sglang:prompt_tokens_total{model=\"b\"} 5
other_metric 99
"""
        parsed = parse_selected_metrics(text)
        self.assertEqual(parsed["sglang:num_running_reqs"], 3)
        self.assertEqual(parsed["sglang:prompt_tokens_total"], 15)
        self.assertNotIn("other_metric", parsed)

    def test_delta_only_counters(self):
        before = {"sglang:prompt_tokens_total": 10, "sglang:num_running_reqs": 1}
        after = {"sglang:prompt_tokens_total": 15, "sglang:num_running_reqs": 2}
        self.assertEqual(metric_delta(before, after), {"sglang:prompt_tokens_total": 5})


if __name__ == "__main__":
    unittest.main()
