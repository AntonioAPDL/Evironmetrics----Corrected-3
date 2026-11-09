#!/usr/bin/env python3
"""Install the existing ancestry guard outside the Overleaf-synchronized tree.

Preserve existing hooks and forward identical pre-push input to the prior hook.
The installation is local Git configuration; it changes no branch or remote.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def install(repo: Path) -> Path:
    repo = Path(git(repo, 'rev-parse', '--show-toplevel')).resolve()
    common = Path(git(repo, 'rev-parse', '--git-common-dir'))
    if not common.is_absolute():
        common = (repo / common).resolve()
    target = common / 'overleaf-guard-hooks'
    record = target / 'installation.json'
    if target.exists() and not record.is_file() and any(target.iterdir()):
        raise ValueError('Refusing to overwrite an unowned nonempty hooks directory')
    configured = subprocess.run(['git', '-C', str(repo), 'config', '--get', 'core.hooksPath'],
                                text=True, capture_output=True)
    if configured.returncode not in (0, 1):
        raise RuntimeError('Cannot inspect existing Git hooks configuration')
    previous = Path(configured.stdout.strip()) if configured.stdout.strip() else common / 'hooks'
    if not previous.is_absolute():
        previous = (repo / previous).resolve()
    if previous == target:
        if not record.is_file():
            raise ValueError('Existing guard installation lacks its original-hook record')
        previous = Path(json.loads(record.read_text())['previous_hooks'])
    if not (repo / 'scripts/check_overleaf_sync.py').is_file():
        raise ValueError('Missing article ancestry checker')
    target.mkdir(exist_ok=True)
    # Keep other configured hooks effective; never overwrite unrelated local files.
    if previous.is_dir():
        for original in previous.iterdir():
            if original.name in {'pre-push', 'installation.json'} or original.name.endswith('.sample'):
                continue
            destination = target / original.name
            if not destination.exists() and not destination.is_symlink():
                destination.symlink_to(original)
    prior = previous / 'pre-push'
    dispatcher = '''#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys
repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
updates = sys.stdin.buffer.read()
guard = subprocess.run([sys.executable, str(repo / 'scripts/check_overleaf_sync.py'),
                        '--repo', str(repo), '--pre-push', *sys.argv[1:]], input=updates)
if guard.returncode:
    sys.exit(guard.returncode)
prior = Path(PRIOR_HOOK)
if prior.is_file() and os.access(prior, os.X_OK):
    sys.exit(subprocess.run([str(prior), *sys.argv[1:]], input=updates).returncode)
'''.replace('PRIOR_HOOK', repr(str(prior)))
    hook = target / 'pre-push'
    hook.write_text(dispatcher)
    hook.chmod(0o755)
    record.write_text(json.dumps({'previous_hooks': str(previous),
                                 'guard_script': 'scripts/check_overleaf_sync.py'}, indent=2) + '\n')
    git(repo, 'config', 'core.hooksPath', str(target))
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print('Overleaf guard installed: ' + str(install(args.repo)))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
