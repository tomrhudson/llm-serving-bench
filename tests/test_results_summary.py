import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ResultsSummaryTests(unittest.TestCase):
    def test_generated_results_summary_is_current(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/generate_results_summary.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
