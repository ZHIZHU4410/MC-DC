"""Arm only the native pause prerequisite in the isolated DC launch spec."""
import argparse
import ctypes as c
from ctypes import wintypes as w
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from prepare_dc_scene import ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--arm',action='store_true');parser.add_argument('--hero',action='store_true');args=parser.parse_args()
    lab=ROOT/'artifacts/lab';path=lab/'dc-launch-spec.json';spec=json.loads(path.read_text())
    if Path(spec['cwd']).resolve()!=lab/'dc-game' or spec['environment'].get('MCDN_DC_ISOLATED_LAB')!='1':raise ValueError('guarded DC lab required')
    record=json.loads((lab/'dc-process.json').read_text());kernel=c.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE;kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,record['pid'])
    if handle:
        try:
            code=w.DWORD();kernel.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)]
            if not kernel.GetExitCodeProcess(handle,c.byref(code)) or code.value==259:raise ValueError('normally close prior DC lab first')
        finally:kernel.CloseHandle(handle)
    backup=ROOT/'artifacts/backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-pause-lab-config');backup.mkdir(parents=True);shutil.copyfile(path,backup/path.name)
    if args.arm:
        if 'MCDN_DC_LIVE_COLOR_MANIFEST' in spec['environment']:raise ValueError('standalone pause prerequisite only')
        spec['environment']['MCDN_DC_PAUSE_LAB']='hero' if args.hero else '1'
    else:spec['environment'].pop('MCDN_DC_PAUSE_LAB',None)
    path.write_text(json.dumps(spec,indent=2));print('PAUSE_LAB_CONFIGURED',args.arm,'BACKUP',backup)

if __name__=='__main__':main()
