"""Replace only our pinned HUD diagnostic; preserve the established world origin and guard."""
import ctypes
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec_path=LAB/"dc-launch-spec.json";spec=json.loads(spec_path.read_text(encoding="utf-8"))
    if not spec.get("include_frame_probe") or Path(spec["cwd"]).resolve()!=LAB/"dc-game" or not (LAB/"dc-game/MCDN_ISOLATED_DC_LAB").is_file():raise ValueError("existing marked frame lab required")
    kernel=ctypes.WinDLL("kernel32",use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    pid=json.loads((LAB/"dc-process.json").read_text())["pid"];handle=kernel.OpenProcess(0x1000,False,pid)
    if handle:
        try:
            code=ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259:raise ValueError("close prior DC lab normally before replacing")
        finally:kernel.CloseHandle(handle)
    for name,digest in spec["package_files"].items():
        if sha(LAB/name)!=digest:raise ValueError("installed package differs from owned launch spec")
    build=json.loads((ROOT/"artifacts/dc-render-api/build-report.json").read_text())
    if build["runtime_gameproxy_sha256"]!=sha(ROOT.parent/"cache/GameProxy.dll"):raise ValueError("runtime binding changed")
    for name,digest in {**build["sources"],**build.get("linked_sources",{}),**build["packages"]}.items():
        if sha(ROOT/name)!=digest:raise ValueError("new build source/package changed")
    package=LAB/"packages/McdnDcFrameProbe";names={p.name for p in package.iterdir()}
    if names!={"Mcdn.DcFrameProbe.dll","modinfo.json"}:raise ValueError("unexpected package files")
    backup=ROOT/"artifacts/backups"/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-dc-frame-replace")
    backup.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(backup/"lab-before.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        files=[spec_path,*sorted((LAB/"dc-mods/McdnDcFrameProbe").iterdir()),LAB/"dc-logs/log_latest.log",LAB/"dc-process.json"]
        files += [p for p in (LAB/"dc-game/save").rglob("*") if p.is_file()]
        for path in files:archive.write(path,path.relative_to(LAB))
    (backup/"manifest.json").write_text(json.dumps({"scope":"private lab save, prior own HUD package and launch identity; original roots untouched", "zip_sha256":sha(backup/"lab-before.zip"),"files":{str(p.relative_to(LAB)):sha(p) for p in files}},indent=2),encoding="utf-8")
    for name in sorted(names):
        target=LAB/"dc-mods/McdnDcFrameProbe"/name;shutil.copyfile(package/name,target)
        spec["package_files"][str(target.relative_to(LAB))]=sha(target)
        spec["private_game_files"][str(target.relative_to(LAB))]=sha(target)
    temp=spec_path.with_suffix(".json.tmp");temp.write_text(json.dumps(spec,indent=2),encoding="utf-8");temp.replace(spec_path)
    print("DC_FRAME_OWNED_REPLACE_PASS",backup)


if __name__=="__main__":main()
