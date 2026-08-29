import unittest

from llm_serving_bench.client import _reasoning_text


class ClientTests(unittest.TestCase):
    def test_reasoning_delta_variants(self) -> None:
        cases = [
            ({"reasoning_content": "a"}, "a"),
            ({"reasoning": "b"}, "b"),
            ({"provider_specific_fields": {"reasoning_content": "c"}}, "c"),
            ({"provider_specific_fields": {"reasoning": "d"}}, "d"),
            ({}, ""),
        ]
        for delta, expected in cases:
            with self.subTest(delta=delta):
                self.assertEqual(_reasoning_text(delta), expected)


if __name__ == "__main__":
    unittest.main()
