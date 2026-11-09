"""Recovery snapshots preserve staged and unstaged state without touching source."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))
import agent_worktrees
import worktree_triage
import capture_worktrees


def git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


class CaptureTests(unittest.TestCase):
    def test_separate_index_and_worktree_and_untracked(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            repo = root / "repo"
            repo.mkdir()
            git(repo, "init", "-b", "main")
            git(repo, "config", "user.name", "Fixture")
            git(repo, "config", "user.email", "fixture@example.invalid")
            git(repo, "config", "commit.gpgsign", "false")
            (repo / "README.md").write_text("base\n")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "fixture")
            (repo / "README.md").write_text("stage\n")
            git(repo, "add", "README.md")
            (repo / "README.md").write_text("unstaged\n")
            (repo / "untracked.txt").write_text("must not copy\n")
            report = agent_worktrees.scan_roots([("fixture", repo)])
            triage = worktree_triage.triage(report, workers=1)
            after_before = git(repo, "status", "--porcelain")
            dest = root / "capture"
            result = capture_worktrees.capture(triage, dest)
            self.assertEqual(len(result["records"]), 1)
            entry = result["records"][0]
            self.assertEqual(entry["status"], "captured")
            self.assertEqual(entry["untracked"]["count"], 1)
            self.assertEqual(
                entry["head_to_worktree"]["sha256"], entry["expected_patch_sha256"]
            )
            self.assertNotEqual(
                entry["head_to_index"]["sha256"],
                entry["index_to_worktree"]["sha256"],
            )
            self.assertEqual(git(repo, "status", "--porcelain"), after_before)
            self.assertFalse(any(dest.rglob("untracked.txt")))
            self.assertTrue((dest / "capture-manifest.json").is_file())
            with self.assertRaises(RuntimeError):
                capture_worktrees.capture(triage, dest)


if __name__ == "__main__":
    unittest.main()
