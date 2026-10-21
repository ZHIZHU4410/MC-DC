"""Begin the ready native script only with DC foreground, and collect bounded display evidence."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import time
from PIL import ImageGrab
from prepare_dc_scene import ROOT, OUT


def main():
    lab=ROOT/'artifacts/lab';pointer=json.loads((lab/'live-color/current-session.json').read_text());directory=Path(pointer['manifest']).parent
    current=json.loads((OUT/'observations/current-run.json').read_text());run=Path(current['directory'])
    ready=json.loads((run/'ready.json').read_text());process=json.loads((lab/'dc-process.json').read_text())
    if ready['fixtureSha256']!=current['fixtureSha256'] or not ready['grounded'] or ready['geometrySource']!='archived-dc-solid-subset':raise ValueError('ready actual DC scene required')
    u=c.WinDLL('user32');u.GetForegroundWindow.restype=w.HWND;u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)];u.GetWindowRect.argtypes=[w.HWND,c.POINTER(w.RECT)]
    u.SetThreadDpiAwarenessContext.argtypes=[c.c_void_p];u.SetThreadDpiAwarenessContext.restype=c.c_void_p
    if not u.SetThreadDpiAwarenessContext(c.c_void_p(-4)):raise c.WinError()
    def foreground():
        hwnd=u.GetForegroundWindow();pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid))
        if pid.value!=process['pid']:raise ValueError('DC must remain foreground: '+str(pid.value))
        return hwnd,pid.value
    foreground();(run/'begin').touch(exist_ok=False)
    samples=[];captures=[];start=time.monotonic();last=0
    while time.monotonic()-start<13:
        hwnd,pid=foreground()
        if (directory/'producer-latest.json').exists() and (directory/'consumer-latest.json').exists():
            producer=json.loads((directory/'producer-latest.json').read_text());consumer=json.loads((directory/'consumer-latest.json').read_text())
            if int(consumer['frameId'])>last:
                last=int(consumer['frameId']);samples.append(dict(foreground_pid=pid,observedUnixNs=time.time_ns(),producer=producer,consumer=consumer))
                if len(captures)<3 and len(samples) in [2,5,8]:
                    rect=w.RECT()
                    if not u.GetWindowRect(hwnd,c.byref(rect)):raise c.WinError()
                    path=directory/('dc-full-view-'+str(len(captures)+1)+'.png');ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom)).save(path);captures.append(str(path))
        time.sleep(.35)
    (directory/'foreground-samples.json').write_text(json.dumps(samples,indent=2))
    (directory/'combined-scene.json').write_text(json.dumps(dict(scope='archived DC solids/native scripted MC player/GPU/DC internal full view; Hero input takeover disabled',nativeRun=str(run),captures=captures,samples=len(samples)),indent=2))
    print('COMBINED_SCENE_OBSERVED',len(samples),'foreground samples',len(captures),'DC window captures')


if __name__=='__main__':main()
