import unittest
import urllib.request
from unittest.mock import Mock, call, patch

from llm_serving_bench.client import (
    InsecureTransportError,
    OpenAIClient,
    RequestResult,
    _reasoning_text,
    answer_matches,
)


class _FakeStream:
    def __init__(self, lines):
        self._lines = [line.encode("utf-8") for line in lines]

    def __enter__(self):
        return iter(self._lines)

    def __exit__(self, *exc):
        return False


def _stream_chat(client, lines, **kwargs):
    with patch("urllib.request.urlopen", return_value=_FakeStream(lines)):
        return client.chat("r", "prompt", 8, **kwargs)


class ClientTests(unittest.TestCase):
    def test_api_key_requires_https(self) -> None:
        insecure_urls = [
            "http://example.test/v1",
            "HTTP://example.test/v1",
        ]
        for base_url in insecure_urls:
            with self.subTest(base_url=base_url):
                with self.assertRaises(InsecureTransportError):
                    OpenAIClient(base_url, "model", api_key="secret")

    def test_https_api_key_and_unauthenticated_http_remain_supported(self) -> None:
        authenticated = OpenAIClient(
            "https://example.test/v1", "model", api_key="secret"
        )
        unauthenticated = OpenAIClient("http://example.test/v1", "model")

        self.assertEqual(authenticated.api_url, "https://example.test/v1")
        self.assertEqual(unauthenticated.api_url, "http://example.test/v1")

    def test_api_key_is_not_forwarded_on_redirect(self) -> None:
        client = OpenAIClient(
            "https://example.test/v1", "model", api_key="secret"
        )
        request = client._api_request(
            "https://example.test/v1/models", method="GET"
        )

        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(request.get_header("Content-type"), "application/json")
        redirected = urllib.request.HTTPRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://other.example/models",
        )
        self.assertIsNotNone(redirected)
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_base_url_routing_remains_compatible(self) -> None:
        with_v1 = OpenAIClient("https://example.test/v1/", "model")
        without_v1 = OpenAIClient("https://example.test", "model")

        self.assertEqual(with_v1.root_url, "https://example.test")
        self.assertEqual(with_v1.api_url, "https://example.test/v1")
        self.assertEqual(without_v1.root_url, "https://example.test")
        self.assertEqual(without_v1.api_url, "https://example.test/v1")

    def test_tokenize_count_supports_vllm_and_llama_cpp(self) -> None:
        client = OpenAIClient("http://127.0.0.1:8000/v1", "model")
        calls = []

        def vllm(url, payload=None, timeout=None):
            calls.append(payload)
            return {"count": 7, "tokens": [1] * 7}

        client._json_request = vllm
        self.assertEqual(client.tokenize_count("hi"), 7)
        self.assertEqual(calls, [{"model": "model", "prompt": "hi"}])

        calls.clear()

        def llama_cpp(url, payload=None, timeout=None):
            calls.append(payload)
            return {"tokens": [1, 2, 3] if "content" in payload else []}

        client._json_request = llama_cpp
        self.assertEqual(client.tokenize_count("hi"), 3)
        self.assertEqual(calls[-1], {"content": "hi", "add_special": False})

        client._json_request = lambda url, payload=None, timeout=None: {}
        with self.assertRaises(RuntimeError):
            client.tokenize_count("hi")

    def test_malformed_base_url_is_rejected(self) -> None:
        for base_url in ["", "localhost:8000", "file:///tmp/socket", "https:///v1"]:
            with self.subTest(base_url=base_url):
                with self.assertRaises(ValueError):
                    OpenAIClient(base_url, "model")

    def test_count_tokenizer_keeps_existing_payload_and_precedence(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        client._json_request = Mock(return_value={"count": 7, "tokens": []})

        self.assertEqual(client.tokenize_count("hello"), 7)
        client._json_request.assert_called_once_with(
            "http://example.test/tokenize", {"model": "model", "prompt": "hello"}
        )

    def test_llama_tokenizer_retries_native_payload_and_remembers_it(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        client._json_request = Mock(side_effect=[
            {"tokens": []}, {"tokens": [11, 22, 33]}, {"tokens": [44, 55]},
        ])

        self.assertEqual(client.tokenize_count("first prompt"), 3)
        self.assertEqual(client.tokenize_count("next prompt"), 2)
        self.assertEqual(client._json_request.call_args_list, [
            call("http://example.test/tokenize", {"model": "model", "prompt": "first prompt"}),
            call("http://example.test/tokenize", {"content": "first prompt", "add_special": False}),
            call("http://example.test/tokenize", {"content": "next prompt", "add_special": False}),
        ])

    def test_llama_tokenizer_accepts_empty_input(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        client._json_request = Mock(side_effect=[{"tokens": []}, {"tokens": []}])

        self.assertEqual(client.tokenize_count(""), 0)

    def test_llama_tokenizer_rejects_empty_result_for_nonempty_input(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        client._json_request = Mock(side_effect=[{"tokens": []}, {"tokens": []}])

        with self.assertRaisesRegex(ValueError, "nonempty prompt"):
            client.tokenize_count("benchmark words")

    def test_malformed_tokenizer_response_fails_before_calibration(self) -> None:
        for response in [None, {}, [], {"tokens": "not a token list"}]:
            with self.subTest(response=response):
                client = OpenAIClient("http://example.test/v1", "model")
                client._json_request = Mock(return_value=response)
                with self.assertRaisesRegex(RuntimeError, "unrecognized /tokenize"):
                    client.tokenize_count("benchmark words")

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


    def test_empty_stream_is_a_failure(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        result = _stream_chat(client, ["data: [DONE]"])

        self.assertIsNotNone(result.error)
        self.assertIn("EmptyStream", result.error)
        self.assertEqual(result.completion_tokens_source, "none")
        self.assertFalse(result.passed)

    def test_error_event_in_stream_is_a_failure(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        result = _stream_chat(client, [
            'data: {"choices":[{"delta":{"content":"par"}}]}',
            'data: {"error":{"message":"out of KV cache"}}',
        ])

        self.assertIsNotNone(result.error)
        self.assertIn("StreamError", result.error)
        self.assertIn("out of KV cache", result.error)

    def test_usage_tokens_are_marked_as_usage(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        result = _stream_chat(client, [
            'data: {"choices":[{"delta":{"content":"hi"}}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":2}}',
            "data: [DONE]",
        ])

        self.assertIsNone(result.error)
        self.assertEqual(result.completion_tokens, 2)
        self.assertEqual(result.completion_tokens_source, "usage")

    def test_missing_usage_falls_back_and_records_source(self) -> None:
        client = OpenAIClient("http://example.test/v1", "model")
        lines = ['data: {"choices":[{"delta":{"content":"abcdefgh"}}]}', "data: [DONE]"]

        client.tokenize_count = Mock(return_value=5)
        result = _stream_chat(client, lines)
        self.assertEqual(result.completion_tokens, 5)
        self.assertEqual(result.completion_tokens_source, "tokenize")

        client.tokenize_count = Mock(side_effect=RuntimeError("no tokenizer"))
        result = _stream_chat(client, lines)
        self.assertEqual(result.completion_tokens, 2)
        self.assertEqual(result.completion_tokens_source, "char_estimate")

    def test_exact_answer_matching(self) -> None:
        accepted = ["703", " 703\n", "703.", "**703**", "`703`", '"703"',
                    "<think>37*19...</think>\n703"]
        for reply in accepted:
            with self.subTest(reply=reply):
                self.assertTrue(answer_matches(reply, "703"))
        self.assertTrue(answer_matches("Jade", "jade"))
        rejected = [
            ("1703", "703"),
            ("The answer is 703.", "703"),
            ("", "703"),
            ("amber, cobalt, jade, violet", "jade"),
        ]
        for reply, expected in rejected:
            with self.subTest(reply=reply):
                self.assertFalse(answer_matches(reply, expected))

    def test_contains_matching_requires_a_standalone_token(self) -> None:
        self.assertTrue(answer_matches(
            "The passkey is ORBIT-7319-CEDAR.", "ORBIT-7319-CEDAR", "contains"
        ))
        self.assertFalse(answer_matches("1703", "703", "contains"))
        self.assertFalse(answer_matches(
            "ORBIT-7319-CEDARS", "ORBIT-7319-CEDAR", "contains"
        ))
        with self.assertRaises(ValueError):
            answer_matches("x", "x", "fuzzy")

    def test_request_result_uses_match_mode(self) -> None:
        result = RequestResult(
            request_id="r", started_at=0, e2e_seconds=1, ttft_seconds=0.1,
            prompt_tokens=1, completion_tokens=4,
            content="Sure: CEDAR-17", expected="CEDAR-17",
        )
        self.assertFalse(result.passed)
        result.match = "contains"
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
