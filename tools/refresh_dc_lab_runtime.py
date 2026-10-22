"""Back up and refresh a closed, marked private lab after installed DCCM changes."""
import ctypes as c
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'artifacts/lab'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = LAB / 'dc-launch-spec.json'
    spec = json.loads(path.read_text())
    if Path(spec['cwd']).resolve() != LAB / 'dc-game' or not (LAB / 'dc-game/MCDN_ISOLATED_DC_LAB').is_file():
        raise ValueError('marked private lab required')
    if spec['environment'].get('MCDN_DC_LIVE_COLOR_MANIFEST'):
        raise ValueError('disarm session before runtime refresh')
    k = c.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.restype = c.c_void_p
    k.GetExitCodeProcess.argtypes = [c.c_void_p, c.POINTER(c.c_ulong)]
    k.CloseHandle.argtypes = [c.c_void_p]
    handle = k.OpenProcess(0x1000, False, json.loads((LAB / 'dc-process.json').read_text())['pid'])
    if handle:
        try:
            code = c.c_ulong()
            if not k.GetExitCodeProcess(handle, c.byref(code)) or code.value == 259:
                raise ValueError('prior lab must have exited')
        finally:
            k.CloseHandle(handle)
    changes = {}
    for name, digest in spec['private_game_files'].items():
        if sha(LAB / name) != digest:
            raise ValueError('private lab drift: ' + name)
    for name in ['GameProxy.dll', 'GameProxy.dll.cache', 'hlboot.dat', 'hlboot.dat.cache']:
        changes[LAB / 'dc-cache' / name] = ROOT.parent / 'cache' / name
    loader = 'dc-plugins/ModCore.ModLoader.Default/ModCore.ModLoader.Default.dll'
    changes[LAB / loader] = ROOT.parent / 'plugins/ModCore.ModLoader.Default/ModCore.ModLoader.Default.dll'
    runtime_proxy = sha(ROOT.parent / 'cache/GameProxy.dll')
    for build_path in [LAB / 'dc-build-report.json', ROOT / 'artifacts/dc-render-api/build-report.json']:
        build = json.loads(build_path.read_text())
        if build['runtime_gameproxy_sha256'] != runtime_proxy:
            raise ValueError('rebuild against current GameProxy first')
        for name, digest in build['packages'].items():
            source = ROOT / name
            if sha(source) != digest:
                raise ValueError('new package drift')
            changes[LAB / 'dc-mods' / source.parent.name / source.name] = source
    backup = ROOT / 'artifacts/backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-dc-runtime-refresh')
    backup.mkdir(parents=True)
    old_files = [path, *changes, *(LAB / 'dc-game/save').rglob('*')]
    with zipfile.ZipFile(backup / 'lab-before.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for old in old_files:
            if old.is_file():
                archive.write(old, old.relative_to(LAB))
    # The host rewrites this diagnostic after a launch; it is not a runtime dependency.
    pins = {str(p.relative_to(ROOT.parent)): sha(p) for p in (ROOT.parent / 'core/host').glob('*') if p.is_file() and p.name != 'last_error.txt'}
    for target, source in changes.items():
        if not target.resolve().is_relative_to(LAB.resolve()):
            raise ValueError('target escaped private lab')
        shutil.copyfile(source, target)
        name = str(target.relative_to(LAB))
        spec['private_game_files'][name] = sha(target)
        if name in spec['package_files']:
            spec['package_files'][name] = sha(target)
    spec['shell_sha256'] = sha(Path(spec['args'][0]))
    spec['runtime_host_files'] = pins
    spec['runtime_refresh_backup'] = str(backup)
    path.write_text(json.dumps(spec, indent=2))
    print('DC_LAB_RUNTIME_REFRESHED; native positive/negative preflight REQUIRED', backup)


if __name__ == '__main__':
    main()
