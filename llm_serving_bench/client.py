from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any


class InsecureTransportError(ValueError):
    """Raised when bearer authentication would use a cleartext transport."""


@dataclass
class RequestResult:
    request_id: str
    started_at: float
    e2e_seconds: float
    ttft_seconds: float | None
    prompt_tokens: int
    completion_tokens: int
    chunk_intervals_seconds: list[float] = field(default_factory=list)
    finish_reason: str | None = None
    content: str = ""
    reasoning_content: str = ""
    error: str | None = None
    expected: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and (
            self.expected is None
            or self.expected.lower() in self.content.lower()
        )

    def to_dict(self, include_text: bool = False) -> dict[str, Any]:
        data = asdict(self)
        data["passed"] = self.passed
        if not include_text:
            data["content"] = ""
            data["reasoning_content"] = ""
        return data


class OpenAIClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 900.0,
    ) -> None:
        base_url = base_url.rstrip("/")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if api_key and parsed.scheme.lower() != "https":
            raise InsecureTransportError(
                "API keys require an https:// base URL; omit --api-key-env only "
                "when plain HTTP is confined to a trusted network"
            )
        if base_url.endswith("/v1"):
            self.root_url = base_url[:-3]
            self.api_url = base_url
        else:
            self.root_url = base_url
            self.api_url = base_url + "/v1"
        self.model = model
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        self.api_key = api_key

    def _api_request(
        self,
        url: str,
        *,
        data: bytes | None = None,
        method: str,
    ) -> urllib.request.Request:
        request = urllib.request.Request(
            url,
            data=data,
            headers=self.headers,
            method=method,
        )
        if self.api_key:
            # urllib copies ordinary headers across redirects. An unredirected
            # header authenticates only the operator-selected endpoint.
            request.add_unredirected_header(
                "Authorization", f"Bearer {self.api_key}"
            )
        return request

    def _json_request(
        self,
        url: str,
        payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = self._api_request(
            url,
            data=data,
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout or self.timeout
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
        return json.loads(raw) if raw else None

    def models(self) -> dict[str, Any]:
        return self._json_request(self.api_url + "/models")

    def tokenize_count(self, prompt: str) -> int:
        response = self._json_request(
            self.root_url + "/tokenize",
            {"model": self.model, "prompt": prompt},
        )
        return int(response["count"])

    def flush_cache(self) -> bool:
        request = self._api_request(
            self.root_url + "/flush_cache",
            data=b"{}",
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response.read()
                return 200 <= response.status < 300
        except (OSError, urllib.error.URLError):
            return False

    def metrics_text(self) -> str | None:
        request = urllib.request.Request(self.root_url + "/metrics", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read().decode("utf-8", "replace")
        except (OSError, urllib.error.URLError):
            return None

    def chat(
        self,
        request_id: str,
        prompt: str,
        output_tokens: int,
        *,
        temperature: float = 0.0,
        ignore_eos: bool = False,
        expected: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> RequestResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": output_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if ignore_eos:
            payload["ignore_eos"] = True
        if extra_body:
            payload.update(extra_body)

        started_wall = time.time()
        started = time.perf_counter()
        request = self._api_request(
            self.api_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        first_token_at: float | None = None
        previous_chunk_at: float | None = None
        chunk_intervals: list[float] = []
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage: dict[str, Any] = {}
        finish_reason: str | None = None

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    event = json.loads(data)
                    if event.get("usage"):
                        usage = event["usage"]
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    finish_reason = choice.get("finish_reason") or finish_reason
                    delta = choice.get("delta") or {}
                    content = delta.get("content") or ""
                    reasoning = _reasoning_text(delta)
                    if content:
                        content_parts.append(content)
                    if reasoning:
                        reasoning_parts.append(reasoning)
                    if content or reasoning:
                        now = time.perf_counter()
                        if first_token_at is None:
                            first_token_at = now
                        if previous_chunk_at is not None:
                            chunk_intervals.append(now - previous_chunk_at)
                        previous_chunk_at = now
        except Exception as exc:
            ended = time.perf_counter()
            return RequestResult(
                request_id=request_id,
                started_at=started_wall,
                e2e_seconds=ended - started,
                ttft_seconds=None,
                prompt_tokens=0,
                completion_tokens=0,
                error=f"{type(exc).__name__}: {exc}",
                expected=expected,
            )

        ended = time.perf_counter()
        full_content = "".join(content_parts)
        full_reasoning = "".join(reasoning_parts)
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        if completion_tokens <= 0 and (full_content or full_reasoning):
            try:
                completion_tokens = self.tokenize_count(
                    full_reasoning + full_content
                )
            except Exception:
                completion_tokens = max(1, len(full_reasoning + full_content) // 4)

        return RequestResult(
            request_id=request_id,
            started_at=started_wall,
            e2e_seconds=ended - started,
            ttft_seconds=(first_token_at - started) if first_token_at else None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            chunk_intervals_seconds=chunk_intervals,
            finish_reason=finish_reason,
            content=full_content,
            reasoning_content=full_reasoning,
            expected=expected,
        )


def _reasoning_text(delta: dict[str, Any]) -> str:
    """Normalize reasoning deltas emitted by OpenAI-compatible servers."""
    reasoning = delta.get("reasoning_content") or delta.get("reasoning")
    if reasoning:
        return str(reasoning)
    provider = delta.get("provider_specific_fields") or {}
    return str(
        provider.get("reasoning_content") or provider.get("reasoning") or ""
    )
