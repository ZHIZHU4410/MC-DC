"""Prepare an isolated PCL version from the user's local installation; no account data or launch."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from verify_fabric_package import verify

ROOT=Path(__file__).resolve().parents[1]
NAME="MC-DC-Lab-26.3"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--mc-version-dir",type=Path,required=True);p.add_argument("--install",action="store_true");a=p.parse_args()
    source=a.mc_version_dir.resolve();info=json.loads((source/(source.name+".json")).read_text(encoding="utf-8-sig"))
    if info["id"]!="26.3-Fabric 0.20.0" or info.get("inheritsFrom"):raise ValueError("unexpected source instance")
    game_jar=source/(source.name+".jar")
    probe=ROOT/"artifacts/lab/packages/mcdn-lab-probe-0.5.0.jar";verify(probe)
    proof=json.loads((ROOT/"artifacts/fabric-transform/report.json").read_text(encoding="utf-8"))
    if sha(probe)!=proof["package_sha256"]:raise ValueError("probe differs from class-loading proof")
    target=source.parent/NAME
    if target.exists():raise ValueError("lab version already exists; refusing to overwrite")
    out=ROOT/"artifacts/lab/profile-stage";out.mkdir(parents=True,exist_ok=True)
    meta=copy.deepcopy(info);meta["id"]=NAME
    # PCL's per-version isolation keeps saves/options/mods under this new version.
    config={"gameDir":str(target),"dcSourceRoot":str(ROOT/"artifacts/lab/dc-probe"),"outputDir":str(ROOT/"artifacts/lab/observations")}
    argument="-Dmcdn.lab.manifest="+str(target/"mcdn-lab.json")
    if any(isinstance(s,str) and "mcdn.lab.manifest" in s for s in meta["arguments"]["jvm"]):raise ValueError("source already configured for lab")
    meta["arguments"]["jvm"].append(argument)
    files={NAME+".json":json.dumps(meta,ensure_ascii=False,indent=2),
           "mcdn-lab.json":json.dumps(config,ensure_ascii=False,indent=2),
           "MCDN_ISOLATED_LAB":"Private disposable MC-DC lab. Existing worlds were not copied.\n",
           "PCL/Setup.ini":"VersionArgumentIndieV2:True\nVersionVanillaName:26.3\nVersionVanilla:26.3.0\nVersionFabric:0.20.0\nInfo:MC-DC isolated collision lab\n",
           "options.txt":"pauseOnLostFocus:false\nrenderDistance:4\nsimulationDistance:4\nmaxFps:60\nfullscreen:false\nlang:zh_cn\n"}
    for name,content in files.items():
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding="utf-8")
    plan={"versionId":NAME,"gameDir":str(target),"sourceInstance":str(source),"source_game_jar_sha256":sha(game_jar),
          "probe_sha256":sha(probe),"jvmArgument":argument,"scope":"new independent version only; no existing worlds/mods/options/accounts copied or changed",
          "launcherEvidence":"PCL per-version VersionArgumentIndieV2=True matches source instance; runtime gameDir and save-root still checked by probe",
          "files":{name:sha(out/name) for name in files},"status":"prepared"}
    (ROOT/"artifacts/lab/mc-profile-plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    if a.install:
        # New directory only. Do not merge into or remove any existing tree.
        target.mkdir()
        for name in files:
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/name,dest)
        shutil.copyfile(game_jar,target/(NAME+".jar"))
        (target/"mods").mkdir();dest=target/"mods"/probe.name;shutil.copyfile(probe,dest)
        if sha(target/(NAME+".jar"))!=plan["source_game_jar_sha256"] or sha(dest)!=plan["probe_sha256"]:raise RuntimeError("installed copy hash mismatch")
        manifest={**plan,"status":"installed, not launched","installed_at":datetime.now(timezone.utc).isoformat(),
                  "target":str(dest),"installed_sha256":sha(dest),"previous":None,
                  "uninstall":"Remove only listed created files whose hashes still match; keep all subsequently created saves/options/logs for user review"}
        manifest["files"][NAME+".jar"]=sha(target/(NAME+".jar"));manifest["files"]["mods/"+probe.name]=sha(dest)
        (ROOT/"artifacts/lab/mc-profile-install.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        print("MC_LAB_PROFILE_INSTALLED",NAME)
    else:print("MC_LAB_PROFILE_PREPARED",NAME)
    print("PLAN",ROOT/"artifacts/lab/mc-profile-plan.json")


if __name__=="__main__":main()
