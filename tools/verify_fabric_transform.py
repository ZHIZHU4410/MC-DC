"""Real Fabric/Knot transformation without calling Minecraft main or opening a game session."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from verify_fabric_package import verify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/fabric-transform"


def main():
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path,required=True);p.add_argument("--mc-version-dir",type=Path,required=True);p.add_argument("--lab-manifest",type=Path);a=p.parse_args()
    version=a.mc_version_dir.resolve();meta=json.loads((version/(version.name+".json")).read_text(encoding="utf-8-sig"))
    jar=ROOT/"artifacts/lab/packages/mcdn-lab-probe-0.5.0.jar";package_check=verify(jar)
    OUT.mkdir(parents=True,exist_ok=True);game=OUT/"game";(game/"mods").mkdir(parents=True,exist_ok=True)
    (game/"mods"/jar.name).write_bytes(jar.read_bytes())
    libraries=version.parent.parent/"libraries";cp=[version/(version.name+".jar")]
    for lib in meta["libraries"]:
        parts=lib["name"].split(":");group,artifact,ver=parts[:3];suffix="-"+parts[3] if len(parts)>3 else ""
        path=libraries/group.replace(".","/")/artifact/ver/(artifact+"-"+ver+suffix+".jar")
        if path.is_file():cp.append(path)
    classes=OUT/"classes";classes.mkdir(exist_ok=True)
    source=ROOT/"tests/fabric/dev/mcdn/tests/FabricTransformBench.java"
    classpath=";".join(map(str,cp))
    compiled=subprocess.run([str(a.java_home/"bin/javac.exe"),"-encoding","UTF-8","-proc:none","-cp",classpath,"-d",str(classes),str(source)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
    if compiled.returncode:raise RuntimeError(compiled.stdout+compiled.stderr)
    # Direct Unicode argv avoids the Java launcher @argfile's Windows codepage mismatch.
    properties=[] if a.lab_manifest is None else ["-Dmcdn.lab.manifest="+str(a.lab_manifest.resolve())]
    command=[str(a.java_home/"bin/java.exe"),"-Djava.awt.headless=true","-Dfabric.log.disableAnsi=true",*properties,"-cp",str(classes)+";"+classpath,"dev.mcdn.tests.FabricTransformBench",str(game)]
    run=subprocess.run(command,cwd=OUT,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
    output=run.stdout+run.stderr;(OUT/"transform.log").write_text(output,encoding="utf-8")
    if run.returncode:raise RuntimeError(output)
    check=next((s for s in output.splitlines() if s.startswith("FABRIC_TRANSFORM_PASS")),None)
    if check is None:raise RuntimeError("transform process returned without success marker")
    report={"scope":"real installed loader transforms/links classes only; no Minecraft main/constructor, game window, native tick or world",
            "checks":[package_check,check],"package_sha256":hashlib.sha256(jar.read_bytes()).hexdigest(),
            "lab_manifest_sha256":None if a.lab_manifest is None else hashlib.sha256(a.lab_manifest.read_bytes()).hexdigest(),
            "log_sha256":hashlib.sha256(output.encode()).hexdigest(),
            "test_source_sha256":hashlib.sha256(source.read_bytes()).hexdigest()}
    (OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(check);print("REPORT",OUT/"report.json")


if __name__=="__main__":main()
