"""Validate and start ONLY the prepared DC lab. Invoke from the user's offline desktop session."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group();mode.add_argument("--launch",action="store_true");mode.add_argument("--preflight",action="store_true");p.add_argument("--missing-loader-check",action="store_true");a=p.parse_args()
    if a.missing_loader_check and not a.preflight:p.error("--missing-loader-check requires --preflight")
    spec=json.loads((LAB/"dc-launch-spec.json").read_text(encoding="utf-8"))
    game=Path(spec["cwd"]).resolve()
    if game!=LAB/"dc-game" or not (game/"MCDN_ISOLATED_DC_LAB").is_file():raise ValueError("lab path/marker mismatch")
    if sha(Path(spec["args"][0]))!=spec["shell_sha256"]:raise ValueError("DCCM shell changed")
    for name,digest in spec["package_files"].items():
        if sha(LAB/name)!=digest:raise ValueError("DC probe package changed")
    for name,digest in spec["private_game_files"].items():
        if Path(name).suffix.lower() in {".pak",".exe",".dll",".hdll"} and sha(LAB/name)!=digest:
            raise ValueError("private game/runtime file changed: "+name)
    if spec["environment"].get("MCDN_DC_ISOLATED_LAB")!="1":raise ValueError("save guard required")
    if spec["environment"].get("DCCM_CUSTOM_STARTUP_TYPE")!="Mcdn.DcProbe.LabStartup, Mcdn.DcProbe":raise ValueError("independent startup guard required")
    if not (LAB/"dc-plugins/ModCore.ModLoader.Default/ModCore.ModLoader.Default.dll").is_file():raise ValueError("default mod-loader plugin missing")
    if spec.get("include_frame_probe") and sha(LAB/"dc-frame/playlist.json")!=spec["environment"].get("MCDN_DC_FRAME_PLAYLIST_SHA256"):
        raise ValueError("recorded native frame playlist changed")
    if spec["environment"].get("MCDN_DC_LIVE_COLOR_MANIFEST"):
        live=Path(spec["environment"]["MCDN_DC_LIVE_COLOR_MANIFEST"]).resolve()
        if not live.is_relative_to(LAB/"live-color") or sha(live)!=spec["environment"]["MCDN_DC_LIVE_COLOR_SHA256"]:
            raise ValueError("live diagnostic manifest identity changed")
        if json.loads(live.read_text())["expiresUnixMs"]<=time.time()*1000:raise ValueError("live session expired; arm a new session while games are closed")
    if not a.launch and not a.preflight:
        print("DC_LAB_LAUNCH_CHECK_PASS private paths and built package verified; not launched");return
    record=LAB/"dc-process.json"
    if record.exists():
        pid=json.loads(record.read_text())["pid"]
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x1000,False,pid)
        if handle:
            code=ctypes.c_ulong();kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            try:
                if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259:raise ValueError("prior lab process is still active")
            finally:kernel.CloseHandle(handle)
    env={**os.environ,**spec["environment"]}
    if a.launch:
        for name in ["dc-native-preflight-report.json","dc-negative-preflight-report.json"]:
            proof=json.loads((LAB/name).read_text(encoding="utf-8"))
            if proof["status"]!="pass" or proof.get("launch_spec_sha256")!=sha(LAB/"dc-launch-spec.json") or proof.get("package_files")!=spec["package_files"]:
                raise ValueError("matching positive/negative native preflight required before launch")
    if a.preflight:
        env["MCDN_DC_GUARD_CHECK_ONLY"]="1"
        if a.missing_loader_check:
            empty=LAB/"dc-empty-plugins";empty.mkdir(exist_ok=True)
            if any(empty.iterdir()):raise ValueError("negative-test plugin directory must be empty")
            env["DCCM_OverridePath_CORE_PLUGINS"]=str(empty)
        run=subprocess.run([spec["executable"],*spec["args"]],cwd=game,env=env,capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW,timeout=40)
        raw=run.stdout+run.stderr;prefix="dc-negative-preflight" if a.missing_loader_check else "dc-preflight"
        (LAB/(prefix+"-console.log")).write_bytes(raw)
        passed=(run.returncode==2 and b"required probe/guard missing after mod initialization" in raw and b"MCDN_DC_LAB_GUARD_READY" in raw
                if a.missing_loader_check else run.returncode==0 and b"MCDN_DC_NATIVE_PREFLIGHT_PASS" in raw)
        passed=passed and b"MCDN_DC_ORIGINAL_ENTRY_RELEASED" not in raw
        if spec.get("include_frame_probe") and not a.missing_loader_check:passed=passed and b"MCDN_DC_FRAME_PROBE_INITIALIZED" in raw
        report={"scope":"real DC native VM/guard/probe startup; exits before original game entry, no character scene",
                "status":"pass" if passed else "failed","returncode":run.returncode,"console_sha256":hashlib.sha256(raw).hexdigest(),
                "launch_spec_sha256":sha(LAB/"dc-launch-spec.json"),"package_files":spec["package_files"],"missing_loader_check":a.missing_loader_check,
                "markers":[s for s in raw.decode("utf-8",errors="replace").splitlines() if "MCDN" in s]}
        (LAB/("dc-negative-preflight-report.json" if a.missing_loader_check else "dc-native-preflight-report.json")).write_text(json.dumps(report,indent=2),encoding="utf-8")
        for line in report["markers"]:print(line.encode("ascii",errors="backslashreplace").decode())
        if not passed:raise ValueError("native startup preflight failed; see dc-preflight-console.log")
        print("DC_NATIVE_NEGATIVE_PREFLIGHT_PASS missing loader refused before game entry" if a.missing_loader_check else "DC_NATIVE_PREFLIGHT_PASS");return
    # No extra console window; SDL still creates the real game window. Never send focus/input here.
    with (LAB/"dc-console.log").open("ab") as log:
        process=subprocess.Popen([spec["executable"],*spec["args"]],cwd=game,env=env,stdout=log,stderr=log,
                                 creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    record.write_text(json.dumps({"pid":process.pid,"started_at_ns":time.time_ns(),"scope":"own isolated DC process only"},indent=2),encoding="utf-8")
    print("DC_LAB_STARTED",process.pid)


if __name__=="__main__":
    try:main()
    except Exception as ex:print("DC_LAB_REFUSED",str(ex));raise SystemExit(1)
