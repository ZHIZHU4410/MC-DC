"""Build only our DC/Fabric probes, stage a separate lab; never install or launch a game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile
from verify_fabric_package import verify as verify_package

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/lab"

def run(command,env=None):
    p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout+p.stderr

def main():
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path);p.add_argument("--mc-version-dir",type=Path);p.add_argument("--dc-only",action="store_true");a=p.parse_args()
    if not a.dc_only and (a.java_home is None or a.mc_version_dir is None):p.error("provide --java-home and --mc-version-dir, or --dc-only")
    OUT.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"DOTNET_CLI_HOME":str(OUT/"dotnet-home"),"APPDATA":str(OUT/"appdata"),"DOTNET_CLI_UI_LANGUAGE":"en","DOTNET_CLI_TELEMETRY_OPTOUT":"1"}
    (OUT/"appdata").mkdir(exist_ok=True)
    helper=ROOT/"tools/dotnet/GameProxyRef/GameProxyRef.csproj"
    run(["dotnet","restore",helper,"--configfile",ROOT/"NuGet.Config"],env)
    run(["dotnet","build",helper,"-c","Release","--no-restore","--nologo"],env)
    original=ROOT.parent/"cache/GameProxy.dll";original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    reference=OUT/"references/GameProxy.dll"
    run(["dotnet",helper.parent/"bin/Release/net10.0/GameProxyRef.dll",original,reference],env)
    if hashlib.sha256(original.read_bytes()).hexdigest()!=original_hash:raise ValueError("runtime GameProxy changed")
    project=ROOT/"src/dotnet/Mcdn.DcProbe/Mcdn.DcProbe.csproj"
    run(["dotnet","restore",project,"--configfile",ROOT/"NuGet.Config"],env)
    run(["dotnet","build",project,"-c","Release","--no-restore","--nologo"],env)
    dc=OUT/"packages/McdnDcProbe";dc.mkdir(parents=True,exist_ok=True)
    for path in [project.parent/"bin/Release/net10.0/Mcdn.DcProbe.dll",ROOT/"src/dotnet/Mcdn.Protocol/bin/Release/net10.0/Mcdn.Protocol.dll",project.parent/"modinfo.json"]:
        (dc/path.name).write_bytes(path.read_bytes())
    (OUT/"dc-build-report.json").write_text(json.dumps({"scope":"DC probe/lab guard compiled against installed DCCM; not runtime verified",
        "runtime_gameproxy_sha256":original_hash,"compile_reference_sha256":hashlib.sha256(reference.read_bytes()).hexdigest(),
        "packages":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(dc.iterdir())},
        "sources":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in [ROOT/"src/dotnet/Mcdn.DcProbe",ROOT/"src/dotnet/Mcdn.Protocol"] for f in sorted(folder.glob("*.cs"))}},indent=2),encoding="utf-8")
    if a.dc_only:
        print("DC_PROBE_BUILD_PASS",dc);return
    version=a.mc_version_dir.resolve();meta=json.loads((version/(version.name+".json")).read_text(encoding="utf-8-sig"))
    cp=[version/(version.name+".jar")]; libraries=version.parent.parent/"libraries"
    for lib in meta["libraries"]:
        parts=lib["name"].split(":");group,artifact,ver=parts[:3];classifier="-"+parts[3] if len(parts)>3 else ""
        jar=libraries/group.replace(".","/")/artifact/ver/(artifact+"-"+ver+classifier+".jar")
        if jar.exists():cp.append(jar)
    sources=[*sorted((ROOT/"src/java").rglob("*.java")),*sorted((ROOT/"src/minecraft/java").rglob("*.java")),*sorted((ROOT/"src/fabric/java").rglob("*.java"))]
    quote=lambda value:'"'+str(value).replace("\\","/")+'"'
    jar=OUT/"packages/mcdn-lab-probe-0.5.0.jar"
    # Fresh compiler output prevents renamed/removed classes leaking from a previous build.
    with tempfile.TemporaryDirectory(prefix="fabric-classes-",dir=OUT) as temporary:
        classes=Path(temporary).resolve()
        if not classes.is_relative_to(OUT.resolve()):raise ValueError("compiler output outside workspace lab")
        args=OUT/"fabric-javac.args";args.write_text("\n".join(["-encoding","UTF-8","-proc:none","-classpath",quote(";".join(map(str,cp))),"-d",quote(classes),*map(quote,sources)]),encoding="utf-8")
        run([a.java_home/"bin/javac.exe","@"+str(args)])
        with zipfile.ZipFile(jar,"w",zipfile.ZIP_DEFLATED) as archive:
            for f in sorted(classes.rglob("*.class")):archive.write(f,f.relative_to(classes).as_posix())
            for f in sorted((ROOT/"src/fabric/resources").iterdir()):archive.write(f,f.name)
    package_check=verify_package(jar)
    # Deliberately separate from the user's launcher game directory and saves.
    game=OUT/"minecraft";game.mkdir(exist_ok=True);(game/"mods").mkdir(exist_ok=True)
    (game/"MCDN_ISOLATED_LAB").write_text("Own disposable lab only; no existing save is to be copied here.\n",encoding="utf-8")
    (game/"mods"/jar.name).write_bytes(jar.read_bytes())
    source=OUT/"dc-probe";source.mkdir(exist_ok=True);(OUT/"observations").mkdir(exist_ok=True)
    config={"gameDir":str(game),"dcSourceRoot":str(source),"outputDir":str(OUT/"observations")}
    (OUT/"fabric-lab.json").write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding="utf-8")
    spec={"status":"prepared, not installed or launched","minecraftVersion":meta["id"],"javaHome":str(a.java_home),
          "gameDir":str(game),"assetsDir":str(version.parent.parent/"assets"),"librariesDir":str(libraries),
          "requiredJvmArgument":"-Dmcdn.lab.manifest="+str(OUT/"fabric-lab.json"),
          "dcEnvironment":{"MCDN_LAB_ROOT":str(OUT)},"account":"Use the user's normal launcher/account; no account tokens are read or generated",
          "world":"Create a disposable single-player world under this gameDir; existing saves stay outside the lab",
          "control":"probe only; input takeover, carrier readiness and frame evidence stay disabled"}
    (OUT/"launch-spec.json").write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding="utf-8")
    files=[*sorted(dc.iterdir()),jar]
    report={"scope":"compiled against installed binaries; no game launch or runtime mixin verification",
            "package_check":package_check,
            "packages":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
            "sources":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in [ROOT/"src"] for f in sorted(folder.rglob("*")) if f.suffix in [".cs",".java",".json",".csproj"] and "bin" not in f.parts and "obj" not in f.parts},
            "java":run([a.java_home/"bin/java.exe","-version"]).strip()}
    (OUT/"build-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("LAB_PACKAGES_BUILD_PASS",jar);print("DC_PROBE_BUILD_PASS",dc);print("SPEC",OUT/"launch-spec.json")

if __name__=="__main__":main()
