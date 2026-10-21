"""Stage a private DC game/save/mod runtime and backup originals. Never start the game."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import time
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--include-frame-probe",action="store_true");args=parser.parse_args()
    original=ROOT.parent.parent;core=ROOT.parent;game=LAB/"dc-game"
    built=json.loads((LAB/"dc-build-report.json").read_text(encoding="utf-8"))
    package=LAB/"packages/McdnDcProbe"
    packages=[package]
    if args.include_frame_probe:
        frame_build=json.loads((ROOT/"artifacts/dc-render-api/build-report.json").read_text(encoding="utf-8"))
        if frame_build["runtime_gameproxy_sha256"]!=built["runtime_gameproxy_sha256"]:raise ValueError("frame binding differs")
        for name,digest in frame_build["packages"].items():
            if sha(ROOT/name)!=digest:raise ValueError("frame addon differs from build record")
        packages.append(LAB/"packages/McdnDcFrameProbe")
    for name,digest in built["packages"].items():
        if sha(ROOT/name)!=digest:raise ValueError("DC staged package differs from build record")
    if sha(core/"cache/GameProxy.dll")!=built["runtime_gameproxy_sha256"]:raise ValueError("runtime GameProxy changed")
    if shutil.disk_usage(LAB).free<3*1024**3 and not (game/"res.pak").exists():raise ValueError("need space for a separate private resource copy")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup=ROOT/"artifacts/backups"/(stamp+"-dc-originals");backup.mkdir(parents=True)
    before={}
    with ZipFile(backup/"save-and-config.zip","w",ZIP_DEFLATED) as archive:
        for folder in [original/"save",core/"config"]:
            for file in sorted(folder.rglob("*")):
                if file.is_file():
                    name=file.relative_to(original).as_posix();before[name]=sha(file);archive.write(file,name)
    (backup/"manifest.json").write_text(json.dumps({"scope":"original saves/config snapshot before isolated DC launch","source":str(original),"files":before},indent=2),encoding="utf-8")
    for file in [LAB/"dc-logs/log_latest.log",LAB/"dc-console.log"]:
        if file.is_file():shutil.copyfile(file,backup/file.name)
    copied={}
    previous_spec=LAB/"dc-launch-spec.json"
    previous=json.loads(previous_spec.read_text(encoding="utf-8")) if previous_spec.exists() else {}
    record=LAB/"dc-process.json"
    if record.exists():
        # User/process must close first; preserve the attempt record instead of overwriting it.
        import ctypes
        kernel=ctypes.WinDLL("kernel32",use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x1000,False,json.loads(record.read_text())["pid"])
        if handle:
            code=ctypes.c_ulong();kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            try:
                if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259:raise ValueError("close the existing DC lab before preparing another")
            finally:kernel.CloseHandle(handle)
        shutil.copyfile(record,backup/record.name)
    # Current lab saves are also preserved after its previous process has exited.
    lab_save_files={}
    with ZipFile(backup/"dc-lab-save.zip","w",ZIP_DEFLATED) as archive:
        for file in sorted((game/"save").rglob('*')):
            if file.is_file():
                name=file.relative_to(game).as_posix();lab_save_files[name]=sha(file);archive.write(file,name)
    (backup/"dc-lab-save-manifest.json").write_text(json.dumps(lab_save_files,indent=2),encoding="utf-8")
    def copy_file(source,dest):
        digest=sha(source)
        if dest.exists():
            old=sha(dest)
            if old!=digest:
                relative=str(dest.relative_to(LAB))
                if not dest.is_relative_to(LAB/"dc-mods") or previous.get("package_files",{}).get(relative)!=old:
                    raise ValueError("existing lab file differs; refusing overwrite: "+str(dest))
                saved=backup/"previous-probe"/dest.name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dest,saved)
                shutil.copyfile(source,dest)
        else:
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
            if sha(dest)!=digest:raise ValueError("copied file hash mismatch")
        copied[str(dest.relative_to(LAB))]=digest
    # Real copies: no hardlinks/junctions that could write through into the original install.
    for name in ["res.pak","deadcells_gl.exe","steam.hdll","steam_api64.dll"]:
        copy_file(original/name,game/name)
    for file in sorted((original/"lang").rglob("*")):
        if file.is_file():copy_file(file,game/"lang"/file.relative_to(original/"lang"))
    for name in ["GameProxy.dll","GameProxy.dll.cache","hlboot.dat","hlboot.dat.cache"]:
        copy_file(core/"cache"/name,LAB/"dc-cache"/name)
    mods=LAB/"dc-mods"
    for current in packages:
        for file in sorted(current.iterdir()):copy_file(file,mods/current.name/file.name)
    loader=core/"plugins/ModCore.ModLoader.Default/ModCore.ModLoader.Default.dll"
    copy_file(loader,LAB/"dc-plugins/ModCore.ModLoader.Default"/loader.name)
    paths={"GAME_ROOT":game,"SAVE_ROOT":game/"save","CORE_MODS":mods,"CORE_PLUGINS":LAB/"dc-plugins",
           "CORE_CONFIG":LAB/"dc-config","CORE_DATA":LAB/"dc-data","CORE_LOGS":LAB/"dc-logs","CORE_CACHE":LAB/"dc-cache"}
    for path in paths.values():path.mkdir(parents=True,exist_ok=True)
    marker=game/"MCDN_ISOLATED_DC_LAB"
    if not marker.exists():marker.write_text("Own disposable DC runtime; local saves only; original assets copied, not linked.\n",encoding="utf-8")
    config=paths["CORE_CONFIG"]/"modcore.json"
    if not config.exists():config.write_text(json.dumps({"EnableGoldberg":False,"GeneratePseudocodeAssembly":False,"AllowLockCursor":False},indent=2),encoding="utf-8")
    if json.loads(config.read_text(encoding="utf-8")).get("EnableGoldberg") is not False:raise ValueError("lab must use the legitimate installed Steam libraries")
    env={"DCCM_OverridePath_"+key:str(path) for key,path in paths.items()}
    env.update({"MCDN_LAB_ROOT":str(LAB),"MCDN_DC_ISOLATED_LAB":"1","DCCM_EXTRA_MODS_PATHS":"","DCCM_EXTRA_PLUGINS_PATHS":"","DCCM_START_WITH_NO_MODS":"false"})
    env["DCCM_LOAD_ADDITIONAL_ASSEMBLIES"]=str(mods/"McdnDcProbe/Mcdn.Protocol.dll")+";"+str(mods/"McdnDcProbe/Mcdn.DcProbe.dll")
    env["DCCM_CUSTOM_STARTUP_TYPE"]="Mcdn.DcProbe.LabStartup, Mcdn.DcProbe"
    env["DCCM_CUSTOM_STARTUP_METHOD"]="Main"
    if args.include_frame_probe:env["MCDN_DC_FRAME_PLAYLIST_SHA256"]=sha(LAB/"dc-frame/playlist.json")
    sample=LAB/"observations/mc-probe.json"
    if time.time()-sample.stat().st_mtime>3:raise ValueError("need a fresh MC lab observation to fix the map origin")
    observation=json.loads(sample.read_text(encoding="utf-8"))
    for axis in ["X","Y","Z"]:
        value=observation["player"+axis]
        if not math.isfinite(value) or abs(value)>=999000:raise ValueError("invalid MC origin")
        env["MCDN_MC_ORIGIN_"+axis]=str(value)
    shell=core/"core/host/DCCMShell.dll"
    spec={"scope":"private DC diagnostic runtime; user starts offline; no production Hero/input/render takeover",
          "status":"prepared, not launched","executable":shutil.which("dotnet"),"args":[str(shell)],"cwd":str(game),"environment":env,
          "shell_sha256":sha(shell),"package_files":{str((mods/current.name/file.name).relative_to(LAB)):sha(file) for current in packages for file in current.iterdir()},
          "include_frame_probe":args.include_frame_probe,
          "private_game_files":copied,"original_backup":str(backup),"original_root":str(original),
          "guard":"Before original game entry, marker/game/save roots and actual cloud checks must pass; failure exits with code 2"}
    (LAB/"dc-launch-spec.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")
    launcher=ROOT/"Start-DC-Lab.cmd"
    launcher.write_text('@echo off\r\npython "'+str(ROOT/"tools/start_dc_lab.py")+'" --launch\r\nif errorlevel 1 pause\r\n',encoding="utf-8")
    print("DC_LAB_PREPARED original saves/config backed up; private assets/mods/cache/save roots staged")
    print("LAUNCHER",launcher);print("BACKUP",backup)


if __name__=="__main__":main()
