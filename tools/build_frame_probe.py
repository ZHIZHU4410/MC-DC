"""Prepare/transform-link a separate bounded GPU diagnostic addon, never install or start the game."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile,ZIP_DEFLATED
from verify_fabric_package import verify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/frame-probe"
BASE_SHA="f595c665f9e35764a0c70adb43d3cd470639e96678bb061498901d8e460f3336"
NAME="mcdn-frame-probe-0.1.0.jar"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path,required=True);p.add_argument("--mc-version-dir",type=Path,required=True);p.add_argument("--transform",action="store_true");a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);version=a.mc_version_dir.resolve();game_jar=version/(version.name+".jar")
    meta=json.loads((version/(version.name+".json")).read_text(encoding="utf-8-sig"));cp=[game_jar];libs=version.parent.parent/"libraries"
    for lib in meta["libraries"]:
        parts=lib["name"].split(":");group,artifact,ver=parts[:3];suffix="-"+parts[3] if len(parts)>3 else ""
        path=libs/group.replace(".","/")/artifact/ver/(artifact+"-"+ver+suffix+".jar")
        if path.is_file():cp.append(path)
    def run(command):
        r=subprocess.run(list(map(str,command)),cwd=OUT,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout+r.stderr
    quote=lambda value:'"'+str(value).replace('\\','/')+'"'
    jar=OUT/NAME
    with tempfile.TemporaryDirectory(prefix="classes-",dir=OUT) as temporary:
        classes=Path(temporary);sources=sorted((ROOT/"src/frameprobe/java").rglob("*.java"))+[ROOT/"src/java/dev/mcdn/protocol/Frame.java",ROOT/"src/java/dev/mcdn/protocol/WorldColorFrame.java",ROOT/"src/ipc/java/dev/mcdn/ipc/NativeMailbox.java"]
        # The installed game/JOML/Gson jars carry optional classfile annotations absent from the
        # launcher classpath. Exclude only dependency classfile lint; retain source warnings as errors.
        args=OUT/"javac.args";args.write_text("\n".join(["-encoding","UTF-8","-proc:none","-Xlint:all,-classfile","-Werror","-cp",quote(";".join(map(str,cp))),"-d",quote(classes),*map(quote,sources)]),encoding="utf-8")
        run([a.java_home/"bin/javac.exe","-J-Duser.language=en","-J-Duser.country=US","@"+str(args)])
        with ZipFile(jar,"w",ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob("*.class")):archive.write(path,path.relative_to(classes).as_posix())
            for path in sorted((ROOT/"src/frameprobe/resources").iterdir()):archive.write(path,path.name)
    package_check=verify(jar);transform=None;size_check=None
    if a.transform:
        base=version/"mods/mcdn-lab-probe-0.5.0.jar"
        if sha(base)!=BASE_SHA:raise ValueError("expected already verified base geometry probe")
        game=OUT/"transform-game";(game/"mods").mkdir(parents=True,exist_ok=True)
        for path in [base,jar]:(game/"mods"/path.name).write_bytes(path.read_bytes())
        (game/"MCDN_ISOLATED_LAB").write_text("Transformer-only lab; no game is started\n",encoding="utf-8")
        # This manifest remains inside the project, separate from the live game's configuration.
        manifest=OUT/"transform-lab.json";manifest.write_text(json.dumps({"gameDir":str(game),"outputDir":str(OUT/"transform-observations")}),encoding="utf-8")
        classes=OUT/"bench";classes.mkdir(exist_ok=True);source=ROOT/"tests/frameprobe/dev/mcdn/tests/FrameTransformBench.java"
        run([a.java_home/"bin/javac.exe","-encoding","UTF-8","-proc:none","-cp",";".join(map(str,cp)),"-d",classes,source])
        run([a.java_home/"bin/javac.exe","-encoding","UTF-8","-proc:none","-cp",jar,"-d",classes,ROOT/"tests/frameprobe/dev/mcdn/tests/FrameSizeBench.java"])
        size_check=run([a.java_home/"bin/java.exe","-cp",str(classes)+";"+str(jar),"dev.mcdn.tests.FrameSizeBench"]).strip()
        output=run([a.java_home/"bin/java.exe","-Djava.awt.headless=true","-Dfabric.log.disableAnsi=true","-Dmcdn.lab.manifest="+str(manifest),"-cp",str(classes)+";"+";".join(map(str,cp)),"dev.mcdn.tests.FrameTransformBench",game])
        (OUT/"transform.log").write_text(output,encoding="utf-8")
        transform=next((line for line in output.splitlines() if line.startswith("FRAME_TRANSFORM_PASS")),None)
        if transform is None:raise RuntimeError("transform returned without pass marker")
    report={"scope":"addon compiled against actual MC26.3; optional real loader transform only, no actual GPU capture",
            "jar":str(jar),"sha256":sha(jar),"game_sha256":sha(game_jar),"base_probe_sha256":BASE_SHA,"linked_sources":{str(p.relative_to(ROOT)):sha(p) for p in sources if "src/frameprobe" not in p.as_posix()},
            "package_check":package_check,"transform":transform,"size_regression":size_check,"java_home":str(a.java_home),
            "sources":{str(path.relative_to(ROOT)):sha(path) for folder in [ROOT/"src/frameprobe",ROOT/"tests/frameprobe"] for path in sorted(folder.rglob('*')) if path.is_file()}}
    (OUT/"build-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("FRAME_PROBE_BUILD_PASS",jar);print("SHA256",report["sha256"])
    if transform:print(transform)
    if size_check:print(size_check)


if __name__=="__main__":main()
