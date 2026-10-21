"""Freeze the passed native fixture run, owned code and filtered loader evidence after normal exit."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import zipfile
import re
from urllib.parse import urlsplit,unquote

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/physics'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--post-restoration',type=Path,required=True);args=parser.parse_args()
    current=json.loads((OUT/'observations/current-run.json').read_text());run=Path(current['directory']).resolve()
    if run.parent!=(OUT/'observations').resolve():raise ValueError('owned run required')
    report=json.loads((run/'runtime-report.json').read_text());build=json.loads((OUT/'build-report.json').read_text());install=json.loads((OUT/'install.json').read_text())
    if report['status']!='native-player-physics-fixture-pass' or report['events_sha256']!=sha(run/'events.jsonl') or report['completion_sha256']!=sha(run/'complete.json'):raise ValueError('passed immutable observations required')
    process=json.loads((OUT/'process.json').read_text(encoding='utf-8-sig'));profile=Path(process['profile'])
    if profile!=Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3') or not (profile/'MCDN_PHYSICS_LAB').is_file():raise ValueError('marked physics profile required')
    # Read-only PID existence check, no process command lines or account information.
    import ctypes as c
    from ctypes import wintypes as w
    kernel=c.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE;kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,process['pid']);exit_code=None
    if handle:
        kernel.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)];value=w.DWORD()
        try:
            if not kernel.GetExitCodeProcess(handle,c.byref(value)):raise c.WinError(c.get_last_error())
            exit_code=value.value
            if exit_code!=0:raise ValueError('recorded game must normally exit before archive: '+str(exit_code))
        finally:kernel.CloseHandle(handle)
    elif c.get_last_error()!=87:raise ValueError('could not prove recorded game exited')
    if sha(Path(install['target_jar']))!=build['sha256'] or sha(Path(build['jar']))!=build['sha256'] or report['installed_sha256']!=build['sha256']:raise ValueError('owned tested JAR')
    text=(profile/'logs/latest.log').read_text(encoding='utf-8',errors='replace')
    markers=[line for line in text.splitlines() if 'MCDN_PHYSICS_' in line or 'MCDN physics' in line]
    initialized=[re.search(r'MCDN_PHYSICS_INITIALIZED source=(.*?) fixture=([0-9a-f]{64});',line) for line in markers];initialized=[m for m in initialized if m]
    if len(initialized)!=1:raise ValueError('unique native initialization source required')
    source=urlsplit(initialized[0][1])
    if source.scheme!='file' or source.netloc or Path(unquote(source.path).lstrip('/')).resolve()!=Path(install['target_jar']).resolve() or initialized[0][2]!=build['fixture_sha256']:raise ValueError('actual loaded native package/fixture')
    for marker in ['MCDN_PHYSICS_WORLD_PREPARED peaceful','MCDN_PHYSICS_SCRIPT_STARTED','MCDN_PHYSICS_SERVER_RESTORED']:
        if not any(marker in line for line in markers):raise ValueError('native loader/runtime marker '+marker)
    if any('/ERROR]' in line for line in markers):raise ValueError('native fixture errors')
    evidence=run/'evidence';evidence.mkdir(exist_ok=False)
    for name in ['build-report.json','install.json','process.json']:shutil.copyfile(OUT/name,evidence/name)
    (evidence/'run.json').write_text(json.dumps(current,indent=2),encoding='utf-8')
    shutil.copyfile(Path(install['target_jar']),evidence/'own.jar');shutil.copyfile(OUT/'fixture-world.mcdw',evidence/'fixture-world.mcdw')
    (evidence/'probe-markers.log').write_text('\n'.join(markers)+'\n',encoding='utf-8')
    with zipfile.ZipFile(evidence/'sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name,digest in build['sources'].items():
            path=ROOT/name
            if sha(path)!=digest:raise ValueError('transformed source drift')
            archive.write(path,name.replace('\\','/'))
        for name in ['build_physics_probe.py','check_native_physics.py','archive_native_physics.py','prepare_physics_profile.py','replace_physics_probe.py','dc_lab_window.py']:
            archive.write(ROOT/'tools'/name,'tools/'+name)
    photograph=args.post_restoration.resolve()
    if not photograph.is_relative_to(ROOT/'artifacts/lab/dc-frame') or photograph.stat().st_mtime_ns<process['started_at_ns']:raise ValueError('current recorded window capture required')
    shutil.copyfile(photograph,evidence/'post-restoration.png')
    summary={'status':'archived-native-physics-fixture-pass','runtime_pass':True,'run':str(run),'game_exited':True,'native_exit_code':exit_code,'scope':report['scope'],'visual':'post-restoration window; auxiliary GPU timing requires separate validation and is not the motion acceptance oracle','files':{p.relative_to(run).as_posix():sha(p) for p in sorted(run.rglob('*')) if p.is_file()}}
    (run/'archive.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');(OUT/'progress.json').write_text(json.dumps({k:v for k,v in summary.items() if k!='files'},indent=2),encoding='utf-8');print('PHYSICS_NATIVE_ARCHIVED',run)


if __name__=='__main__':main()
