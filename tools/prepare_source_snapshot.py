"""Export only authored source into an existing clean staging clone; never push."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'artifacts/publish/repository'
SKIP = {'bin', 'obj', 'build', '.gradle', '__pycache__'}


def main():
    if not (TARGET / '.git').is_dir():
        raise ValueError('existing staging clone required')
    candidates = [ROOT / name for name in
                  ['.gitignore', 'README.md', 'MODLOG.md', 'NuGet.Config',
                   'REFERENCE_STUDY.md', 'Start-DC-Lab.cmd',
                   'research/GITHUB_RESEARCH.md', 'research/sources.json']]
    for name in ['src', 'tests', 'tools', 'docs']:
        candidates.extend(p for p in (ROOT / name).rglob('*') if p.is_file()
                          and not SKIP.intersection(p.relative_to(ROOT).parts))
    allowed = {'.md', '.json', '.cs', '.csproj', '.java', '.cpp', '.py', '.cmd', '.config'}
    secrets = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{40,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    manifest = {}
    for source in candidates:
        if source.name != '.gitignore' and source.suffix.lower() not in allowed:
            raise ValueError('unreviewed extension: ' + str(source))
        data = source.read_bytes()
        if len(data) > 2_000_000 or secrets.search(data):
            raise ValueError('size/credential audit failed: ' + str(source))
        manifest[source.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
    # All removal targets are direct children of the fixed, checked staging clone.
    if TARGET.resolve() != ROOT.resolve() / 'artifacts/publish/repository':
        raise ValueError('staging path changed')
    for child in TARGET.iterdir():
        if child.name == '.git':
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    for name in manifest:
        destination = TARGET / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (ROOT / 'artifacts/publish/source-manifest.json').write_text(
        json.dumps(manifest, indent=2), encoding='utf-8')
    print('SOURCE_SNAPSHOT_AUDITED', len(manifest), 'files')


if __name__ == '__main__':
    main()
