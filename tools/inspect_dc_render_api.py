"""Extract only installed GameProxy public render signatures via Cecil; no decompilation or game load."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/dc-render-api"


def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/"appdata").mkdir(exist_ok=True)
    project=ROOT/"tools/dotnet/RenderSymbols/RenderSymbols.csproj";original=ROOT.parent/"cache/GameProxy.dll"
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    env={**os.environ,"DOTNET_CLI_HOME":str(OUT/"dotnet-home"),"APPDATA":str(OUT/"appdata"),"DOTNET_CLI_UI_LANGUAGE":"en","DOTNET_CLI_TELEMETRY_OPTOUT":"1"}
    commands=[["dotnet","restore",project,"--configfile",ROOT/"NuGet.Config"],["dotnet","build",project,"-c","Release","--no-restore","--nologo"],
              ["dotnet",project.parent/"bin/Release/net10.0/RenderSymbols.dll",original,OUT/"report.json"]]
    for command in commands:
        result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    report=json.loads((OUT/"report.json").read_text(encoding="utf-8"))
    if hashlib.sha256(original.read_bytes()).hexdigest()!=before or report["sha256"]!=before:raise ValueError("binding changed during metadata read")
    print(result.stdout.strip());print("REPORT",OUT/"report.json")


if __name__=="__main__":main()
