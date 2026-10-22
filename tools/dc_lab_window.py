"""Inspect/focus/close only the recorded, creation-time-verified private DC window."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=["inspect","focus","close","capture","escape","enter","space","f3","f5","f7","minimize","show-inactive"]);p.add_argument("--hold-ms",type=int,default=50);group=p.add_mutually_exclusive_group();group.add_argument("--mc",action="store_true");group.add_argument("--physics",action="store_true");a=p.parse_args()
    if not 50<=a.hold_ms<=500:raise ValueError("hold must be between 50 and 500 ms")
    lab=ROOT/"artifacts/lab";record_path=ROOT/"artifacts/physics/process.json" if a.physics else lab/("mc-live-process.json" if a.mc else "dc-process.json")
    record=json.loads(record_path.read_text(encoding="utf-8-sig"));a.mc=a.mc or a.physics
    if a.mc:
        game=Path(r"D:\MC\.minecraft\versions")/("MC-DC-Physics-26.3" if a.physics else "MC-DC-Lab-26.3")
        if not (game/"MCDN_ISOLATED_LAB").is_file():raise ValueError("marked MC lab required")
        if a.physics and (Path(record["profile"])!=game or not (game/"MCDN_PHYSICS_LAB").is_file()):raise ValueError("recorded dedicated physics lab required")
        spec={"executable":record["executable"]}
    else:
        spec=json.loads((lab/"dc-launch-spec.json").read_text())
        if Path(spec["cwd"]).resolve()!=lab/"dc-game" or not (lab/"dc-game/MCDN_ISOLATED_DC_LAB").is_file():raise ValueError("marked lab required")
    k=c.WinDLL("kernel32",use_last_error=True);u=c.WinDLL("user32",use_last_error=True)
    u.SetThreadDpiAwarenessContext.argtypes=[c.c_void_p];u.SetThreadDpiAwarenessContext.restype=c.c_void_p
    if not u.SetThreadDpiAwarenessContext(c.c_void_p(-4)):raise c.WinError(c.get_last_error())
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE]
    k.GetProcessTimes.argtypes=[w.HANDLE,*([c.POINTER(w.FILETIME)]*4)]
    k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)]
    handle=k.OpenProcess(0x1000,False,record["pid"])
    if not handle:raise ValueError("recorded process is absent/inaccessible")
    try:
        times=[w.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle,*[c.byref(t) for t in times]):raise c.WinError(c.get_last_error())
        created=((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)*100-11644473600000000000
        if abs(created-record["started_at_ns"])>5_000_000_000:raise ValueError("PID creation time differs; refusing reused PID")
        name=c.create_unicode_buffer(32768);size=w.DWORD(len(name))
        if not k.QueryFullProcessImageNameW(handle,0,name,c.byref(size)):raise c.WinError(c.get_last_error())
        if Path(name.value).resolve()!=Path(spec["executable"]).resolve():raise ValueError("recorded executable differs")
        rows=[]
        u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
        u.IsWindowVisible.argtypes=[w.HWND];u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
        @c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
        def visit(hwnd,_):
            pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid))
            if pid.value==record["pid"] and u.IsWindowVisible(hwnd):
                title=c.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,len(title))
                rows.append({"hwnd":int(hwnd),"title":title.value,"pid":pid.value,"created_at_ns":created})
            return True
        u.EnumWindows(visit,0)
        # Windows IME may create an additional visible CiceroUIWndFrame for this PID.
        # Select only the actual game title; still reject ambiguous game windows.
        rows=[row for row in rows if row['title'].startswith('Minecraft')] if a.mc else [row for row in rows if row['title']=='Dead Cells with Core Modding']
        print(json.dumps(rows,ensure_ascii=True))
        if a.action!="inspect":
            if len(rows)!=1:raise ValueError("exactly one visible lab window required")
            hwnd=rows[0]["hwnd"]
            if a.mc and not rows[0]["title"].startswith("Minecraft"):raise ValueError("recorded Minecraft window title differs")
            if a.action=="close":
                u.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
                if not u.PostMessageW(hwnd,0x10,0,0):raise c.WinError(c.get_last_error())
                print("DC_LAB_NORMAL_CLOSE_REQUESTED")
            elif a.action in {"minimize","show-inactive"}:
                u.ShowWindowAsync.argtypes=[w.HWND,c.c_int]
                u.ShowWindowAsync(hwnd,6 if a.action=="minimize" else 4)
                print("MC_WINDOW_STATE",a.action)
            elif a.action in {"escape","enter","space","f3","f5","f7"}:
                if a.action in {"f3","f5"} and not a.mc:raise ValueError("debug/camera keys only allowed for MC")
                import time
                u.GetForegroundWindow.restype=w.HWND
                if u.GetForegroundWindow()!=hwnd:raise ValueError("input requires foreground lab window")
                class Keyboard(c.Structure):
                    _fields_=[("vk",w.WORD),("scan",w.WORD),("flags",w.DWORD),("time",w.DWORD),("extra",c.c_size_t)]
                class Mouse(c.Structure):
                    _fields_=[("x",w.LONG),("y",w.LONG),("data",w.DWORD),("flags",w.DWORD),("time",w.DWORD),("extra",c.c_size_t)]
                class Union(c.Union):_fields_=[("keyboard",Keyboard),("mouse",Mouse)]
                class Input(c.Structure):_fields_=[("type",w.DWORD),("value",Union)]
                u.SendInput.argtypes=[w.UINT,c.POINTER(Input),c.c_int]
                def send(flags):
                    value=Input(type=1,value=Union(keyboard=Keyboard(vk=0,scan={"f3":0x3d,"f5":0x3f,"f7":0x41,"escape":1,"enter":0x1c,"space":0x39}[a.action],flags=flags)))
                    if u.SendInput(1,c.byref(value),c.sizeof(value))!=1:raise c.WinError(c.get_last_error())
                try:send(8);time.sleep(a.hold_ms/1000)
                finally:send(8|2)
                print("DC_FOREGROUND_ESCAPE_SCAN_SENT")
            elif a.action=="capture":
                from PIL import ImageGrab
                import time
                u.GetForegroundWindow.restype=w.HWND;u.GetWindowRect.argtypes=[w.HWND,c.POINTER(w.RECT)]
                if u.GetForegroundWindow()!=hwnd:raise ValueError("lab window must be foreground for visible evidence")
                rect=w.RECT()
                if not u.GetWindowRect(hwnd,c.byref(rect)):raise c.WinError(c.get_last_error())
                dest=lab/"dc-frame"/("visible-"+str(time.time_ns())+".png")
                ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom)).save(dest)
                print("DC_VISIBLE_WINDOW_CAPTURED",dest)
            else:
                u.ShowWindowAsync.argtypes=[w.HWND,c.c_int];u.SetForegroundWindow.argtypes=[w.HWND]
                u.ShowWindowAsync(hwnd,9)
                u.GetForegroundWindow.restype=w.HWND
                foreground=u.GetForegroundWindow();foreground_thread=u.GetWindowThreadProcessId(foreground,None)
                current_thread=k.GetCurrentThreadId();attached=False
                try:
                    if foreground_thread!=current_thread:attached=bool(u.AttachThreadInput(current_thread,foreground_thread,True))
                    print("FOREGROUND_RESULT",bool(u.SetForegroundWindow(hwnd)))
                finally:
                    if attached:u.AttachThreadInput(current_thread,foreground_thread,False)
    finally:k.CloseHandle(handle)


if __name__=="__main__":main()
