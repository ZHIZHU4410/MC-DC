"""Freeze the combined native-motion/live-display run after both games have exited normally."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from prepare_dc_scene import ROOT, OUT

LAB=ROOT/'artifacts/lab'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def exited(record):
    kernel=c.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE;kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,record['pid'])
    if not handle:
        if c.get_last_error()==87:return None
        raise c.WinError(c.get_last_error())
    try:
        kernel.GetProcessTimes.argtypes=[w.HANDLE,*([c.POINTER(w.FILETIME)]*4)];times=[w.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle,*[c.byref(t) for t in times]):raise c.WinError(c.get_last_error())
        created=((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)*100-11644473600000000000
        if abs(created-record['started_at_ns'])>5000000000:raise ValueError('process creation identity differs')
        code=w.DWORD();kernel.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)]
        if not kernel.GetExitCodeProcess(handle,c.byref(code)) or code.value!=0:raise ValueError('normal recorded game exit required')
        return code.value
    finally:kernel.CloseHandle(handle)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--restored',type=Path,required=True);parser.add_argument('--observed',required=True);args=parser.parse_args()
    pointer=json.loads((LAB/'live-color/current-session.json').read_text());directory=Path(pointer['manifest']).parent
    report=json.loads((directory/'runtime-report.json').read_text());combined=json.loads((directory/'combined-scene.json').read_text())
    if report['session']!=directory.name or report['presentation']!='full-scene-diagnostic' or not report['producer_stopped_preview_cleared_markers']:raise ValueError('completed live display required')
    codes={role:exited(report[role+'_process']) for role in ['mc','dc']}
    native=Path(combined['nativeRun'])
    if not native.resolve().is_relative_to(OUT/'observations') or not (native/'archive.json').is_file():raise ValueError('archived native trajectory required')
    shutil.copytree(native,directory/'native-run')
    for source,name in [(LAB/'dc-launch-spec.json','dc-launch-spec.json'),(LAB/'dc-logs/log_latest.log','dc-runtime.log'),(Path(json.loads((directory/'session.json').read_text())['gameDir'])/'logs/latest.log','mc-runtime.log'),(OUT/'build-report.json','mc-build-report.json'),(ROOT/'artifacts/dc-render-api/build-report.json','dc-build-report.json'),(LAB/'dc-mods/McdnDcFrameProbe/Mcdn.DcFrameProbe.dll','Mcdn.DcFrameProbe.dll'),(args.restored,'dc-restored.png')]:shutil.copyfile(source,directory/name)
    build=json.loads((OUT/'build-report.json').read_text());shutil.copyfile(build['jar'],directory/'mc-native-scene.jar')
    display=json.loads((ROOT/'artifacts/dc-render-api/build-report.json').read_text())
    with zipfile.ZipFile(directory/'display-sources.zip','x',zipfile.ZIP_DEFLATED) as source:
        for name,digest in {**display['sources'],**display['linked_sources']}.items():
            path=ROOT/name
            if sha(path)!=digest:raise ValueError('display source drift')
            source.write(path,name.replace('\\','/'))
        for name in ['observe_combined_scene.py','check_live_color.py','archive_combined_scene.py']:source.write(ROOT/'tools'/name,'tools/'+name)
    visible=dict(status='combined-native-scene-in-dc-visible-pass',session=directory.name,observation=args.observed,nativeExitCodes=codes,
                 runtimeReportSha256=sha(directory/'runtime-report.json'),nativeMotionReportSha256=sha(native/'runtime-report.json'),
                 captures={Path(p).name:sha(Path(p)) for p in combined['captures']},restoredImageSha256=sha(directory/'dc-restored.png'),
                 limitation='Archived DC solid subset and local scripted MC input. No live DC controls, Hero bypass, production MODE, combat or world editing.')
    (directory/'visible-report.json').write_text(json.dumps(visible,indent=2))
    excluded={'color.map','archive-combined.json','producer-latest.json.tmp','consumer-latest.json.tmp'}
    manifest=dict(status='combined-scene-archived',session=directory.name,files={p.relative_to(directory).as_posix():sha(p) for p in directory.rglob('*') if p.is_file() and p.name not in excluded})
    (directory/'archive-combined.json').write_text(json.dumps(manifest,indent=2));print('COMBINED_SCENE_ARCHIVED',directory)


if __name__=='__main__':main()
