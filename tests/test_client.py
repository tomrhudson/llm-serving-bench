import unittest
import urllib.request
from unittest.mock import Mock, call

from llm_serving_bench.client import (
    InsecureTransportError,
    OpenAIClient,
    _reasoning_text,
)


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
                with self.assertRaisesRegex(ValueError, "unsupported /tokenize"):
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


if __name__ == "__main__":
    unittest.main()
