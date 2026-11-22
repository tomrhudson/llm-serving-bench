"""Adapters for the sampled RULER, LongBench v2, and local τ²-Bench protocols."""

from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re
import runpy
import shutil
from statistics import mean
import subprocess
import sys
from tempfile import NamedTemporaryFile
from types import ModuleType
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "spark-bench-capability-samples-v1"
SEED = 42
RULER_LENGTHS = (4096, 32768, 131072)
RULER_SAMPLES = 2
LONG_BENCH_OUTPUT = 128
TAU_DOMAINS = ("airline", "retail", "telecom")
TAU_CASES = 3
NORMAL_TAU_ENDINGS = {"user_stop", "agent_stop", "max_steps"}
SOURCES = {
    "RULER": ("NVIDIA/RULER", "db43f92ff634bbce1c33d1fb15858aec4bba509a"),
    "LongBench": ("THUDM/LongBench", "2e00731f8d0bff23dc4325161044d0ed8af94c1e"),
    "tau2-bench": ("sierra-research/tau2-bench", "768f3d8fe8528b4f32a5096f9ed008ae50f48ead"),
}
DATASETS = {
    "english_words.json": (
        "https://media.githubusercontent.com/media/NVIDIA/RULER/"
        f"{SOURCES['RULER'][1]}/scripts/data/synthetic/json/english_words.json",
        "affcd6d45fdf3cc843d585c99c97ad615094e760e6c4756b654bab6c73bc2eca",
    ),
    "squad.json": (
        "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json",
        "80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8",
    ),
    "hotpotqa.json": (
        "https://huggingface.co/datasets/namlh2004/hotpotqa/resolve/"
        "7e54db4656209750ff487f6fdf8e39a66dba136b/hotpot_dev_distractor_v1.json",
        "e3da074df24e8369009918aa5cdbdd254dadcde4c63f7569d36afd6f2268caa8",
    ),
    "longbench-data.json": (
        "https://huggingface.co/datasets/THUDM/LongBench-v2/resolve/"
        "2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9/data.json",
        "15d61c22d92c96900b3c4948b6aeea218d3214b676a65df48e7b8555604c7fe2",
    ),
}
CONTEXT_DEPENDENCIES = (
    "tokenizers==0.23.3", "nltk==3.10.4", "numpy==2.5.5", "scipy==1.18.1",
    "wonderwords==3.0.1", "tqdm==4.70.1", "PyYAML==6.0.4",
    "html2text==2025.4.15", "beautifulsoup4==4.15.0",
)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path, value):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def download_dataset(name, destination):
    url, expected_sha = DATASETS[name]
    temp = destination.with_suffix(".download")
    with urlopen(url, timeout=120) as response, temp.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    if sha256(temp) != expected_sha:
        raise ValueError(f"{name} does not match the pinned dataset checksum")
    temp.replace(destination)


def upstream_function(path, name):
    # The pinned scorers are standalone. Loading only the function avoids the
    # upstream CLIs' model clients and unrelated inference dependencies.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


def run_ruler_generator():
    from tokenizers import Tokenizer

    script, *arguments = sys.argv[2:]
    sys.argv = [script, *arguments]
    sys.path[:0] = [str(Path(script).parent), str(Path(script).parent.parent)]
    # The RULER generators only use the length of text_to_tokens(). Loading a
    # local tokenizer.json provides that count without model code or weights.
    adapter = ModuleType("tokenizer")

    def select_tokenizer(_kind, path):
        tokenizer = Tokenizer.from_file(path)

        class RulerTokenizer:
            def text_to_tokens(self, text):
                return tokenizer.encode(text, add_special_tokens=False).ids

        return RulerTokenizer()

    adapter.select_tokenizer = select_tokenizer
    sys.modules["tokenizer"] = adapter
    runpy.run_path(script, run_name="__main__")


