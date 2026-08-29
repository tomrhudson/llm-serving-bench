import unittest

from llm_serving_bench.workloads import prepare_requests


class FakeClient:
    def tokenize_count(self, prompt):
        return len(prompt.split())


class FakeFactory:
    client = FakeClient()

    def unique_prompt(self, target, offset):
        return "unique prompt"

    def shared_prompt(self, group, target, offset):
        return "shared prompt"

    def needle_prompt(self, target, passkey, offset):
        return f"needle {passkey}"


class WorkloadTests(unittest.TestCase):
    def test_canaries_repeat(self):
        scenario = {
            "name": "canary", "kind": "canary", "repetitions": 2,
            "cases": [{"prompt": "say X", "expected": "X"}],
        }
        prepared = prepare_requests(scenario, FakeFactory())
        self.assertEqual(len(prepared), 2)
        self.assertTrue(all(item.expected == "X" for item in prepared))

    def test_needle_expected(self):
        scenario = {
            "name": "needle", "kind": "needle", "requests": 1,
            "prompt_tokens": 100, "passkey": "KEY",
        }
        prepared = prepare_requests(scenario, FakeFactory())
        self.assertEqual(prepared[0].expected, "KEY")


if __name__ == "__main__":
    unittest.main()
