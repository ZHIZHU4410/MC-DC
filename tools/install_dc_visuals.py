"""Arm/remove the owned DC source-material pack in the existing marked physics lab, with backup."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'artifacts/dc-visuals'
GAME = Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_pack(options, name, selected):
    rows = options.splitlines()
    values = [row for row in rows if row.startswith('resourcePacks:')]
    if len(values) != 1:
        raise ValueError('one native resource pack option required')
    packs = json.loads(values[0].split(':', 1)[1])
    packs = [pack for pack in packs if pack != name]
    if selected:
        packs.append(name)
    return '\n'.join('resourcePacks:'+json.dumps(packs, separators=(',', ':')) if row.startswith('resourcePacks:') else row for row in rows)+'\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--install', action='store_true')
    p.add_argument('--restore', action='store_true')
    a = p.parse_args()
    if a.install and a.restore:
        p.error('choose install or restore')
    config = OUT/'conversion-report.json'
    visual = json.loads(config.read_text(encoding='utf-8'))
    if not (GAME/'MCDN_PHYSICS_LAB').is_file() or not (GAME/'MCDN_ISOLATED_LAB').is_file():
        raise ValueError('marked private native player lab required')
    options, physics = GAME/'options.txt', GAME/'mcdn-physics.json'
    native = json.loads(physics.read_text())
    if native['fixtureSha256'] != visual['sceneDigest']:
        raise ValueError('native and visual geometry disagree')
    target = GAME/'resourcepacks'/visual['packFile']
    if target.name != 'mcdn-dc-prison.zip' or target.parent != GAME/'resourcepacks':
        raise ValueError('only the named private generated pack is allowed')
    if not a.install and not a.restore:
        print('DC_VISUAL_INSTALL_READY', target)
        return
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
                             '@(Get-Process java,javaw -ErrorAction SilentlyContinue).Count'],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != '0':
        raise ValueError('close Java games normally before changing the laboratory')
    for lock in (GAME/'saves').rglob('session.lock'):
        lock.read_bytes()
    record_path = OUT/'install.json'
    record = json.loads(record_path.read_text()) if record_path.exists() else None
    if target.exists() and (not record or sha(target) != record['packSha256']):
        raise ValueError('existing pack is not the recorded owned artifact')
    backup = ROOT/'artifacts/backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-dc-visuals')
    backup.mkdir(parents=True)
    with ZipFile(backup/'config-before.zip', 'x', ZIP_DEFLATED) as archive:
        for path in [options, physics]:
            archive.write(path, path.name)
    before = options.read_text(encoding='utf-8')
    if a.restore:
        if not record or record['status'] != 'installed' or not target.exists() or native.get('dcVisualsSha256') != record['visualConfigSha256']:
            raise ValueError('matching owned visual installation required')
        options.write_text(set_pack(before, visual['packId'], False), encoding='utf-8')
        native.pop('dcVisuals', None)
        native.pop('dcVisualsSha256', None)
        physics.write_text(json.dumps(native, indent=2), encoding='utf-8')
        # Retain the exact generated private asset outside the source project; no asset in backups.
        saved = Path(visual['packPath']).parent/('restored-'+sha(target)+'.zip')
        if saved.exists() and sha(saved) != sha(target):
            raise ValueError('private restore destination differs')
        if not saved.exists():
            shutil.copyfile(target, saved)
        target.unlink()
        record.update(status='restored', restoreBackup=str(backup), retainedPrivatePack=str(saved))
    else:
        source = Path(visual['packPath']).resolve()
        if ROOT in source.parents or sha(source) != visual['packSha256'] or target.exists():
            raise ValueError('fresh private source pack required')
        if native.get('inputManifest') or native.get('dcVisuals'):
            raise ValueError('disarm the previous run before installing visuals')
        updated = set_pack(before, visual['packId'], True)
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        native.update(dcVisuals=str(config), dcVisualsSha256=sha(config))
        options.write_text(updated, encoding='utf-8')
        physics.write_text(json.dumps(native, indent=2), encoding='utf-8')
        record = dict(status='installed', target=str(target), packSha256=sha(target),
                      visualConfigSha256=sha(config), backup=str(backup))
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print('DC_VISUAL_'+record['status'].upper(), 'BACKUP', backup)


if __name__ == '__main__':
    main()
