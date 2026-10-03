import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_publication_hygiene",
    ROOT / "scripts/check_publication_hygiene.py",
)
assert SPEC and SPEC.loader
HYGIENE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HYGIENE)


class PublicationHygieneTests(unittest.TestCase):
    def scan_history_with_log(
        self,
        log: bytes,
        *,
        blocked_email_hashes: set[str],
        exceptions: set[tuple[str, str, str]],
    ) -> list[str]:
        def fake_git(*args: str) -> bytes:
            if args[:2] == ("rev-list", "--objects"):
                return b""
            if args[:2] == ("log", "--all"):
                return log
            raise AssertionError(f"unexpected git invocation: {args}")

        with (
            patch.object(HYGIENE, "git", side_effect=fake_git),
            patch.object(HYGIENE, "synthetic_pull_request_merge_commits", return_value=set()),
            patch.object(HYGIENE, "BLOCKED_EMAIL_HASHES", blocked_email_hashes),
            patch.object(
                HYGIENE,
                "KNOWN_PUBLISHED_COMMIT_IDENTITY_EXCEPTIONS",
                exceptions,
            ),
        ):
            return HYGIENE.scan_history()

    def test_synthetic_pr_merge_identity_is_ignored_in_actions(self) -> None:
        commit = "a" * 40
        parent_a = "b" * 40
        parent_b = "c" * 40
        metadata = (
            f"{commit}\0{parent_a} {parent_b}\0Tom Hudson\0private@example.com\0"
            f"GitHub\0noreply@github.com\0Merge {parent_b} into {parent_a}\n"
        ).encode()

        with (
            patch.dict(
                os.environ,
                {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "pull_request"},
                clear=False,
            ),
            patch.object(HYGIENE, "git", return_value=metadata),
        ):
            self.assertEqual(HYGIENE.synthetic_pull_request_merge_commits(), {commit})

    def test_non_github_merge_identity_remains_in_scope(self) -> None:
        commit = "a" * 40
        parent_a = "b" * 40
        parent_b = "c" * 40
        metadata = (
            f"{commit}\0{parent_a} {parent_b}\0Tom Hudson\0private@example.com\0"
            f"Tom Hudson\0private@example.com\0Merge {parent_b} into {parent_a}\n"
        ).encode()

        with (
            patch.dict(
                os.environ,
                {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "pull_request"},
                clear=False,
            ),
            patch.object(HYGIENE, "git", return_value=metadata),
        ):
            self.assertEqual(HYGIENE.synthetic_pull_request_merge_commits(), set())

    def test_local_runs_do_not_ignore_head(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(HYGIENE.synthetic_pull_request_merge_commits(), set())

    def test_known_published_identity_exception_is_exact(self) -> None:
        commit = "a" * 40
        private_email = "private@example.com"
        email_hash = HYGIENE.digest(private_email)
        log = f"{commit}\t{private_email}\tnoreply@github.com\n".encode()

        self.assertEqual(
            self.scan_history_with_log(
                log,
                blocked_email_hashes={email_hash},
                exceptions={(commit, "author", email_hash)},
            ),
            [],
        )

    def test_known_identity_remains_blocked_in_another_commit(self) -> None:
        excepted_commit = "a" * 40
        other_commit = "b" * 40
        private_email = "private@example.com"
        email_hash = HYGIENE.digest(private_email)
        log = f"{other_commit}\t{private_email}\tnoreply@github.com\n".encode()

        self.assertEqual(
            self.scan_history_with_log(
                log,
                blocked_email_hashes={email_hash},
                exceptions={(excepted_commit, "author", email_hash)},
            ),
            [f"{other_commit[:12]}: author uses a private email address"],
        )

    def test_known_identity_remains_blocked_in_another_role(self) -> None:
        commit = "a" * 40
        private_email = "private@example.com"
        email_hash = HYGIENE.digest(private_email)
        log = f"{commit}\tnoreply@github.com\t{private_email}\n".encode()

        self.assertEqual(
            self.scan_history_with_log(
                log,
                blocked_email_hashes={email_hash},
                exceptions={(commit, "author", email_hash)},
            ),
            [f"{commit[:12]}: committer uses a private email address"],
        )


if __name__ == "__main__":
    unittest.main()
