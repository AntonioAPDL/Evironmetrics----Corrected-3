from __future__ import annotations

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_overleaf_sync.py"
SPEC = importlib.util.spec_from_file_location("overleaf_sync_guard", SCRIPT)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class OverleafSyncGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote, self.local, self.editor = [self.base / p for p in ("remote.git", "local", "editor")]
        self.env = os.environ.copy()
        self.env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        self.git(self.base, "init", "--bare", "-q", "-b", "main", str(self.remote))
        self.git(self.base, "init", "-q", "-b", "main", str(self.local))
        self.identify(self.local)
        (self.local / "article.tex").write_text("Initial article.\n")
        self.git(self.local, "add", "article.tex")
        self.git(self.local, "commit", "-q", "-m", "Initial")
        self.git(self.local, "remote", "add", "origin", str(self.remote))
        self.git(self.local, "push", "-q", "-u", "origin", "main")
        self.git(self.base, "clone", "-q", str(self.remote), str(self.editor))
        self.identify(self.editor)
        self.branch = "overleaf-2026-11-09-0005"

    def git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull,
                                 "-C", str(repo), *args], env=self.env,
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def identify(self, repo: Path) -> None:
        self.git(repo, "config", "user.name", "Guard test")
        self.git(repo, "config", "user.email", "guard@example.invalid")

    def overleaf_edit(self, content: str = "Overleaf source edit.\n") -> str:
        self.git(self.editor, "checkout", "-q", "-B", self.branch)
        (self.editor / "article.tex").write_text(content)
        self.git(self.editor, "add", "article.tex")
        self.git(self.editor, "commit", "-q", "-m", "Overleaf edit")
        self.git(self.editor, "push", "-q", "origin", self.branch)
        return self.git(self.editor, "rev-parse", "HEAD")

    def fetch(self) -> None:
        self.git(self.local, "fetch", "-q", "origin")

    def test_no_overleaf_branches_passes_without_mutation(self) -> None:
        before = self.git(self.local, "show-ref")
        self.assertEqual(guard.check_sync(self.local, "origin", "HEAD"), [])
        self.assertEqual(self.git(self.local, "show-ref"), before)
        self.assertEqual(self.git(self.local, "status", "--porcelain"), "")

    def test_unfetched_live_branch_blocks_without_automatic_fetch(self) -> None:
        oid = self.overleaf_edit()
        with self.assertRaisesRegex(guard.SyncCheckError, "not available locally"):
            guard.check_sync(self.local, "origin", "HEAD")
        result = subprocess.run(["git", "-C", str(self.local), "cat-file", "-e", oid],
                                text=True, capture_output=True, env=self.env)
        self.assertNotEqual(result.returncode, 0)

    def test_known_unmerged_branch_blocks(self) -> None:
        self.overleaf_edit()
        self.fetch()
        with self.assertRaisesRegex(guard.SyncCheckError, "not merged"):
            guard.check_sync(self.local, "origin", "HEAD")

    def test_merged_branch_passes_even_if_review_retains_main_tree(self) -> None:
        self.overleaf_edit()
        self.fetch()
        before = self.git(self.local, "rev-parse", "HEAD^{tree}")
        self.git(self.local, "merge", "-q", "--no-ff", "-s", "ours", "--no-edit", "origin/" + self.branch)
        self.assertEqual(self.git(self.local, "rev-parse", "HEAD^{tree}"), before)
        self.assertEqual(guard.check_sync(self.local, "origin", "HEAD"), ["refs/heads/" + self.branch])

    def test_generated_file_deletion_also_requires_reviewed_history_merge(self) -> None:
        (self.local / "generated.txt").write_text("Preserved generated content.\n")
        self.git(self.local, "add", "generated.txt")
        self.git(self.local, "commit", "-q", "-m", "Generated content")
        self.git(self.local, "push", "-q", "origin", "main")
        self.git(self.editor, "fetch", "-q", "origin")
        self.git(self.editor, "checkout", "-q", "-b", self.branch, "origin/main")
        self.git(self.editor, "rm", "-q", "generated.txt")
        self.git(self.editor, "commit", "-q", "-m", "Generated file absent from Overleaf export")
        self.git(self.editor, "push", "-q", "origin", self.branch)
        self.fetch()
        with self.assertRaisesRegex(guard.SyncCheckError, "not merged"):
            guard.check_sync(self.local, "origin", "HEAD")
        before = self.git(self.local, "rev-parse", "HEAD^{tree}")
        self.git(self.local, "merge", "-q", "--no-ff", "-s", "ours", "--no-edit", "origin/" + self.branch)
        self.assertEqual(self.git(self.local, "rev-parse", "HEAD^{tree}"), before)
        self.assertTrue((self.local / "generated.txt").is_file())
        self.assertEqual(len(guard.check_sync(self.local, "origin", "HEAD")), 1)

    def test_overleaf_edit_after_sync_blocks_despite_stale_tracking_ref(self) -> None:
        self.overleaf_edit()
        self.fetch()
        self.git(self.local, "merge", "-q", "--no-edit", "origin/" + self.branch)
        stale = self.git(self.local, "rev-parse", "origin/" + self.branch)
        latest = self.overleaf_edit("A second Overleaf edit after the previous synchronization.\n")
        self.assertNotEqual(stale, latest)
        with self.assertRaisesRegex(guard.SyncCheckError, "not available locally"):
            guard.check_sync(self.local, "origin", "HEAD")
        self.assertEqual(self.git(self.local, "rev-parse", "origin/" + self.branch), stale)

    def test_every_live_branch_must_be_merged(self) -> None:
        self.overleaf_edit()
        self.fetch()
        self.git(self.local, "merge", "-q", "--no-edit", "origin/" + self.branch)
        self.branch = "overleaf-second"
        self.overleaf_edit("Another pending branch.\n")
        self.fetch()
        with self.assertRaisesRegex(guard.SyncCheckError, "overleaf-second"):
            guard.check_sync(self.local, "origin", "HEAD")

    def test_nonmain_push_skips_network_and_main_deletion_blocks(self) -> None:
        oid = self.git(self.local, "rev-parse", "HEAD")
        zeros = "0" * len(oid)
        with mock.patch.object(guard, "check_sync") as check:
            with mock.patch("sys.stdin", io.StringIO(f"refs/heads/topic {oid} refs/heads/topic {zeros}\n")):
                self.assertEqual(guard.main(["--repo", str(self.local), "--pre-push", "origin", "unreachable"]), 0)
            check.assert_not_called()
            with mock.patch("sys.stdin", io.StringIO(f"(delete) {zeros} refs/heads/main {oid}\n")):
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(guard.main(["--repo", str(self.local), "--pre-push", "origin", "unreachable"]), 1)
            self.assertIn("Deleting main", errors.getvalue())
            check.assert_not_called()

    def test_malformed_updates_are_rejected(self) -> None:
        with self.assertRaisesRegex(guard.SyncCheckError, "Malformed"):
            guard.proposed_main("missing update fields\n")
        with self.assertRaisesRegex(guard.SyncCheckError, "Invalid"):
            guard.proposed_main("refs/heads/main not-an-object refs/heads/main " + "0" * 40)

    def test_actual_proposed_main_is_checked_not_checkout(self) -> None:
        initial = self.git(self.local, "rev-parse", "HEAD")
        self.overleaf_edit()
        self.fetch()
        self.git(self.local, "merge", "-q", "--no-edit", "origin/" + self.branch)
        with mock.patch("sys.stdin", io.StringIO(f"refs/heads/old {initial} refs/heads/main {initial}\n")):
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(guard.main(["--repo", str(self.local), "--pre-push", "origin", str(self.remote)]), 1)
        self.assertIn("not merged", errors.getvalue())

    def test_query_failure_and_timeout_do_not_expose_remote_credentials(self) -> None:
        secret = "https://person:secret@example.invalid/private.git"
        original = guard.git
        def fail_query(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
            if args[0] == "ls-remote":
                return subprocess.CompletedProcess(args, 128, "", "fatal: " + secret)
            return original(repo, *args)
        with mock.patch.object(guard, "git", side_effect=fail_query):
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(guard.main(["--repo", str(self.local), "--remote", secret]), 1)
            self.assertNotIn(secret, errors.getvalue())
            self.assertNotIn("person", errors.getvalue())
        with mock.patch.object(guard.subprocess, "run", side_effect=subprocess.TimeoutExpired(secret, 45)):
            with self.assertRaises(guard.SyncCheckError) as raised:
                guard.git(self.local, "ls-remote", secret)
            self.assertNotIn(secret, str(raised.exception))

    def test_real_hook_blocks_then_allows_normal_main_push_after_merge(self) -> None:
        (self.local / "scripts").mkdir()
        (self.local / ".githooks").mkdir()
        shutil.copy2(SCRIPT, self.local / "scripts/check_overleaf_sync.py")
        hook = self.local / ".githooks/pre-push"
        shutil.copy2(ROOT / ".githooks/pre-push", hook)
        hook.chmod(0o755)
        self.git(self.local, "config", "core.hooksPath", ".githooks")
        initial_remote = self.git(self.remote, "rev-parse", "main")
        self.overleaf_edit()
        (self.local / "article.tex").write_text("Local revised source.\n")
        self.git(self.local, "add", "article.tex")
        self.git(self.local, "commit", "-q", "-m", "Local revision")
        def push() -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", "-C", str(self.local), "push", "origin", "main"],
                                  env=self.env, text=True, capture_output=True)
        blocked = push()
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("Pending Overleaf history", blocked.stderr)
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), initial_remote)
        self.fetch()
        self.git(self.local, "merge", "-q", "--no-ff", "-s", "ours", "--no-edit", "origin/" + self.branch)
        passed = push()
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), self.git(self.local, "rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
