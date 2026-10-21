"""Actual Win64 C# / Java processes and named mutexes; synthetic RGBA only, never launches games."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/mailbox"


def bounded_line(process,timeout=15):
    future=concurrent.futures.Future()
    def read():
        try:future.set_result(process.stdout.readline())
        except Exception as error:future.set_exception(error)
    threading.Thread(target=read,daemon=True).start()
    line=future.result(timeout)
    if not line:raise RuntimeError("mailbox server exited before readiness")
    return json.loads(line)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--java-home",required=True,type=Path);parser.add_argument("--jni-home",type=Path);args=parser.parse_args()
    command=["python",ROOT/"tools/build_mailbox.py","--java-home",args.java_home]
    if args.jni_home:command.extend(["--jni-home",args.jni_home])
    subprocess.run(list(map(str,command)),cwd=ROOT,check=True,timeout=60)
    build=json.loads((OUT/"build-report.json").read_text(encoding="utf-8"))
    dll=Path(build["native_dll"]);digest=build["native_sha256"]
    if hashlib.sha256(dll.read_bytes()).hexdigest()!=digest:raise ValueError("native build identity mismatch")
    fixture=ROOT/"artifacts/world/vectors/ready.frame"
    if not fixture.is_file():raise ValueError("run verify_world.py once to produce the validated frame header fixture")
    results=[];case_root=OUT/"cases";case_root.mkdir(exist_ok=True)
    env={**os.environ,"DOTNET_CLI_HOME":str(OUT/"dotnet-home"),"APPDATA":str(OUT/"appdata"),"DOTNET_CLI_UI_LANGUAGE":"en","DOTNET_CLI_TELEMETRY_OPTOUT":"1"}
    for mode in ["stress","reverse","corrupt-pixels","abandoned-slot","abandoned-publication"]:
        server=None;guest=None
        with (case_root/(mode+"-dotnet.stderr.log")).open("w",encoding="utf-8") as server_log:
            try:
                server=subprocess.Popen(list(map(str,["dotnet",ROOT/"tests/ipc/dotnet/bin/Release/net10.0/Mcdn.Mailbox.Bench.dll",dll,digest,mode,case_root,fixture])),cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=server_log,text=True,encoding="utf-8")
                ready=bounded_line(server)
                guest=subprocess.Popen(list(map(str,[args.java_home/"bin/java.exe","--enable-native-access=ALL-UNNAMED","-cp",OUT/"java","dev.mcdn.ipc.MailboxBench",dll,digest,fixture,ready["file"],ready["session"],ready["capacity"],ready["port"]])),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8")
                guest_stdout,guest_stderr=guest.communicate(timeout=35)
                (case_root/(mode+"-java.stderr.log")).write_text(guest_stderr,encoding="utf-8")
                output,_=server.communicate(timeout=20)
                if guest.returncode or server.returncode:raise RuntimeError(f"{mode}: Java={guest.returncode} C#={server.returncode}; {guest_stderr}; {output}; {server_log.name}")
                result=json.loads(output.strip());assert result["status"]=="pass" and result["mode"]==mode
                result.update(file=ready["file"],session=ready["session"],guest_exit=guest.returncode,host_exit=server.returncode)
                results.append(result);print("MAILBOX_CASE_PASS",mode,flush=True)
            finally:
                # Only children created by this script; no game or unrelated process control.
                for process in [guest,server]:
                    if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
    report={"status":"pass","scope":"synthetic RGBA cross-process Win32 mapping/JNI/PInvoke, not native game frames or DC display", "build":build,"fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),"cases":results}
    (OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("MAILBOX_VERIFY_PASS 5 real cross-process cases; no game launch/input/capture")


if __name__=="__main__":main()