def prepare_ruler_assets(source, work, essays):
    import nltk

    data = source / "data" / "synthetic" / "json"
    for name in ("english_words.json", "squad.json", "hotpotqa.json"):
        download_dataset(name, data / name)
    essay_file = data / "PaulGrahamEssays.json"
    if essays:
        shutil.copyfile(essays, essay_file)
    else:
        urls = data / "PaulGrahamEssays_URLs.txt"
        urls.write_text(urls.read_text().replace(
            "http://www.paulgraham.com/", "https://paulgraham.com/"
        ))
        generated = subprocess.run(
            [sys.executable, "download_paulgraham_essay.py"], cwd=data,
            capture_output=True, text=True, timeout=1800, check=True,
        )
        if "Fail download " in generated.stdout:
            raise RuntimeError("RULER essay download was partial; supply a complete corpus with --ruler-essays")
    if not read_json(essay_file).get("text", "").strip():
        raise ValueError("RULER essay corpus has no text")
    nltk_data = work / "nltk-data"
    nltk_data.mkdir()
    nltk.download("punkt_tab", download_dir=str(nltk_data), raise_on_error=True, quiet=True)
    return sha256(essay_file), nltk_data


def run_ruler(source, work, settings, request):
    import yaml

    tasks = yaml.safe_load((source / "synthetic.yaml").read_text(encoding="utf-8"))
    if len(tasks) != 13:
        raise ValueError("RULER must contain the 13 pinned task variants")
    data_constants = runpy.run_path(str(source / "data/synthetic/constants.py"))["TASKS"]
    metrics = runpy.run_path(str(source / "eval/synthetic/constants.py"))["TASKS"]
    postprocess = upstream_function(source / "eval/evaluate.py", "postprocess_pred")
    essay_sha, nltk_data = prepare_ruler_assets(source, work, settings.get("ruler_essays"))
    generation_env = dict(os.environ, NLTK_DATA=str(nltk_data), TOKENIZERS_PARALLELISM="false")
    results = {}
    with (work / "ruler.jsonl").open("w", encoding="utf-8", buffering=1) as stream:
        for length in settings["ruler_lengths"]:
            scores, errors, prompt_tokens = {}, 0, []
            for task, definition in tasks.items():
                kind = definition["task"]
                spec = data_constants[kind]
                output_cap = spec["tokens_to_generate"]
                target = work / "ruler-data" / str(length)
                template = spec["template"] + spec.get("answer_prefix", "")
                command = [
                    sys.executable, __file__, "ruler-generator",
                    str(source / "data" / "synthetic" / f"{kind}.py"),
                    "--save_dir", str(target), "--save_name", task,
                    "--tokenizer_path", str(work / "tokenizer.json"), "--tokenizer_type", "hf",
                    "--max_seq_length", str(length), "--tokens_to_generate", str(output_cap),
                    "--num_samples", str(RULER_SAMPLES), "--random_seed", str(SEED),
                    "--template", template,
                ]
                for name, value in definition["args"].items():
                    command.extend([f"--{name}", str(value)])
                subprocess.run(command, env=generation_env, timeout=1800, check=True)
                path = target / task / "validation.jsonl"
                cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                if len(cases) != RULER_SAMPLES or len({row["index"] for row in cases}) != RULER_SAMPLES:
                    raise ValueError(f"RULER generated incorrect coverage for {task} at {length}")
                predictions, references = [], []
                for row in cases:
                    result = request(row["input"], 0, output_cap)
                    stream.write(json.dumps({"length": length, "task": task, **row, **result}) + "\n")
                    errors += int("error" in result)
                    token_count = (result.get("usage") or {}).get("prompt_tokens")
                    if token_count is not None:
                        prompt_tokens.append(token_count)
                    predictions.append(postprocess(result.get("prediction", ""), definition))
                    references.append(row["outputs"])
                scores[task] = {
                    "score": metrics[kind]["metric_fn"](predictions, references),
                    "empty_responses": predictions.count(""),
                }
            results[str(length)] = {
                "tasks": scores, "macro_score": mean(row["score"] for row in scores.values()),
                "cases": len(tasks) * RULER_SAMPLES, "request_errors": errors,
                "served_prompt_token_range": [min(prompt_tokens), max(prompt_tokens)]
                if prompt_tokens else None,
            }
    return {
        "complete": (
            tuple(settings["ruler_lengths"]) == RULER_LENGTHS
            and all(row["request_errors"] == 0 for row in results.values())
        ),
        "essay_sha256": essay_sha, "lengths": results,
    }


