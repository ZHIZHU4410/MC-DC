"""Short, foreground-checked native keyboard challenge during the opt-in pause prerequisite."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import time
from prepare_dc_scene import ROOT

def main():
    lab=ROOT/'artifacts/lab';current=json.loads((lab/'dc-frame/pause-lab/current.json').read_text());run=Path(current['directory']);process=json.loads((lab/'dc-process.json').read_text())
    if current['pid']!=process['pid'] or current['productionModeGranted']:raise ValueError('current standalone prerequisite identity')
    u=c.WinDLL('user32',use_last_error=True);u.GetForegroundWindow.restype=w.HWND;u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
    def own():
        pid=w.DWORD();u.GetWindowThreadProcessId(u.GetForegroundWindow(),c.byref(pid))
        if pid.value!=process['pid']:raise ValueError('only foreground DC input allowed')
    class Keyboard(c.Structure):_fields_=[('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',c.c_size_t)]
    class Mouse(c.Structure):_fields_=[('x',w.LONG),('y',w.LONG),('data',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',c.c_size_t)]
    class Union(c.Union):_fields_=[('keyboard',Keyboard),('mouse',Mouse)]
    class Input(c.Structure):_fields_=[('type',w.DWORD),('value',Union)]
    u.SendInput.argtypes=[w.UINT,c.POINTER(Input),c.c_int]
    def key(scan,up=False):
        value=Input(type=1,value=Union(keyboard=Keyboard(vk=0,scan=scan,flags=8|(2 if up else 0))))
        if u.SendInput(1,c.byref(value),c.sizeof(value))!=1:raise c.WinError(c.get_last_error())
    own();(run/'begin').touch(exist_ok=False);deadline=time.monotonic()+5
    installed=False
    while time.monotonic()<deadline:
        own()
        if (run/'events.jsonl').exists() and any(json.loads(row)['kind']=='installed' for row in (run/'events.jsonl').read_text().splitlines()):installed=True;break
        time.sleep(.01)
    if not installed:raise ValueError('native pause installation missing')
    started=time.time_ns()
    try:
        own();key(0x11);key(0x39);time.sleep(.15)
    finally:key(0x11,True);key(0x39,True)
    (run/'keyboard-challenge.json').write_text(json.dumps(dict(pid=process['pid'],startedUnixNs=started,endedUnixNs=time.time_ns(),keys=['W','Space'],source='foreground-checked Win32 SendInput scan codes',allReleased=True)))
    print('PAUSE_LAB_KEYBOARD_CHALLENGE_SENT',run)

if __name__=='__main__':main()
