"""Freeze a completed native scene run and sources. Requires normal exit of its exact process."""
import ctypes as c
from ctypes import wintypes as w
import json
import shutil
import subprocess
import sys
from pathlib import Path
import zipfile
from prepare_dc_scene import ROOT, OUT, sha


def main():
    subprocess.run([sys.executable,str(ROOT/'tools/check_dc_scene_runtime.py')],check=True)
    process=json.loads((OUT/'process.json').read_text(encoding='utf-8-sig'))
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE];handle=kernel.OpenProcess(0x1000,False,process['pid'])
    exit_code=None
    if handle:
        try:
            times=[w.FILETIME() for _ in range(4)];kernel.GetProcessTimes.argtypes=[w.HANDLE,*([c.POINTER(w.FILETIME)]*4)]
            if not kernel.GetProcessTimes(handle,*[c.byref(t) for t in times]):raise c.WinError(c.get_last_error())
            created=((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)*100-11644473600000000000
            if abs(created-process['started_at_ns'])>1000000:raise ValueError('reused PID')
            kernel.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)];value=w.DWORD()
            if not kernel.GetExitCodeProcess(handle,c.byref(value)):raise c.WinError(c.get_last_error())
            exit_code=value.value
            if exit_code!=0:raise ValueError('normal game exit required: '+str(exit_code))
        finally:kernel.CloseHandle(handle)
    elif c.get_last_error()!=87:raise ValueError('cannot establish process exit')
    current=json.loads((OUT/'observations/current-run.json').read_text());run=Path(current['directory']);evidence=run/'evidence';evidence.mkdir(exist_ok=False)
    build=json.loads((OUT/'build-report.json').read_text());install=json.loads((OUT/'install.json').read_text())
    for name in ['scene.json','scene.mcdw','source.json','source.mcdw','build-report.json','install.json','process.json','verification.json']:
        shutil.copyfile(OUT/name,evidence/name)
    (evidence/'run.json').write_text(json.dumps(current,indent=2));shutil.copyfile(install['target_jar'],evidence/'own.jar')
    text=(Path(process['profile'])/'logs/latest.log').read_text(encoding='utf-8',errors='replace')
    markers=[line for line in text.splitlines() if 'MCDN' in line]
    if not any('MCDN_PHYSICS_INITIALIZED' in line and build['fixture_sha256'] in line and '/mods/mcdn-native-physics-0.1.0.jar' in line for line in markers):raise ValueError('loaded source/scene marker')
    (evidence/'probe-markers.log').write_text('\n'.join(markers)+'\n',encoding='utf-8')
    with zipfile.ZipFile(evidence/'sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in build['sources']:archive.write(ROOT/name,name.replace('\\','/'))
        frame=json.loads((ROOT/'artifacts/frame-probe/build-report.json').read_text())
        if frame['sha256']!=build['linked_frame_jar_sha256']:raise ValueError('linked frame build drift')
        (evidence/'frame-build-report.json').write_text(json.dumps(frame,indent=2))
        for name,digest in {**frame['sources'],**frame['linked_sources']}.items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError('linked frame source drift')
            if name not in build['sources']:archive.write(ROOT/name,name.replace('\\','/'))
        for name in ['prepare_dc_scene.py','verify_dc_scene.py','check_dc_scene_runtime.py','check_dc_scene_render.py','archive_dc_scene.py','build_physics_probe.py','install_dc_scene.py']:archive.write(ROOT/'tools'/name,'tools/'+name)
    shutil.copyfile(ROOT/'docs/DC_SCENE_SLICE.md',evidence/'slice.md')
    visual=(run/'render-evidence.json').is_file() and json.loads((run/'render-evidence.json').read_text())['visualAcceptance']
    manifest=dict(status='archived-dc-native-motion-pass',nativeExitCode=exit_code,visualAcceptance=visual,files={p.relative_to(run).as_posix():sha(p.read_bytes()) for p in run.rglob('*') if p.is_file()})
    (run/'archive.json').write_text(json.dumps(manifest,indent=2));print('DC_SCENE_NATIVE_ARCHIVED',run)


if __name__=='__main__':main()
