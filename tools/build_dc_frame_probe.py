"""Build own native DC HUD diagnostic against the private installed-version binding reference."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/dc-render-api"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/"appdata").mkdir(exist_ok=True)
    project=ROOT/"src/dotnet/Mcdn.DcFrameProbe/Mcdn.DcFrameProbe.csproj"
    env={**os.environ,"DOTNET_CLI_HOME":str(OUT/"dotnet-home"),"APPDATA":str(OUT/"appdata"),"DOTNET_CLI_UI_LANGUAGE":"en","DOTNET_CLI_TELEMETRY_OPTOUT":"1"}
    for command in [["dotnet","restore",project,"--configfile",ROOT/"NuGet.Config"],["dotnet","build",project,"-c","Release","--no-restore","--nologo"]]:
        run=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    package=ROOT/"artifacts/lab/packages/McdnDcFrameProbe";package.mkdir(exist_ok=True)
    for path in [project.parent/"bin/Release/net10.0/Mcdn.DcFrameProbe.dll",project.parent/"modinfo.json"]:(package/path.name).write_bytes(path.read_bytes())
    report={"scope":"compiled actual DC/Heaps native HUD texture adapter; not native runtime/render evidence", "runtime_gameproxy_sha256":sha(ROOT.parent/"cache/GameProxy.dll"),
            "packages":{str(path.relative_to(ROOT)):sha(path) for path in sorted(package.iterdir())},
            "sources":{str(path.relative_to(ROOT)):sha(path) for path in sorted(project.parent.iterdir()) if path.is_file()},"linked_sources":{str(path.relative_to(ROOT)):sha(path) for path in [ROOT/"src/dotnet/Mcdn.FrameMailbox/FrameMailbox.cs",ROOT/"src/dotnet/Mcdn.Protocol/WorldColorFrame.cs",ROOT/"src/dotnet/Mcdn.Protocol/Frame.cs",ROOT/'src/dotnet/Mcdn.Protocol/Control.cs',ROOT/'src/dotnet/Mcdn.Protocol/Wire.cs']}}
    (OUT/"build-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("DC_FRAME_PROBE_BUILD_PASS",package)


if __name__=="__main__":main()
