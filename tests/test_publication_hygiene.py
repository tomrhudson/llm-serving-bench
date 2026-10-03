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


if __name__ == "__main__":
    unittest.main()
