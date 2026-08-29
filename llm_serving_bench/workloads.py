from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .client import OpenAIClient


WORDS = (
    "amber anchor apple arch atlas autumn badge bamboo beacon birch blue "
    "brisk bronze canyon cedar cipher cloud cobalt comet coral crane delta "
    "drift dune echo ember falcon fern field fjord flame forest frost galaxy "
    "garden glacier gold harbor hazel heron horizon indigo island ivory jade "
    "juniper kite lagoon lake lantern leaf lemon lilac lunar maple meadow mist "
    "moss mountain navy north oak ocean olive opal orbit orchid pearl pine "
    "plum prism quartz raven reef ridge river robin rose ruby sage sand scarlet "
    "shadow shore silver sky solar sparrow spruce stone storm summit teal terra "
    "thistle tide timber topaz valley violet willow wind winter wren zephyr"
).split()


@dataclass
class PreparedRequest:
    request_id: str
    prompt: str
    output_tokens: int
    temperature: float
    ignore_eos: bool
    expected: str | None = None
    extra_body: dict[str, Any] | None = None
    prepared_prompt_tokens: int = 0


class PromptFactory:
    def __init__(self, client: OpenAIClient, seed: int = 20260829) -> None:
        self.client = client
        self.seed = seed
        self._word_counts: dict[tuple[int, str], int] = {}
        self._shared: dict[tuple[str, int], str] = {}

    def _words(self, count: int, seed: int) -> str:
        rng = random.Random(seed)
        return " ".join(rng.choice(WORDS) for _ in range(max(1, count)))

    def _calibrated_word_count(self, target_tokens: int, suffix: str) -> int:
        key = (target_tokens, suffix)
        if key in self._word_counts:
            return self._word_counts[key]
        count = max(1, target_tokens)
        for _ in range(4):
            probe = self._words(count, self.seed) + suffix
            actual = max(1, self.client.tokenize_count(probe))
            adjusted = max(1, round(count * target_tokens / actual))
            if abs(actual - target_tokens) <= max(8, target_tokens * 0.01):
                break
            count = adjusted
        self._word_counts[key] = count
        return count

    def unique_prompt(self, target_tokens: int, seed_offset: int) -> str:
        suffix = "\nContinue with a detailed but concise benchmark response."
        count = self._calibrated_word_count(target_tokens, suffix)
        return self._words(count, self.seed + seed_offset * 7919) + suffix

    def shared_prompt(
        self, group: str, target_tokens: int, seed_offset: int
    ) -> str:
        key = (group, target_tokens)
        if key not in self._shared:
            suffix = "\nThis is a reusable shared benchmark prefix."
            count = self._calibrated_word_count(target_tokens, suffix)
            self._shared[key] = self._words(
                count, self.seed + sum(ord(c) for c in group)
            ) + suffix
        return (
            self._shared[key]
            + f"\nRequest variant {seed_offset}: summarize the preceding material."
        )

    def needle_prompt(
        self, target_tokens: int, passkey: str, seed_offset: int
    ) -> str:
        marker = f"\nThe benchmark passkey is {passkey}. Remember it exactly.\n"
        question = "\nWhat is the benchmark passkey? Reply with the passkey exactly."
        count = self._calibrated_word_count(target_tokens, marker + question)
        filler = self._words(count, self.seed + seed_offset * 104729)
        split = max(1, len(filler) // 10)
        return filler[:split] + marker + filler[split:] + question


def prepare_requests(
    scenario: dict[str, Any], factory: PromptFactory
) -> list[PreparedRequest]:
    name = scenario["name"]
    kind = scenario.get("kind", "throughput")
    output_tokens = int(scenario.get("output_tokens", 128))
    temperature = float(scenario.get("temperature", 0.0))
    ignore_eos = bool(scenario.get("ignore_eos", False))
    extra_body = scenario.get("extra_body")

    if kind == "canary":
        requests = []
        repetitions = int(scenario.get("repetitions", 1))
        for repetition in range(repetitions):
            for index, case in enumerate(scenario["cases"]):
                prompt = str(case["prompt"])
                requests.append(PreparedRequest(
                    request_id=f"{name}-{repetition}-{index}",
                    prompt=prompt,
                    output_tokens=int(case.get("output_tokens", output_tokens)),
                    temperature=float(case.get("temperature", temperature)),
                    ignore_eos=False,
                    expected=str(case["expected"]),
                    extra_body=case.get("extra_body", extra_body),
                    prepared_prompt_tokens=factory.client.tokenize_count(prompt),
                ))
        return requests

    count = int(scenario.get("requests", 1))
    target = int(scenario.get("prompt_tokens", 256))
    mode = scenario.get("prompt_mode", "unique")
    group = str(scenario.get("prompt_group", name))
    requests: list[PreparedRequest] = []
    for index in range(count):
        expected = None
        if kind == "needle":
            expected = str(scenario.get("passkey", "ORBIT-7319-CEDAR"))
            prompt = factory.needle_prompt(target, expected, index)
        elif mode == "shared":
            prompt = factory.shared_prompt(group, target, index)
        else:
            stable_name = sum(ord(char) for char in name)
            prompt = factory.unique_prompt(target, index + stable_name)
        requests.append(PreparedRequest(
            request_id=f"{name}-{index}",
            prompt=prompt,
            output_tokens=output_tokens,
            temperature=temperature,
            ignore_eos=ignore_eos,
            expected=expected,
            extra_body=extra_body,
            prepared_prompt_tokens=factory.client.tokenize_count(prompt),
        ))
    return requests
