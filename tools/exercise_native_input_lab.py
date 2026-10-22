"""Bounded real DC foreground keyboard experiment, with native status observations."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import time
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]


def main():
    lab = ROOT / 'artifacts/lab'
    pointer = json.loads((lab / 'live-color/current-session.json').read_text())
    manifest = Path(pointer['manifest'])
    cfg = json.loads(manifest.read_text())
    directory = manifest.parent
    process = json.loads((lab / 'dc-process.json').read_text())
    if not cfg.get('inputLab') or cfg['eligibleForControl'] or cfg['expiresUnixMs'] <= time.time()*1000:
        raise ValueError('current unexpired diagnostic input session required')
    if (directory / 'keyboard-experiment.json').exists():
        raise ValueError('one experiment per session')
    u = c.WinDLL('user32', use_last_error=True)
    u.GetForegroundWindow.restype = w.HWND
    u.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
    u.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
    u.SetThreadDpiAwarenessContext.argtypes = [c.c_void_p]
    u.SetThreadDpiAwarenessContext.restype = c.c_void_p
    if not u.SetThreadDpiAwarenessContext(c.c_void_p(-4)):
        raise c.WinError(c.get_last_error())
    class Keyboard(c.Structure):
        _fields_ = [('vk', w.WORD), ('scan', w.WORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', c.c_size_t)]
    class Mouse(c.Structure):
        _fields_ = [('x', w.LONG), ('y', w.LONG), ('data', w.DWORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', c.c_size_t)]
    class Union(c.Union):
        _fields_ = [('keyboard', Keyboard), ('mouse', Mouse)]
    class Input(c.Structure):
        _fields_ = [('type', w.DWORD), ('value', Union)]
    u.SendInput.argtypes = [w.UINT, c.POINTER(Input), c.c_int]
    held = set()
    events, samples, captures = [], [], []
    def own():
        hwnd = u.GetForegroundWindow()
        pid = w.DWORD()
        u.GetWindowThreadProcessId(hwnd, c.byref(pid))
        if pid.value != process['pid']:
            raise ValueError('only foreground DC input allowed')
        return hwnd
    def key(scan, up=False):
        if not up:
            own()
        value = Input(type=1, value=Union(keyboard=Keyboard(scan=scan, flags=8 | (2 if up else 0))))
        if u.SendInput(1, c.byref(value), c.sizeof(value)) != 1:
            raise c.WinError(c.get_last_error())
        held.discard(scan) if up else held.add(scan)
        events.append(dict(scan=scan, up=up, unixNs=time.time_ns()))
    def tap(scan):
        key(scan)
        time.sleep(.1)
        key(scan, True)
    def mouse(dx,dy):
        own()
        value=Input(type=0,value=Union(mouse=Mouse(x=dx,y=dy,flags=1)))
        if u.SendInput(1,c.byref(value),c.sizeof(value))!=1:
            raise c.WinError(c.get_last_error())
        events.append(dict(mouseX=dx,mouseY=dy,unixNs=time.time_ns()))
    def state():
        path = directory / 'native-input-states.jsonl'
        if not path.exists():
            return None
        lines = path.read_bytes().split(b'\n')
        return json.loads(lines[-2]) if len(lines) > 1 else None
    def observe():
        hwnd = own()
        value = state()
        consumer = directory / 'consumer-latest.json'
        if value and consumer.exists():
            # Optional latest snapshots are atomically replaced by the writer. A transient
            # Windows sharing violation must not abort native input or its finally recovery.
            try:
                uploaded=json.loads(consumer.read_text())
            except (PermissionError,FileNotFoundError):
                uploaded=None
            if uploaded is not None:
                samples.append(dict(foreground_pid=process['pid'], observedUnixNs=time.time_ns(),
                                    native=value, consumer=uploaded))
        return hwnd, value
    def wait(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            observe()
            time.sleep(.025)
    def until(stage, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            _, value = observe()
            if value and value['Stage'] == stage:
                return value
            time.sleep(.025)
        raise ValueError('native stage missing: ' + stage)
    def capture(label):
        hwnd = own()
        rect = w.RECT()
        if not u.GetWindowRect(hwnd, c.byref(rect)):
            raise c.WinError(c.get_last_error())
        path = directory / ('input-' + label + '.png')
        ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(path)
        captures.append(str(path))
    def screen(expected):
        end=time.monotonic()+3
        while time.monotonic()<end:
            _,value=observe()
            if value and value['Stage']=='active' and value.get('Screen')==expected:return
            time.sleep(.025)
        raise ValueError('native inventory screen missing: '+expected)
    started = time.time_ns()
    started_native_stage = None
    activated = released = success = False
    error = None
    try:
        initial = state()
        started_native_stage = initial.get('Stage') if initial else None
        if started_native_stage == 'active' and not cfg.get('testWrongWorld'):
            activated = True
            capture('ready')  # Required starting-frame evidence; stage is recorded below.
        else:
            until('ready', 3)
            capture('ready')
        if cfg.get('testWrongWorld'):
            tap(0x41)
            wait(1)
            _,refused=observe()
            if refused['Stage']!='ready' or refused['Consumed'] or (directory/'native-host-input.jsonl').exists():
                raise ValueError('wrong DC world received native player ownership')
            capture('world-refused')
            success=True
            return
        if not activated:
            tap(0x41)
            activated = True
            until('active', 3)
        key(0x11)  # W: native forward towards the fractional DC wall
        wait(2)
        capture('wall')
        tap(0x39)  # native jump while continuing to approach wall
        wait(.2)
        capture('jump')
        key(0x11, True)
        wait(.8)
        key(0x20)  # D: depth movement
        wait(.15)
        key(0x20, True)
        wait(.3)
        key(0x1f)  # S: native retreat
        wait(.4)
        key(0x1f, True)
        wait(.4)
        if cfg.get('viewControl'):
            mouse(220,-80)
            wait(.4)
            capture('look-third')
            tap(0x3f)  # F5: third person front
            wait(.4)
            tap(0x3f)  # F5: first person
            wait(.5)
            capture('look-first')
            mouse(-100,40)
            wait(.4)
            tap(0x3f)  # F5: third person back
            wait(.4)
        if cfg.get('inventoryControl'):
            tap(0x12)  # E: actual vanilla InventoryScreen
            screen('inventory')
            wait(.5)
            capture('inventory')
            key(0x11)
            key(0x39)
            wait(.8)  # Protocol input continues; native GUI must suppress movement.
            key(0x11,True)
            key(0x39,True)
            wait(.25)
            tap(0x12)
            screen('none')
            wait(.25)
            tap(0x12)
            screen('inventory')  # F7 must close this owned GUI as part of recovery.
            wait(.3)
        tap(0x41)
        released = True
        returned = until('restored', 3)
        if not returned['InputRestored']:
            raise ValueError('native original input reference not restored')
        wait(2)
        capture('returned')
        success = True
    except Exception as ex:
        error = str(ex)
        raise
    finally:
        for scan in list(held):
            key(scan, True)
        if activated and not released:
            try:
                tap(0x41)
            except Exception:
                pass  # host foreground watchdog also releases on focus loss
        (directory / 'keyboard-experiment.json').write_text(json.dumps(dict(
            success=success, error=error, pid=process['pid'], startedUnixNs=started,
            startedNativeStage=started_native_stage,
            endedUnixNs=time.time_ns(), events=events, samples=samples, captures=captures,
            allInjectedKeysReleased=not held, productionModeGranted=False), indent=2))
    print('NATIVE_INPUT_EXPERIMENT_OBSERVED', len(samples), 'samples', len(captures), 'captures')


if __name__ == '__main__':
    main()
