"""Install ONLY the built MCDN probe with a backup and content-hash manifest."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from verify_fabric_package import verify as verify_package

ROOT=Path(__file__).resolve().parents[1]
NAME="mcdn-lab-probe-0.5.0.jar"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument("--mc-version-dir",type=Path,required=True);a=p.parse_args()
    version=a.mc_version_dir.resolve();meta=version/(version.name+".json")
    info=json.loads(meta.read_text(encoding="utf-8-sig"))
    if info["id"]!="26.3-Fabric 0.20.0":raise ValueError("unexpected instance")
    source=ROOT/"artifacts/lab/packages"/NAME;target=version/"mods"/NAME
    if not source.is_file() or not target.parent.is_dir():raise ValueError("build or mods directory missing")
    verify_package(source)
    backup=ROOT/"artifacts/backups"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");backup.mkdir(parents=True)
    old=None
    if target.exists():
        old={"sha256":sha(target),"backup":str(backup/NAME)};(backup/NAME).write_bytes(target.read_bytes())
    target.write_bytes(source.read_bytes())
    record={"target":str(target),"installed_sha256":sha(target),"previous":old,
            "scope":"single own mod only; no launcher options, saves, loaders or other mods changed",
            "uninstall":"remove only target when its sha256 equals installed_sha256; restore backup if previous is present"}
    (backup/"install.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    (ROOT/"artifacts/lab/mc-install.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print("MC_PROBE_INSTALLED",target);print("SHA256",record["installed_sha256"]);print("MANIFEST",backup/"install.json")

if __name__=="__main__":main()
