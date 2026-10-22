"""Preserve a failed dedicated lab save, then restore its complete pre-run snapshot."""
import argparse
import ctypes as c
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3')


def main():
    p=argparse.ArgumentParser();p.add_argument('backup',type=Path);a=p.parse_args()
    archive=a.backup.resolve();world=GAME/'saves/MCDN-Physics'
    if not archive.is_relative_to((ROOT/'artifacts/backups').resolve()) or world.resolve()!=world or not (GAME/'MCDN_PHYSICS_LAB').is_file():raise ValueError('dedicated canonical lab and own backup required')
    k=c.WinDLL('kernel32');k.OpenProcess.restype=c.c_void_p;k.GetExitCodeProcess.argtypes=[c.c_void_p,c.POINTER(c.c_ulong)];k.CloseHandle.argtypes=[c.c_void_p]
    record=json.loads((ROOT/'artifacts/physics/process.json').read_text(encoding='utf-8-sig'));handle=k.OpenProcess(0x1000,False,record['pid'])
    if handle:
        try:
            code=c.c_ulong()
            if not k.GetExitCodeProcess(handle,c.byref(code)) or code.value==259:raise ValueError('close recorded MC normally before restoring')
        finally:k.CloseHandle(handle)
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('backup CRC')
        entries={n[len('saves/MCDN-Physics/'):]:z.read(n) for n in z.namelist() if n.startswith('saves/MCDN-Physics/') and not n.endswith('/')}
    if not entries or len(entries)>4096 or sum(map(len,entries.values()))>512*1024*1024:raise ValueError('backup world bounds')
    for name in entries:
        target=(world/name).resolve()
        if not target.is_relative_to(world) or target==world:raise ValueError('backup path escape')
    destination=ROOT/'artifacts/backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-failed-physics-save')
    destination.mkdir(parents=True)
    moved=destination/'world-after-failure'
    if not moved.resolve().is_relative_to((ROOT/'artifacts/backups').resolve()) or world.resolve()!=GAME/'saves/MCDN-Physics':raise ValueError('move bounds')
    shutil.move(str(world),str(moved)) # Preserve every failed-save file; never delete it.
    world.mkdir()
    for name,data in entries.items():
        target=world/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    expected={n:hashlib.sha256(data).hexdigest() for n,data in entries.items()}
    actual={p.relative_to(world).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in world.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('restored complete file tree differs')
    (destination/'restore.json').write_text(json.dumps(dict(source=str(archive),sourceSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),preservedFailedSave=str(moved),restoredSave=str(world),files=expected),indent=2))
    print('DEDICATED_PHYSICS_WORLD_RESTORED',len(actual),'files; failed world preserved at',moved)


if __name__=='__main__':main()
