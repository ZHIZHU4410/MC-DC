"""Build our Win64 JNI/PInvoke mailbox with the installed MSVC/SDK/JDK; no game install or launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/mailbox"


def run(args,env=None):
    result=subprocess.run(list(map(str,args)),cwd=OUT,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout+result.stderr


def main():
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path,required=True);p.add_argument("--jni-home",type=Path);a=p.parse_args()
    jni_home=a.jni_home or a.java_home
    for header in [jni_home/"include/jni.h",jni_home/"include/win32/jni_md.h"]:
        if not header.is_file():raise ValueError(f"JNI development header missing: {header}; specify installed full JDK with --jni-home")
    OUT.mkdir(parents=True,exist_ok=True);(OUT/"headers").mkdir(exist_ok=True);(OUT/"java").mkdir(exist_ok=True)
    sources=[*sorted((ROOT/"src/java").rglob("*.java")),*sorted((ROOT/"src/ipc/java").rglob("*.java")),*sorted((ROOT/"tests/ipc/java").rglob("*.java"))]
    run([a.java_home/"bin/javac.exe","-J-Duser.language=en","-J-Duser.country=US","-encoding","UTF-8","-Xlint:all","-Werror","-h",OUT/"headers","-d",OUT/"java",*sources])
    vswhere=Path(os.environ.get("ProgramFiles(x86)",r"C:\Program Files (x86)"))/"Microsoft Visual Studio/Installer/vswhere.exe"
    installations=run([vswhere,"-products","*","-requires","Microsoft.VisualStudio.Component.VC.Tools.x86.x64","-property","installationPath"]).splitlines()
    if not installations:raise ValueError("installed MSVC x64 toolchain required")
    vc=max((Path(installations[0])/"VC/Tools/MSVC").iterdir(),key=lambda path:tuple(map(int,path.name.split('.'))))
    kits=Path(os.environ.get("ProgramFiles(x86)",r"C:\Program Files (x86)"))/"Windows Kits/10"
    sdk=max((kits/"Lib").iterdir(),key=lambda path:tuple(map(int,path.name.split('.')))).name
    bin_dir=vc/"bin/Hostx64/x64"
    env={**os.environ,"VSLANG":"1033","PATH":str(bin_dir)+os.pathsep+os.environ["PATH"],
         "INCLUDE":";".join(map(str,[vc/"include",kits/"Include"/sdk/"ucrt",kits/"Include"/sdk/"shared",kits/"Include"/sdk/"um",jni_home/"include",jni_home/"include/win32",OUT/"headers"])),
         "LIB":";".join(map(str,[vc/"lib/x64",kits/"Lib"/sdk/"ucrt/x64",kits/"Lib"/sdk/"um/x64"]))}
    dll=OUT/"mcdn_ipc.dll"
    run([bin_dir/"cl.exe","/nologo","/std:c++20","/W4","/WX","/EHsc","/LD","/MT","/O2","/utf-8","/DWIN32_LEAN_AND_MEAN","/DNOMINMAX",
         ROOT/"src/native/mcdn_ipc.cpp","/Fo"+str(OUT/"mcdn_ipc.obj"),"/Fe"+str(dll),"/link","/OUT:"+str(dll),"kernel32.lib","advapi32.lib"],env)
    dotnet={**os.environ,"DOTNET_CLI_HOME":str(OUT/"dotnet-home"),"APPDATA":str(OUT/"appdata"),"DOTNET_CLI_UI_LANGUAGE":"en","DOTNET_CLI_TELEMETRY_OPTOUT":"1"}
    (OUT/"appdata").mkdir(exist_ok=True)
    projects=[ROOT/"src/dotnet/Mcdn.FrameMailbox/Mcdn.FrameMailbox.csproj"]
    bench=ROOT/"tests/ipc/dotnet/Mcdn.Mailbox.Bench.csproj"
    if bench.exists():projects=[bench]
    for project in projects:
        run(["dotnet","restore",project,"--configfile",ROOT/"NuGet.Config"],dotnet)
        run(["dotnet","build",project,"-c","Release","--no-restore","--nologo"],dotnet)
    report={"scope":"compiled native Win32 JNI/PInvoke mailbox, not a game frame capture",
            "native_dll":str(dll),"native_sha256":hashlib.sha256(dll.read_bytes()).hexdigest(),"msvc":vc.name,"windows_sdk":sdk,
            "java_home":str(a.java_home),"jni_home":str(jni_home),"jni_headers":{str(h):hashlib.sha256(h.read_bytes()).hexdigest() for h in [jni_home/"include/jni.h",jni_home/"include/win32/jni_md.h"]},
            "build_scripts":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/"tools/build_mailbox.py",ROOT/"tools/verify_mailbox.py"]},
            "sources":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in [ROOT/"src/native",ROOT/"src/ipc",ROOT/"src/java",ROOT/"src/dotnet/Mcdn.Protocol",ROOT/"src/dotnet/Mcdn.FrameMailbox",ROOT/"tests/ipc"] for f in sorted(folder.rglob('*')) if f.suffix in ['.cpp','.java','.cs','.csproj'] and 'bin' not in f.parts and 'obj' not in f.parts}}
    (OUT/"build-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("MAILBOX_BUILD_PASS MSVC="+vc.name+" SDK="+sdk+" JNI + P/Invoke")
    print("DLL_SHA256",report["native_sha256"])


if __name__=="__main__":main()
