"""Regression tests for worktree inventory and safe owner-labelled admission."""
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "tools" / "agent_worktrees.py"
SPEC = importlib.util.spec_from_file_location("agent_worktrees", MODULE_PATH)
assert SPEC and SPEC.loader
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout.strip()


class WorktreeLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name)
        self.repo = self.home / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Fixture Owner")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "commit.gpgsign", "false")  # Disposable fixtures only.
        (self.repo / "README.md").write_text("one\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "fixture baseline")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def test_scan_clean_modified_and_untracked(self):
        linked = self.home / "scratch"
        git(self.repo, "worktree", "add", "-b", "fixture", str(linked), self.base)
        (linked / "README.md").write_text("two\n")
        (linked / "new.txt").write_text("untracked\n")
        report = tool.scan_roots([("fixture", self.repo)], workers=2)
        group = report["repositories"][0]
        self.assertEqual(group["summary"]["registered"], 2)
        items = {row["path"]: row for row in group["worktrees"]}
        self.assertEqual(items[str(self.repo)]["status"], "clean")
        self.assertEqual(items[str(linked)]["status"], "dirty")
        self.assertEqual(items[str(linked)]["untracked_entries"], 1)
        self.assertEqual(items[str(linked)]["unstaged"], 1)
        self.assertEqual(group["summary"]["errors"], 0)

    def test_scan_reports_staged_and_missing_without_pruning(self):
        linked = self.home / "gone"
        git(self.repo, "worktree", "add", "--detach", str(linked), self.base)
        (self.repo / "README.md").write_text("staged\n")
        git(self.repo, "add", "README.md")
        report = tool.scan_roots([("fixture", self.repo)])
        self.assertEqual(report["repositories"][0]["summary"]["staged_entries"], 1)
        shutil.rmtree(linked)
        report = tool.scan_roots([("fixture", self.repo)])
        group = report["repositories"][0]
        self.assertEqual(group["summary"]["missing"], 1)
        self.assertTrue(any(w["prunable"] for w in group["worktrees"]))

    def test_admit_idempotent_and_owner_takeover_denied(self):
        state = self.home / "state"
        workspace = self.home / "managed"
        kwargs = dict(
            repo=self.repo, project="fixture", task="issue-123",
            owner="agent-one", purpose="Fix bounded fixture",
            base=self.base, state=state, workspace=workspace,
            trusted_roots={"fixture": str(self.repo)},
        )
        result = tool.admit(**kwargs)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["branch"], "agent/issue-123")
        self.assertEqual(result, tool.admit(**kwargs))
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**{**kwargs, "owner": "agent-two"})
        self.assertTrue((workspace / "fixture" / "issue-123").is_dir())

    def test_no_existing_branch_or_unowned_directory_reuse(self):
        state = self.home / "state"
        workspace = self.home / "managed"
        kwargs = dict(
            repo=self.repo, project="fixture", task="issue-123",
            owner="agent-one", purpose="Fix bounded fixture",
            base=self.base, state=state, workspace=workspace,
            trusted_roots={"fixture": str(self.repo)},
        )
        git(self.repo, "branch", "agent/issue-123")
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**kwargs)
        self.assertFalse(tool.owner_ledger(state, "fixture", "issue-123").exists())
        git(self.repo, "branch", "-D", "agent/issue-123")
        (workspace / "fixture" / "issue-123").mkdir(parents=True)
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**kwargs)

    def test_lease_missing_requires_recovery_and_private_record(self):
        state = self.home / "state"
        workspace = self.home / "managed"
        kwargs = dict(
            repo=self.repo, project="fixture", task="issue-123",
            owner="agent-one", purpose="Fix bounded fixture",
            base=self.base, state=state, workspace=workspace,
            trusted_roots={"fixture": str(self.repo)},
        )
        entry = tool.admit(**kwargs)
        manifest = tool.owner_ledger(state, "fixture", "issue-123")
        self.assertEqual(stat.S_IMODE(manifest.stat().st_mode), 0o600)
        self.assertEqual(json.loads(manifest.read_text())["base_sha"], self.base)
        shutil.rmtree(entry["path"])
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**kwargs)

    def test_admission_requires_trusted_source_and_immutable_sha(self):
        kwargs = dict(
            repo=self.repo, project="fixture", task="issue-123",
            owner="agent-one", purpose="Fix bounded fixture", base=self.base,
            state=self.home / "state", workspace=self.home / "managed",
            trusted_roots={"fixture": str(self.repo)},
        )
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**{**kwargs, "trusted_roots": {}})
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**{**kwargs, "base": "main"})
        with self.assertRaises(tool.AdmissionError):
            tool.admit(**{**kwargs, "trusted_roots": {"fixture": str(self.home)}})
        self.assertFalse((self.home / "managed").exists())

    def test_integrated_clean_lease_cannot_be_reused_on_old_source(self):
        kwargs = dict(
            repo=self.repo, project="fixture", task="retired-task",
            owner="agent-one", purpose="Completed fixture", base=self.base,
            state=self.home / "state", workspace=self.home / "managed",
            trusted_roots={"fixture": str(self.repo)},
        )
        entry = tool.admit(**kwargs)
        (self.repo / "README.md").write_text("new main\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "main advances")
        now = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/remotes/origin/main", now)
        with self.assertRaisesRegex(tool.AdmissionError, "upstream-integrated"):
            tool.admit(**kwargs)
        self.assertTrue(pathlib.Path(entry["path"]).is_dir())
        self.assertEqual(json.loads(tool.owner_ledger(kwargs["state"], "fixture", "retired-task").read_text())["status"], "ready")

    def test_dirty_owned_lease_preserves_unintegrated_work(self):
        kwargs = dict(
            repo=self.repo, project="fixture", task="unfinished-task",
            owner="agent-one", purpose="Unfinished fixture", base=self.base,
            state=self.home / "state", workspace=self.home / "managed",
            trusted_roots={"fixture": str(self.repo)},
        )
        entry = tool.admit(**kwargs)
        (self.repo / "README.md").write_text("new main\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "main advances")
        git(self.repo, "update-ref", "refs/remotes/origin/main", git(self.repo, "rev-parse", "HEAD"))
        (pathlib.Path(entry["path"]) / "README.md").write_text("unique uncommitted work\n")
        self.assertEqual(tool.admit(**kwargs)["path"], entry["path"])
        self.assertEqual((pathlib.Path(entry["path"]) / "README.md").read_text(), "unique uncommitted work\n")

    def test_reconcile_reports_merged_and_dirty_without_reaping(self):
        state, workspace = self.home / "state", self.home / "managed"
        kwargs = dict(repo=self.repo, project="fixture", task="merged-task",
                      owner="agent-one", purpose="Tracked task", base=self.base,
                      state=state, workspace=workspace,
                      trusted_roots={"fixture": str(self.repo)})
        ready = tool.admit(**kwargs)
        dirty = self.home / "untracked-worktree"
        git(self.repo, "worktree", "add", "-b", "uncommitted", str(dirty), self.base)
        (dirty / "new.txt").write_text("unique evidence\n")
        (self.repo / "README.md").write_text("new main\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "new main")
        now = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/remotes/origin/main", now)
        report = tool.reconcile_upstreams([("fixture", self.repo)], {"fixture": now}, state)
        group = report["repositories"][0]
        self.assertEqual(group["errors"], [])
        by_path = {row["path"]: row for row in group["worktrees"]}
        self.assertEqual(by_path[str(self.repo)]["disposition"], "canonical-current")
        self.assertEqual(by_path[ready["path"]]["disposition"], "upstream-integrated-needs-owner-retirement")
        self.assertEqual(by_path[ready["path"]]["lease"]["owner"], "agent-one")
        self.assertEqual(by_path[str(dirty)]["disposition"], "needs-review")
        self.assertTrue((dirty / "new.txt").exists())
        self.assertTrue(pathlib.Path(ready["path"]).exists())

    def test_reconcile_does_not_assert_unverified_upstream(self):
        now = git(self.repo, "rev-parse", "HEAD")
        report = tool.reconcile_upstreams(
            [("fixture", self.repo)], {"fixture": now}, self.home / "state"
        )
        group = report["repositories"][0]
        self.assertTrue(group["errors"])
        self.assertTrue(all(row["disposition"] == "unsafe/unknown"
                            for row in group["worktrees"]))

    def test_bad_identifiers_and_duplicate_roots_fail_closed(self):
        with self.assertRaises(tool.AdmissionError):
            tool.verify_name("../unsafe")
        report = tool.scan_roots([("one", self.repo), ("two", self.repo)])
        self.assertIn("Duplicate Git common directory", report["repositories"][1]["errors"][0])


if __name__ == "__main__":
    unittest.main()
