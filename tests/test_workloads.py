import unittest

from llm_serving_bench.workloads import PromptFactory, prepare_requests


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
        self.assertEqual(prepared[0].match, "contains")

    def test_canaries_default_to_exact_match(self):
        scenario = {
            "name": "canary", "kind": "canary",
            "cases": [
                {"prompt": "say X", "expected": "X"},
                {"prompt": "say Y", "expected": "Y", "match": "contains"},
            ],
        }
        prepared = prepare_requests(scenario, FakeFactory())
        self.assertEqual([item.match for item in prepared], ["exact", "contains"])

    def test_unique_prompts_do_not_repeat_across_scenarios(self):
        # "decode-c1" and "decode-c2" differ by one in their character-code
        # sum, which used to give c2 request 0 the same prompt as c1 request 1.
        factory = PromptFactory(FakeClient(), seed=1)
        prompts = []
        for name in ("decode-c1", "decode-c2", "decode-c4"):
            scenario = {"name": name, "requests": 4, "prompt_tokens": 64}
            prompts.extend(item.prompt for item in prepare_requests(scenario, factory))
        self.assertEqual(len(prompts), len(set(prompts)))

        again = PromptFactory(FakeClient(), seed=1)
        repeat = prepare_requests(
            {"name": "decode-c1", "requests": 1, "prompt_tokens": 64}, again
        )
        self.assertEqual(repeat[0].prompt, prompts[0])

    def test_shared_prefix_is_reused_within_a_group(self):
        factory = PromptFactory(FakeClient(), seed=1)
        cold = prepare_requests({"name": "cold", "requests": 2, "prompt_tokens": 64,
                                 "prompt_mode": "shared", "prompt_group": "g"}, factory)
        warm = prepare_requests({"name": "warm", "requests": 2, "prompt_tokens": 64,
                                 "prompt_mode": "shared", "prompt_group": "g"}, factory)
        prefix = cold[0].prompt.rsplit("\nRequest variant", 1)[0]
        self.assertTrue(all(item.prompt.startswith(prefix) for item in cold + warm))
        self.assertNotEqual(cold[0].prompt, cold[1].prompt)


if __name__ == "__main__":
    unittest.main()
