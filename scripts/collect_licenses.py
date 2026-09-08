"""Copy installed dependency notices into the Windows distribution."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
import sys


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    for distribution in distributions():
        name = distribution.metadata['Name']
        if name.startswith('chess-vision-assistant'):
            continue
        for relative in distribution.files or ():
            path = Path(str(relative))
            if not any('license' in part.lower() or 'copying' in part.lower()
                       or part.lower().startswith('notice') for part in path.parts):
                continue
            source = Path(distribution.locate_file(relative))
            if not source.is_file() or source.suffix.lower() in ('.py', '.pyc', '.dll', '.pyd'):
                continue
            # Flatten only safe relative components, preserving nested notices.
            target = destination / name / Path(*[p for p in path.parts if p not in ('..', '.')])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


if __name__ == '__main__':
    main()
