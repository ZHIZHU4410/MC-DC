"""Observe actual DC revisions/epochs and paired MC receipts; never send input to either game."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def main():
    p=argparse.ArgumentParser();p.add_argument("--seconds",type=int,default=120);a=p.parse_args()
    if not 10<=a.seconds<=300:raise ValueError("recording duration must be bounded to 10..300 seconds")
    prior=json.loads((LAB/"dc-mc-native-query-report.json").read_text(encoding="utf-8"))
    if prior["status"]!="pass":raise ValueError("real DC->MC query baseline required")
    base=prior["dc_metadata"];meta=LAB/"dc-probe"/base["session"].replace("-","")/"latest.json"
    baseline=json.loads(meta.read_text(encoding="utf-8"));known={baseline["digest"]:baseline}
    backup=ROOT/"artifacts/backups"/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-dc-lifecycle")
    backup.mkdir(parents=True)
    with ZipFile(backup/"lab-save.zip","w",ZIP_DEFLATED) as archive:
        for file in sorted((LAB/"dc-game/save").rglob("*")):
            if file.is_file():archive.write(file,file.relative_to(LAB/"dc-game/save"))
    deadline=time.monotonic()+a.seconds;records=[];revision=None;epoch=None;last=None
    print("WORLD_LIFECYCLE_RECORDING baseline epoch="+baseline["worldEpoch"]+" revision="+baseline["revision"],flush=True)
    while time.monotonic()<deadline:
        try:
            source=json.loads(meta.read_text(encoding="utf-8"));native=json.loads((LAB/"observations/mc-probe.json").read_text(encoding="utf-8"))
            known[source["digest"]]=source
            key=(source["digest"],native.get("digest"),native["gameTicks"])
            if key!=last:
                last=key;sample={"observed_at_ns":time.time_ns(),"source":source,"native":native};records.append(sample)
                applied=known.get(native.get("digest"))
                paired=(applied is not None and native.get("digest")==native.get("serverDigest") and native["clientQueryCount"]>0 and native["serverQueryCount"]>0)
                if paired and revision is None and int(applied["worldEpoch"])==int(baseline["worldEpoch"]) and int(applied["revision"])>int(baseline["revision"]):
                    revision={**sample,"applied_source":applied};print("WORLD_REVISION_RUNTIME_PASS revision="+applied["revision"],flush=True)
                if paired and epoch is None and int(applied["worldEpoch"])>int(baseline["worldEpoch"]) and applied["MapUid"]!=baseline["MapUid"]:
                    epoch={**sample,"applied_source":applied};print("WORLD_EPOCH_RUNTIME_PASS epoch="+applied["worldEpoch"],flush=True)
                if revision is not None and epoch is not None:break
        except (OSError,ValueError,KeyError):pass
        time.sleep(0.2)
    report={"scope":"actual DC diagnostic geometry revisions/epochs applied and queried on actual MC client/server; no input/Hero/frame handoff claim",
            "status":"pass" if revision is not None and epoch is not None else "incomplete","baseline":baseline,
            "revision_evidence":revision,"epoch_evidence":epoch,"records":records,"lab_save_backup":str(backup)}
    dest=LAB/"world-lifecycle-runtime-report.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("WORLD_LIFECYCLE_RUNTIME_PASS" if report["status"]=="pass" else "WORLD_LIFECYCLE_INCOMPLETE",flush=True)
    print("REPORT",dest,flush=True)


if __name__=="__main__":main()
