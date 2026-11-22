import unittest

from llm_serving_bench.client import RequestResult
from llm_serving_bench.stats import add_concurrency_effectiveness, percentile, summarize


class StatsTests(unittest.TestCase):
    def test_percentile_interpolates(self):
        self.assertEqual(percentile([1, 2, 3, 4], 50), 2.5)

    def test_summary_counts_errors_and_quality(self):
        good = RequestResult(
            request_id="good", started_at=0, e2e_seconds=2,
            ttft_seconds=0.5, prompt_tokens=10, completion_tokens=20,
            chunk_intervals_seconds=[0.1], content="CEDAR", expected="cedar",
        )
        bad = RequestResult(
            request_id="bad", started_at=0, e2e_seconds=1,
            ttft_seconds=None, prompt_tokens=0, completion_tokens=0,
            error="boom",
        )
        summary = summarize([good, bad], wall_seconds=2, concurrency=2)
        self.assertEqual(summary["successful_requests"], 1)
        self.assertEqual(summary["failed_requests"], 1)
        self.assertEqual(summary["quality_passed"], 1)
        self.assertEqual(summary["output_throughput_tps"], 10)

    def test_decode_rate_excludes_first_token(self):
        result = RequestResult(
            request_id="r", started_at=0, e2e_seconds=3, ttft_seconds=1,
            prompt_tokens=10, completion_tokens=21,
        )
        summary = summarize([result], wall_seconds=3, concurrency=1)
        self.assertEqual(summary["per_request_decode_tps_mean"], 10)

    def test_estimated_completion_tokens_are_counted(self):
        estimated = RequestResult(
            request_id="e", started_at=0, e2e_seconds=1, ttft_seconds=0.1,
            prompt_tokens=0, completion_tokens=5,
            completion_tokens_source="char_estimate",
        )
        reported = RequestResult(
            request_id="u", started_at=0, e2e_seconds=1, ttft_seconds=0.1,
            prompt_tokens=0, completion_tokens=5,
        )
        summary = summarize([estimated, reported], wall_seconds=1, concurrency=2)
        self.assertEqual(summary["completion_tokens_estimated_requests"], 1)

    def test_concurrency_effectiveness(self):
        scenarios = [
            {"config": {"comparison_group": "x"},
             "summary": {"concurrency": 1, "output_throughput_tps": 10}},
            {"config": {"comparison_group": "x"},
             "summary": {"concurrency": 4, "output_throughput_tps": 30}},
        ]
        add_concurrency_effectiveness(scenarios)
        self.assertEqual(scenarios[1]["summary"]["throughput_speedup_vs_c1"], 3)
        self.assertEqual(scenarios[1]["summary"]["parallel_efficiency"], 0.75)


if __name__ == "__main__":
    unittest.main()
