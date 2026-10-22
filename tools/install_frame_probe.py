"""Install a new, separate own diagnostic JAR in the marked lab; leave every existing mod untouched."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import zipfile
from verify_fabric_package import verify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/frame-probe"
NAME="mcdn-frame-probe-0.1.0.jar"
BASE_SHA="f595c665f9e35764a0c70adb43d3cd470639e96678bb061498901d8e460f3336"
GAME_SHA="4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--mc-version-dir",type=Path,required=True);p.add_argument("--install",action="store_true");p.add_argument("--replace-owned",action="store_true");a=p.parse_args()
    game=a.mc_version_dir.resolve();record=json.loads((OUT/"build-report.json").read_text(encoding="utf-8"));source=OUT/NAME;target=game/"mods"/NAME
    if game.name!="MC-DC-Lab-26.3" or not (game/"MCDN_ISOLATED_LAB").is_file():raise ValueError("only marked private lab supported")
    meta=json.loads((game/(game.name+".json")).read_text(encoding="utf-8-sig"))
    if meta["id"]!=game.name or sha(game/(game.name+".jar"))!=GAME_SHA:raise ValueError("pinned game identity required")
    if sha(game/"mods/mcdn-lab-probe-0.5.0.jar")!=BASE_SHA:raise ValueError("known loaded base probe required")
    if not record.get("transform") or sha(source)!=record["sha256"] or record["game_sha256"]!=GAME_SHA:raise ValueError("matching successful transform required")
    for name,digest in {**record["sources"],**record.get("linked_sources",{})}.items():
        if sha(ROOT/name)!=digest:raise ValueError("frame source changed since transform")
    verify(source);manifest=json.loads((game/"mcdn-lab.json").read_text(encoding="utf-8"))
    if Path(manifest["gameDir"]).resolve()!=game or Path(manifest["outputDir"]).resolve()!=ROOT/"artifacts/lab/observations":raise ValueError("unexpected diagnostic manifest")
    previous=None
    if target.exists():
        if not a.replace_owned:raise ValueError("addon path already exists; use --replace-owned only for an own hash-matching addon after MC exit")
        previous=json.loads((OUT/"install.json").read_text(encoding="utf-8"))
        if Path(previous["target"]).resolve()!=target or sha(target)!=previous["installed_sha256"]:raise ValueError("existing addon is not the recorded owned file")
    elif a.replace_owned:raise ValueError("owned addon to replace missing")
    if not a.install:print("FRAME_INSTALL_READY new addon only; pinned game/base/transform/marked lab checked");return
    backup=ROOT/"artifacts/backups"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");backup.mkdir(parents=True)
    snapshots=[]
    with zipfile.ZipFile(backup/"mc-frame-lab-backup.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for path in [game/"mcdn-lab.json",game/"options.txt",*sorted((game/"saves").rglob('*'))]:
            if path.is_file():
                content=path.read_bytes();name=path.relative_to(game).as_posix();archive.writestr(name,content)
                snapshots.append({"file":name,"bytes":len(content),"sha256":hashlib.sha256(content).hexdigest()})
    if previous is None:
        with target.open("xb") as stream:stream.write(source.read_bytes())
    else:
        # The complete save backup above fails on a live session.lock, before any replacement.
        if sha(target)!=previous["installed_sha256"]:raise ValueError("owned addon changed during backup")
        (backup/NAME).write_bytes(target.read_bytes());(backup/"previous-install.json").write_text(json.dumps(previous,indent=2),encoding="utf-8")
        staging=target.with_name(NAME+".mcdn-new")
        with staging.open("xb") as stream:stream.write(source.read_bytes())
        staging.replace(target)
    if sha(target)!=record["sha256"]:raise ValueError("installed JAR differs")
    result={"target":str(target),"installed_sha256":sha(target),"installed_at":datetime.now(timezone.utc).isoformat(),
        "build_report_sha256":sha(OUT/"build-report.json"),"previous":None if previous is None else {"sha256":previous["installed_sha256"],"backup":str(backup/NAME)},"backup":str(backup/"mc-frame-lab-backup.zip"),
        "backup_sha256":sha(backup/"mc-frame-lab-backup.zip"),"snapshot_files":snapshots,
        "scope":"new addon only; base JAR, launcher, account, saves and game configuration not modified; next offline user launch required",
        "uninstall":"remove only target when its sha256 equals installed_sha256; do not replace saves from snapshot without user request"}
    (backup/"install.json").write_text(json.dumps(result,indent=2),encoding="utf-8");(OUT/"install.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("FRAME_PROBE_INSTALLED",target);print("SHA256",result["installed_sha256"]);print("BACKUP",backup/"mc-frame-lab-backup.zip")


if __name__=="__main__":main()
