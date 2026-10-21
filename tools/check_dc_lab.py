"""Read-only evidence check for guarded DC export -> actual MC client/server collision layers."""
import hashlib
import json
import re
from pathlib import Path
import struct
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec=json.loads((LAB/"dc-launch-spec.json").read_text(encoding="utf-8"))
    log=LAB/"dc-logs/log_latest.log"
    if not log.exists():print("DC_LAB_PENDING no isolated DC startup log");return
    raw=log.read_bytes()
    try:lines=raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:lines=raw.decode("gb18030").splitlines()
    markers=[s for s in lines if "MCDN" in s]
    guarded=any("MCDN_DC_LAB_GUARD_READY" in s and spec["environment"]["DCCM_OverridePath_SAVE_ROOT"] in s for s in markers)
    if not guarded:
        print("DC_LAB_PENDING_OR_REFUSED native save/cloud guard has not reported ready")
        for s in markers[-5:]:print(s.encode("ascii",errors="backslashreplace").decode())
        return
    if not any("MCDN_DC_PROBE_ENTRY_READY" in s for s in markers) or not any("MCDN_DC_ORIGINAL_ENTRY_RELEASED" in s for s in markers):
        print("DC_LAB_GUARD_PASS pre-entry only; no full guarded game session");return
    sessions=[m.group(1) for s in markers if (m:=re.search(r'MCDN read-only probe "?([a-f0-9-]{36})"? ->',s))]
    if len(sessions)!=1:raise ValueError("current DC probe session marker missing or ambiguous")
    for name,digest in spec["package_files"].items():
        if sha(LAB/name)!=digest:raise ValueError("staged DC package changed after launch preparation")
    candidates=[]
    for directory in (LAB/"dc-probe").iterdir():
        meta=directory/"latest.json"
        if not meta.is_file():continue
        parsed=json.loads(meta.read_text(encoding="utf-8"))
        if parsed.get("kind")=="read-only-dc-probe" and parsed.get("session")==sessions[0]:candidates.append((meta,parsed))
    if not candidates:print("DC_LAB_GUARD_PASS export pending; enter a DC character scene");return
    meta,world=max(candidates,key=lambda pair:pair[0].stat().st_mtime_ns)
    file=world["file"]
    if file!=f"world-{world['worldEpoch']}-{world['revision']}.mcdw":raise ValueError("unexpected DC export filename")
    blob=(meta.parent/file).read_bytes()
    if len(blob)<96 or len(blob)>96+4096*64 or hashlib.sha256(blob).hexdigest()!=world["digest"]:raise ValueError("DC export size/digest mismatch")
    header=struct.unpack_from("<4sHHII16sQQII32sQ",blob)
    if (header[0:5]!=(b"MCDW",0,1,96,(len(blob)-96)//64) or (len(blob)-96)%64 or
        header[5]!=uuid.UUID(world["session"]).bytes or header[6]!=int(world["worldEpoch"]) or header[7]!=int(world["revision"]) or
        header[8:10]!=(64,0) or header[10]!=hashlib.sha256(blob[96:]).digest() or header[11]!=0 or world["eligibleForControl"] is not False):
        raise ValueError("DC export header/metadata mismatch")
    sample=LAB/"observations/mc-probe.json";native=json.loads(sample.read_text(encoding="utf-8"))
    matched=(time.time()-sample.stat().st_mtime<3 and native.get("digest")==native.get("serverDigest")==world["digest"] and
             native["clientQueryCount"]>0 and native["serverQueryCount"]>0)
    backup=Path(spec["original_backup"]);before=json.loads((backup/"manifest.json").read_text(encoding="utf-8"))
    original=Path(before["source"])
    changes=[name for name,digest in before["files"].items() if not (original/name).is_file() or sha(original/name)!=digest]
    extras=[]
    for directory in [original/"save",original/"coremod/config"]:
        extras += [str(f.relative_to(original)) for f in directory.rglob("*") if f.is_file() and f.relative_to(original).as_posix() not in before["files"]]
    report={"scope":"actual DC diagnostic solid subset -> actual offline MC client/integrated-server collision queries; no movement/input/frame/Hero claim",
            "status":"pass" if matched and not changes and not extras else "waiting-or-failed","guard_markers":markers,
            "dc_metadata":world,"dc_blob_sha256":world["digest"],"dc_shape_count":header[4],"native_observation":native,
            "original_save_config_changed":changes,"original_save_config_added":extras,"observed_at_ns":time.time_ns()}
    dest=LAB/"dc-mc-native-query-report.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("DC_MC_NATIVE_QUERY_PASS" if report["status"]=="pass" else "DC_MC_NATIVE_QUERY_PENDING_OR_FAILED")
    print("shapes",header[4],"unsupportedCells",world["unsupportedCells"],"original_changes",len(changes)+len(extras))
    print("REPORT",dest)


if __name__=="__main__":main()