def select_longbench(data):
    rng = random.Random(SEED)
    for domain in sorted({row["domain"] for row in data}):
        pool = sorted((row for row in data if row["domain"] == domain), key=lambda row: row["_id"])
        used = set()
        for length, difficulty in (("short", "easy"), ("medium", "hard"),
                                   ("long", "easy"), ("short", "hard")):
            candidates = [row for row in pool if row["_id"] not in used and row["length"] == length]
            if not candidates:
                candidates = [row for row in pool if row["_id"] not in used and row["length"] == "medium"]
            row = rng.choice([row for row in candidates if row["difficulty"] == difficulty] or candidates)
            used.add(row["_id"])
            yield row


def run_longbench(source, work, settings, request):
    from tokenizers import Tokenizer

    dataset = work / "longbench-data.json"
    download_dataset(dataset.name, dataset)
    selected = list(select_longbench(read_json(dataset)))
    if len(selected) != 24:
        raise ValueError("LongBench v2 must select 24 questions")
    tokenizer = Tokenizer.from_file(str(work / "tokenizer.json"))
    template = (source / "prompts/0shot.txt").read_text(encoding="utf-8")
    extract_answer = upstream_function(source / "pred.py", "extract_answer")
    results = []
    with (work / "longbench.jsonl").open("w", encoding="utf-8", buffering=1) as stream:
        for row in selected:
            prompt = template.replace("$Q$", row["question"])
            for choice in "ABCD":
                prompt = prompt.replace(f"$C_{choice}$", row[f"choice_{choice}"])
            prompt = prompt.replace("$DOC$", row["context"].strip())
            tokens = tokenizer.encode(prompt, add_special_tokens=False).ids
            truncated = len(tokens) > settings["longbench_prompt_cap"]
            if truncated:
                halves = settings["longbench_prompt_cap"] // 2
                prompt = (tokenizer.decode(tokens[:halves], skip_special_tokens=False)
                          + tokenizer.decode(tokens[-halves:], skip_special_tokens=False))
            result = request(prompt, 0.1, LONG_BENCH_OUTPUT)
            answer = extract_answer(result.get("prediction", ""))
            case = {key: row[key] for key in ("_id", "domain", "length", "difficulty", "answer")}
            case.update(result, correct=answer == row["answer"], parsed_answer=answer,
                        source_tokens=len(tokens), truncated=truncated)
            stream.write(json.dumps(case) + "\n")
            results.append(case)

    def summarize(rows):
        correct = sum(row["correct"] for row in rows)
        return {
            "cases": len(rows), "correct": correct, "accuracy": correct / len(rows),
            "unparseable": sum("error" not in row and row["parsed_answer"] is None for row in rows),
            "unparseable_at_output_limit": sum(
                row.get("finish_reason") == "length" and row["parsed_answer"] is None for row in rows
            ),
            "request_errors": sum("error" in row for row in rows),
            "truncated": sum(row["truncated"] for row in rows),
        }

    overall = summarize(results)
    return {
        "complete": overall["request_errors"] == 0,
        "prompt_cap": settings["longbench_prompt_cap"],
        "overall": overall,
        **{field: {value: summarize([row for row in results if row[field] == value])
                   for value in sorted({row[field] for row in results})}
           for field in ("domain", "length")},
    }


