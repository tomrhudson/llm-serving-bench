#!/usr/bin/env python3
"""Fail when tracked publication surfaces contain high-confidence private data."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_IDENTIFIER_HASHES = {
    "786578600c7bb8cdd3967a052689d8c8f98e31ee4ed41d19a052d499f6c47866": "private host identifier",
    "49304fdead364a98f7d9dcfc05649af6993d036016c3f5b75616900db357694c": "private route identifier",
}
BLOCKED_EMAIL_HASHES = {
    "e6af86b867c529609ba5fa9fb7ae8efbd4c0118530613f47c2acc1e39aa17ef6"
}
# This GitHub-created squash commit was already public before the history check
# first ran on main. Removing its author identity would require rewriting public
# history, so accept only the exact immutable commit/role/email combination. A
# future commit using the same address (including another squash merge) remains
# blocked.
KNOWN_PUBLISHED_COMMIT_IDENTITY_EXCEPTIONS = {
    (
        "39c95e272cb9d8d7ecba2100a44cc1ed4f4d26cd",
        "author",
        "e6af86b867c529609ba5fa9fb7ae8efbd4c0118530613f47c2acc1e39aa17ef6",
    )
}
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+")
RULES = [
    (
        "private IPv4 address",
        re.compile(
            r"(?<![0-9])(?:10(?:\.[0-9]{1,3}){3}|192\.168(?:\.[0-9]{1,3}){2}|"
            r"172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2})(?![0-9])"
        ),
    ),
    ("private key material", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("OpenAI-style token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("user home path", re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/")),
]


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True
    ).stdout


def digest(value: str) -> str:
    return hashlib.sha256(value.casefold().encode("utf-8")).hexdigest()


def scan_text(label: str, raw: bytes) -> list[str]:
    if b"\0" in raw:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []

    issues: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule_name, pattern in RULES:
            if pattern.search(line):
                issues.append(f"{label}:{line_number}: {rule_name}")
        for token in TOKEN.findall(line):
            blocked = BLOCKED_IDENTIFIER_HASHES.get(digest(token))
            if blocked:
                issues.append(f"{label}:{line_number}: {blocked}")
        for email in EMAIL.findall(line):
            if digest(email) in BLOCKED_EMAIL_HASHES:
                issues.append(f"{label}:{line_number}: private email address")
    return issues


def scan_current_tree() -> list[str]:
    issues: list[str] = []
    for relative in git("ls-files", "-z").decode("utf-8").split("\0"):
        if not relative:
            continue
        issues.extend(scan_text(relative, (ROOT / relative).read_bytes()))
    return issues


def synthetic_pull_request_merge_commits() -> set[str]:
    """Return the current GitHub-generated PR merge commit, when present.

    GitHub Actions checks out a temporary two-parent merge for pull_request
    workflows. Its author identity is synthesized from the repository owner,
    so it is not publication history controlled by either branch. The parents
    and every reachable blob remain in scope; only that temporary commit's
    author/committer identity is excluded.
    """

    if os.environ.get("GITHUB_ACTIONS") != "true":
        return set()
    if os.environ.get("GITHUB_EVENT_NAME") not in {"pull_request", "pull_request_target"}:
        return set()

    fields = git(
        "show",
        "-s",
        "--format=%H%x00%P%x00%an%x00%ae%x00%cn%x00%ce%x00%s",
        "HEAD",
    ).decode("utf-8").strip().split("\0")
    if len(fields) != 7:
        return set()

    commit, parents, _author_name, _author_email, committer_name, committer_email, subject = fields
    if len(parents.split()) != 2:
        return set()
    if committer_name != "GitHub" or committer_email != "noreply@github.com":
        return set()
    if not re.fullmatch(r"Merge [0-9a-f]{7,40} into [0-9a-f]{7,40}", subject):
        return set()
    return {commit}


def scan_history() -> list[str]:
    issues: list[str] = []
    ignored_commit_identities = synthetic_pull_request_merge_commits()
    seen: set[str] = set()
    for entry in git("rev-list", "--objects", "--all").decode("utf-8").splitlines():
        object_id, separator, path = entry.partition(" ")
        if not separator or object_id in seen:
            continue
        seen.add(object_id)
        if git("cat-file", "-t", object_id).strip() != b"blob":
            continue
        issues.extend(scan_text(f"{object_id[:12]}:{path}", git("cat-file", "-p", object_id)))

    for line in git("log", "--all", "--format=%H%x09%ae%x09%ce").decode("utf-8").splitlines():
        commit, author_email, committer_email = line.split("\t", 2)
        if commit in ignored_commit_identities:
            continue
        for role, email in (("author", author_email), ("committer", committer_email)):
            email_hash = digest(email)
            if email_hash not in BLOCKED_EMAIL_HASHES:
                continue
            identity = (commit, role, email_hash)
            if identity in KNOWN_PUBLISHED_COMMIT_IDENTITY_EXCEPTIONS:
                continue
            issues.append(f"{commit[:12]}: {role} uses a private email address")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--history",
        action="store_true",
        help="also scan every blob and commit identity reachable from local refs",
    )
    args = parser.parse_args()

    issues = scan_history() if args.history else scan_current_tree()
    if issues:
        print("Publication hygiene check failed:")
        for issue in sorted(set(issues)):
            print(f"- {issue}")
        return 1
    print("Publication hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
