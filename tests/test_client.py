import unittest
import urllib.request

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