def context_evaluation(stage, work, settings, connection):
    sys.path.insert(0, str(ROOT))
    from llm_serving_bench.client import OpenAIClient

    api_key = os.environ.pop("LLM_SERVING_BENCH_ENDPOINT_KEY", None)
    client = OpenAIClient(connection["base_url"], connection["model"], api_key, settings["timeout"])

    def request(prompt, temperature, output_cap):
        try:
            response = client.chat_completion(prompt, output_cap, temperature, settings["extra_body"])
            choice = response["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                return {"error": "invalid completion message"}
            content = message.get("content")
            usage = response.get("usage")
            if content is not None and not isinstance(content, str):
                return {"error": "invalid completion content"}
            if usage is not None and not isinstance(usage, dict):
                return {"error": "invalid completion usage"}
            return {"prediction": content or "", "finish_reason": choice.get("finish_reason"),
                    "usage": usage}
        except (OSError, ValueError, RuntimeError, KeyError, IndexError, TypeError) as exc:
            return {"error": type(exc).__name__}

    sources = work / "sources"
    if stage == "ruler":
        if settings["ruler_lengths"]:
            result = run_ruler(sources / "RULER/scripts", work, settings, request)
        else:
            result = {"complete": False, "lengths": {}, "reason": "context window below minimum"}
    else:
        result = run_longbench(sources / "LongBench", work, settings, request)
    write_json(work / f"{stage}-summary.json", result)


def tau_task_ids(domain_path):
    base = set(read_json(domain_path / "split_tasks.json")["base"])
    tasks = read_json(domain_path / "tasks.json")
    pool = [task["id"] for task in tasks if task["id"] in base
            and not task["evaluation_criteria"].get("communicate_info")]
    return random.Random(SEED).sample(sorted(pool), TAU_CASES)


def summarize_tau(simulations, task_ids):
    endings = Counter(row.get("termination_reason") for row in simulations)
    graded = [row for row in simulations
              if row.get("termination_reason") in NORMAL_TAU_ENDINGS
              and isinstance((row.get("reward_info") or {}).get("reward"), (int, float))]
    rewards = [row["reward_info"]["reward"] for row in graded]
    return {
        "complete": (
            Counter(row.get("task_id") for row in graded) == Counter(task_ids)
            and len(simulations) == len(task_ids)
        ),
        "expected": len(task_ids), "graded": len(graded),
        "full_reward": rewards.count(1), "mean_reward": mean(rewards) if rewards else None,
        "termination_reasons": {str(key): value for key, value in endings.items()},
    }


def tau_domain(work, settings, connection, domain):
    from tau2.cli import main
    from tau2.evaluator import evaluator_nl_assertions

    model = f"openai/{connection['model']}"
    arguments = {"api_base": connection["base_url"], "temperature": 0, "max_tokens": 1024}
    if settings["extra_body"]:
        arguments["extra_body"] = settings["extra_body"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = model
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = arguments
    data = work / "sources/tau2-bench/data/tau2/domains" / domain
    ids = tau_task_ids(data)
    output = work / "tau2" / domain
    sys.argv = [
        "tau2", "run", "--benchmark", "none", "--domain", domain,
        "--agent-llm", model, "--agent-llm-args", json.dumps(arguments),
        "--user-llm", model, "--user-llm-args", json.dumps(arguments),
        "--num-trials", "1", "--seed", str(SEED), "--max-steps", "60", "--timeout", "420",
        "--max-concurrency", "1", "--max-retries", "1", "--communicate-scorer", "substring",
        "--log-level", "WARNING", "--save-to", str(output), "--task-ids", *ids,
    ]
    main()
    simulations = read_json(output / "results.json")["simulations"]
    write_json(work / f"tau2-{domain}-summary.json", summarize_tau(simulations, ids))


if __name__ == "__main__":
    if sys.argv[1] == "ruler-generator":
        run_ruler_generator()
    else:
        stage, directory = sys.argv[1:3]
        work = Path(directory)
        settings = read_json(work / "settings.json")
        connection = {"model": os.environ["LLM_SERVING_BENCH_MODEL"],
                      "base_url": os.environ["LLM_SERVING_BENCH_BASE_URL"]}
        if stage in ("ruler", "longbench"):
            context_evaluation(stage, work, settings, connection)
        else:
            tau_domain(work, settings, connection, stage)
