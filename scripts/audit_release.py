"""Read-only credential scan. Reports paths/object IDs, never matching values."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    rb'(?:sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}'
    rb'|gh[pousr]_[A-Za-z0-9]{30,})'
)


def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args], cwd=ROOT)


def main():
    failures = []
    paths = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')
    for name in filter(None, paths):
        path = ROOT / name
        if path.is_file() and PATTERN.search(path.read_bytes()):
            failures.append('worktree: ' + name)
        if path.name.startswith('.env') and path.name != '.env.example':
            failures.append('included environment file: ' + name)
    objects = git('rev-list', '--objects', 'HEAD').decode().splitlines()
    count = 0
    for item in objects:
        sha, _, name = item.partition(' ')
        if git('cat-file', '-t', sha).strip() != b'blob':
            continue
        count += 1
        if PATTERN.search(git('cat-file', 'blob', sha)):
            failures.append(f'history: {sha} {name}')
    if '--dist' in sys.argv:
        for path in (ROOT / 'dist' / 'ChessVision').rglob('*'):
            if path.is_file() and PATTERN.search(path.read_bytes()):
                failures.append('distribution: ' + str(path.relative_to(ROOT)))
    print(f'Scanned {len(paths)-1} release files and {count} historical blobs.')
    print('\n'.join(failures) if failures else 'No credential patterns found.')
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
