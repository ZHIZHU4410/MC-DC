"""Recreate a deleted private lab from retained metadata and a hash-pinned official game JAR."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import urlopen
from verify_fabric_package import verify

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"
NAME="MC-DC-Lab-26.3"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--minecraft-dir",type=Path,required=True);p.add_argument("--install",action="store_true");a=p.parse_args()
    minecraft=a.minecraft_dir.resolve();target=minecraft/"versions"/NAME
    if not minecraft.is_dir() or target.exists():raise ValueError("Minecraft root missing or lab already exists; refusing to overwrite")
    template=LAB/"profile-stage";meta=json.loads((template/(NAME+".json")).read_text(encoding="utf-8"))
    if meta["id"]!=NAME or meta.get("inheritsFrom"):raise ValueError("unexpected retained profile")
    probe=LAB/"packages/mcdn-lab-probe-0.5.0.jar";verify(probe)
    proof=json.loads((ROOT/"artifacts/fabric-transform/report.json").read_text(encoding="utf-8"))
    if sha(probe)!=proof["package_sha256"]:raise ValueError("probe differs from verified package")
    client=meta["downloads"]["client"]
    expected=json.loads((ROOT/"artifacts/environment.json").read_text(encoding="utf-8"))["minecraft"]["game_jar"]["sha256"]
    url=urlparse(client["url"])
    if url.scheme!="https" or url.hostname!="piston-data.mojang.com" or url.path!="/v1/objects/"+client["sha1"]+"/client.jar":
        raise ValueError("game download must match the pinned official Mojang URL")
    argument="-Dmcdn.lab.manifest="+str(target/"mcdn-lab.json")
    meta["arguments"]["jvm"]=[s for s in meta["arguments"]["jvm"] if not (isinstance(s,str) and s.startswith("-Dmcdn.lab.manifest="))]+[argument]
    config={"gameDir":str(target),"dcSourceRoot":str(LAB/"dc-probe"),"outputDir":str(LAB/"observations")}
    stage=LAB/"profile-restored-stage";stage.mkdir(exist_ok=True)
    for name in ["MCDN_ISOLATED_LAB","PCL/Setup.ini","options.txt"]:
        dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(template/name,dest)
    (stage/(NAME+".json")).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    (stage/"mcdn-lab.json").write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding="utf-8")
    files=[p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()]
    plan={"versionId":NAME,"gameDir":str(target),"source":"retained project metadata + pinned official Mojang game download",
          "source_game_jar_sha256":expected,"probe_sha256":sha(probe),"jvmArgument":argument,
          "scope":"new private lab only; no existing saves/accounts/versions changed",
          "dependencies":"PCL will download missing libraries and assets from the retained normal version metadata on first launch",
          "files":{name:sha(stage/name) for name in files},"status":"prepared"}
    (LAB/"mc-profile-restore-plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    if not a.install:
        print("MC_LAB_RESTORE_PREPARED",NAME);return
    cache=LAB/"download-cache";cache.mkdir(exist_ok=True);game=cache/"minecraft-26.3-client.jar"
    def valid(path):
        if not path.is_file() or path.stat().st_size!=client["size"]:return False
        data=path.read_bytes()
        return hashlib.sha1(data).hexdigest()==client["sha1"] and hashlib.sha256(data).hexdigest()==expected
    if not valid(game):
        part=cache/"minecraft-26.3-client.jar.part"
        with urlopen(client["url"],timeout=30) as response,part.open("wb") as stream:
            if urlparse(response.geturl()).hostname!="piston-data.mojang.com":raise ValueError("unexpected game download redirect")
            received=0
            while block:=response.read(1024*1024):
                received+=len(block)
                if received>client["size"]:raise ValueError("game download exceeds pinned size")
                stream.write(block)
        if not valid(part):raise ValueError("official download hash/size mismatch")
        part.replace(game)
    # Only create the absent lab. Existing directories, including saves, are never merged or removed.
    target.mkdir(parents=True)
    for name in files:
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(stage/name,dest)
    shutil.copyfile(game,target/(NAME+".jar"));(target/"mods").mkdir();dest=target/"mods"/probe.name;shutil.copyfile(probe,dest)
    if not valid(target/(NAME+".jar")) or sha(dest)!=plan["probe_sha256"]:raise RuntimeError("installed copy hash mismatch")
    old=LAB/"mc-profile-install.json"
    if old.exists():
        backup=ROOT/"artifacts/backups"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup.mkdir(parents=True);shutil.copyfile(old,backup/old.name)
    manifest={**plan,"status":"restored, not launched","installed_at":datetime.now(timezone.utc).isoformat(),
              "target":str(dest),"installed_sha256":sha(dest),"previous":None,
              "uninstall":"Remove only listed files when hashes still match; preserve all later-created saves/options/logs"}
    manifest["files"][NAME+".jar"]=expected;manifest["files"]["mods/"+probe.name]=sha(dest)
    old.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("MC_LAB_PROFILE_RESTORED",NAME);print("GAME_JAR_SHA256",expected);print("MANIFEST",old)


if __name__=="__main__":main()
