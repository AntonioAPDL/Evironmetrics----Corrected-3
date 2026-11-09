"""Exercise local installation without modifying any live repository or remote."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('install_guard', ROOT / 'scripts/install_overleaf_guard.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GuardInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'scripts').mkdir()
        self.checker = self.repo / 'scripts/check_overleaf_sync.py'
        self.checker.write_text("import sys\nfrom pathlib import Path\nPath('guard-input').write_bytes(sys.stdin.buffer.read())\nsys.exit(0)\n")
        self.old = self.repo / '.githooks'
        self.old.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'config', 'core.hooksPath', '.githooks'], check=True)

    def run_hook(self, installed, updates=b'test update\n'):
        return subprocess.run([str(installed / 'pre-push'), 'origin', 'remote'],
                              input=updates, cwd=self.repo, capture_output=True)

    def test_resists_synced_mode_loss_and_is_idempotent(self):
        prior = self.old / 'pre-push'
        prior.write_text('#!/bin/sh\nexit 0\n')
        prior.chmod(0o755)
        installed = MODULE.install(self.repo)
        self.assertEqual(MODULE.install(self.repo), installed)
        prior.chmod(0o644)
        self.assertEqual(self.run_hook(installed).returncode, 0)
        self.assertEqual((self.repo / 'guard-input').read_bytes(), b'test update\n')
        self.assertTrue(installed.is_relative_to(self.repo / '.git'))

    def test_preserves_prior_hook_rejection_and_stdin(self):
        prior = self.old / 'pre-push'
        prior.write_text('#!/bin/sh\ncat > prior-input\nexit 7\n')
        prior.chmod(0o755)
        installed = MODULE.install(self.repo)
        result = self.run_hook(installed, b'identical updates\n')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual((self.repo / 'prior-input').read_bytes(), b'identical updates\n')
        self.assertEqual((self.repo / 'guard-input').read_bytes(), b'identical updates\n')

    def test_guard_rejection_precedes_prior_hook(self):
        self.checker.write_text('import sys\nsys.exit(9)\n')
        prior = self.old / 'pre-push'
        prior.write_text('#!/bin/sh\ntouch prior-ran\n')
        prior.chmod(0o755)
        installed = MODULE.install(self.repo)
        self.assertEqual(self.run_hook(installed).returncode, 9)
        self.assertFalse((self.repo / 'prior-ran').exists())

    def test_existing_unowned_target_is_preserved(self):
        directory = self.repo / '.git/overleaf-guard-hooks'
        directory.mkdir()
        hook = directory / 'pre-push'
        hook.write_text('An unrelated local hook\n')
        with self.assertRaisesRegex(ValueError, 'unowned'):
            MODULE.install(self.repo)
        self.assertEqual(hook.read_text(), 'An unrelated local hook\n')

    def test_other_hooks_are_preserved_and_table_recovery_is_narrow(self):
        other = self.old / 'post-commit'
        other.write_text('#!/bin/sh\nexit 0\n')
        other.chmod(0o755)
        installed = MODULE.install(self.repo)
        self.assertEqual((installed / 'post-commit').resolve(), other)
        import sys
        spec = importlib.util.spec_from_file_location('merge_overleaf_paths',
            ROOT / 'scripts/merge_overleaf_branch_preserving_generated_assets.py')
        merge = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = merge
        spec.loader.exec_module(merge)
        self.assertTrue(merge.protected_generated('tables/compact_publication/main_aggregate.tex'))
        self.assertTrue(merge.protected_generated('tables/editorial_revision/benchmark_crps_main_table.tex'))
        self.assertFalse(merge.protected_generated('supporting_information.tex'))


if __name__ == '__main__':
    unittest.main()
