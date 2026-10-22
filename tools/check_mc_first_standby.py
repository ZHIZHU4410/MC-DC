"""Check the real MC guest socket handshake after DC starts beyond the old 30s deadline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/dc-scene/warm-start'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--mc-version-dir', type=Path, required=True)
    args = parser.parse_args()
    version = args.mc_version_dir.resolve()
    metadata = json.loads((version / (version.name + '.json')).read_text(encoding='utf-8-sig'))
    report = json.loads((ROOT / 'artifacts/dc-scene/build-report.json').read_text())
    jar = Path(report['jar'])
    if sha(jar) != report['sha256'] or sha(ROOT / 'artifacts/dc-scene/scene.mcdw') != report['fixture_sha256']:
        raise ValueError('verified native build and scene required')
    libs = version.parent.parent / 'libraries'
    cp = [jar]
    for lib in metadata['libraries']:
        group, artifact, release, *classifier = lib['name'].split(':')
        path = libs / group.replace('.', '/') / artifact / release / (artifact + '-' + release + ('-' + classifier[0] if classifier else '') + '.jar')
        if path.exists():
            cp.append(path)
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'tests/physics/dev/mcdn/physics/WarmStartBench.java'
    classpath = ';'.join(map(str, cp))
    compile_result = subprocess.run([str(args.java_home / 'bin/javac.exe'), '-encoding', 'UTF-8', '-proc:none', '-cp', classpath, '-d', str(OUT), str(source)], capture_output=True, text=True, timeout=60)
    if compile_result.returncode:
        raise RuntimeError(compile_result.stdout + compile_result.stderr)
    run = subprocess.run([str(args.java_home / 'bin/java.exe'), '-cp', str(OUT) + ';' + classpath,
                          'dev.mcdn.physics.WarmStartBench', str(jar), str(ROOT / 'artifacts/dc-scene/scene.mcdw'), str(OUT)],
                         capture_output=True, text=True, timeout=50)
    if run.returncode or 'MC_FIRST_STANDBY_PASS' not in run.stdout:
        raise RuntimeError(run.stdout + run.stderr)
    result = {'status': 'pass', 'scope': 'real delayed local socket/HELLO after 32 seconds; no game window',
              'buildSha256': report['sha256'], 'sceneSha256': report['fixture_sha256'],
              'testSha256': sha(source), 'output': run.stdout.strip()}
    (OUT / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(run.stdout.strip())


if __name__ == '__main__':
    main()
