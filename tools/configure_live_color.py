"""Arm the isolated profiles with one pinned diagnostic session after both games have exited."""
import argparse
import ctypes
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group();m.add_argument("--arm",action="store_true");m.add_argument("--disarm",action="store_true");a=p.parse_args()
    pointer=json.loads((LAB/"live-color/current-session.json").read_text());manifest=Path(pointer["manifest"])
    if not manifest.resolve().is_relative_to(LAB/"live-color") or sha(manifest)!=pointer["sha256"]:raise ValueError("pinned live session required")
    cfg=json.loads(manifest.read_text());game=Path(cfg["gameDir"])
    physics=game==Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3')
    if game not in [Path(r"D:\MC\.minecraft\versions\MC-DC-Lab-26.3"),Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3')] or not (game/"MCDN_ISOLATED_LAB").is_file() or (physics and not (game/'MCDN_PHYSICS_LAB').is_file()):raise ValueError("only marked MC lab")
    target=game/"mcdn-world-color.json";record=LAB/"live-color/installed-pointer.json"
    if target.exists():
        previous=json.loads(record.read_text())
        if previous["sha256"]!=sha(target):raise ValueError("existing live pointer is not the recorded owned file")
    options=game/"options.txt";spec=LAB/"dc-launch-spec.json"
    if not a.arm and not a.disarm:print("LIVE_COLOR_ARM_READY");return
    kernel=ctypes.WinDLL("kernel32",use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    for record_path in [LAB/"dc-process.json",LAB/"mc-live-process.json",ROOT/'artifacts/physics/process.json']:
        if not record_path.exists():continue
        pid=json.loads(record_path.read_text(encoding="utf-8-sig"))["pid"];handle=kernel.OpenProcess(0x1000,False,pid)
        if handle:
            try:
                code=ctypes.c_ulong()
                if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259:raise ValueError("normally close recorded game processes before changing live configuration")
            finally:kernel.CloseHandle(handle)
    # A live MC world holds session.lock; fail before writing profile configuration.
    for lock in (game/"saves").rglob("session.lock"):lock.read_bytes()
    backup=ROOT/"artifacts/backups"/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-live-color-config");backup.mkdir(parents=True)
    with zipfile.ZipFile(backup/"profiles-before.zip","x",zipfile.ZIP_DEFLATED) as archive:
        for path in [options,spec,*([game/'mcdn-lab.json',game/'mcdn-physics.json'] if physics else []),*([target] if target.exists() else [])]:archive.write(path,str(path.relative_to(game)) if path.is_relative_to(game) else "dc-launch-spec.json")
    if a.disarm:
        if not target.exists():raise ValueError("owned live pointer already absent")
        dc=json.loads(spec.read_text())
        if dc["environment"].get("MCDN_DC_LIVE_COLOR_SHA256")!=pointer["sha256"]:raise ValueError("DC is armed for a different session")
        dc["environment"].pop("MCDN_DC_LIVE_COLOR_MANIFEST");dc["environment"].pop("MCDN_DC_LIVE_COLOR_SHA256")
        if physics:
            native=json.loads((game/'mcdn-physics.json').read_text())
            if native.get('inputManifestSha256')==pointer['sha256']:
                native.pop('inputManifest',None);native.pop('inputManifestSha256',None);(game/'mcdn-physics.json').write_text(json.dumps(native,indent=2),encoding='utf-8')
        spec.write_text(json.dumps(dc,indent=2),encoding="utf-8");target.unlink()
        record.write_text(json.dumps({"status":"disarmed","session":cfg["session"],"backup":str(backup)},indent=2),encoding="utf-8")
        print("LIVE_COLOR_DISARMED; lab background option retained; BACKUP",backup);return
    before=options.read_text(encoding="utf-8");rows=before.splitlines();rows=[r for r in rows if not r.startswith("pauseOnLostFocus:")];rows.append("pauseOnLostFocus:false")
    if physics:
        frame=json.loads((game/'mcdn-lab.json').read_text());frame['outputDir']=str(LAB/'observations');(game/'mcdn-lab.json').write_text(json.dumps(frame,indent=2),encoding='utf-8')
        if cfg.get('inputLab'):
            native=json.loads((game/'mcdn-physics.json').read_text());native['inputManifest']=str(manifest);native['inputManifestSha256']=pointer['sha256'];(game/'mcdn-physics.json').write_text(json.dumps(native,indent=2),encoding='utf-8')
    target.write_text(json.dumps(pointer,indent=2),encoding="utf-8");options.write_text("\n".join(rows)+"\n",encoding="utf-8")
    dc=json.loads(spec.read_text());dc["environment"]["MCDN_DC_LIVE_COLOR_MANIFEST"]=str(manifest);dc["environment"]["MCDN_DC_LIVE_COLOR_SHA256"]=pointer["sha256"];spec.write_text(json.dumps(dc,indent=2),encoding="utf-8")
    record.write_text(json.dumps({"target":str(target),"sha256":sha(target),"backup":str(backup),"session":cfg["session"]},indent=2),encoding="utf-8")
    print("LIVE_COLOR_ARMED",cfg["session"],"BACKUP",backup)


if __name__=="__main__":main()
