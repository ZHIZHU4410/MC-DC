"""Publish explicitly synthetic collision data to an already-running isolated lab, never DC evidence."""
import hashlib
import json
import math
from pathlib import Path
import struct
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def main():
    load=json.loads((LAB/"mc-profile-load-report.json").read_text(encoding="utf-8"))
    if load["status"]!="pass":raise ValueError("isolated profile load not verified")
    install=json.loads((LAB/"mc-profile-install.json").read_text(encoding="utf-8"))
    game=Path(install["gameDir"])
    config=json.loads((game/"mcdn-lab.json").read_text(encoding="utf-8"))
    if Path(config["gameDir"]).resolve()!=game.resolve() or not (game/"MCDN_ISOLATED_LAB").is_file():raise ValueError("lab marker/config mismatch")
    sample=LAB/"observations/mc-probe.json"
    if time.time()-sample.stat().st_mtime>3:raise ValueError("native world observation is stale")
    before=json.loads(sample.read_text(encoding="utf-8"))
    if before["paused"] or before["kind"]!="isolated-native-world-probe" or not before["onGround"]:raise ValueError("need a live grounded lab player")
    x,y,z=(before["player"+axis] for axis in ["X","Y","Z"])
    if not all(math.isfinite(v) and abs(v)<999900 for v in [x,y,z]):raise ValueError("unsafe fixture anchor")
    # Ground remains at the currently observed feet height; the wall starts three blocks away.
    boxes=[(x-64,y-1,z-64,x+64,y,z+64),(x+3,y,z-3,x+3.25,y+3,z+3)]
    session=uuid.uuid4();body=b"".join(struct.pack("<Q6dII",i+1,*box,1,0) for i,box in enumerate(boxes))
    blob=struct.pack("<4sHHII16sQQII32sQ",b"MCDW",0,1,96,len(boxes),session.bytes,1,1,64,0,hashlib.sha256(body).digest(),0)+body
    digest=hashlib.sha256(blob).hexdigest();folder=Path(config["dcSourceRoot"])/session.hex;folder.mkdir()
    name="world-1-1.mcdw";(folder/name).write_bytes(blob)
    metadata={"kind":"synthetic-mc-runtime-smoke","session":str(session),"worldEpoch":"1","revision":"1","file":name,"digest":digest,
              "unsupportedCells":0,"eligibleForControl":False,"note":"Synthetic floor/wall from native player anchor; not a DC map export"}
    tmp=folder/"latest.json.tmp";tmp.write_text(json.dumps(metadata,indent=2),encoding="utf-8");tmp.replace(folder/"latest.json")
    evidence={"scope":"synthetic geometry published to actual offline MC lab; native application/query receipt still pending",
              "metadata":metadata,"boxes":boxes,"before":before,"published_at_ns":time.time_ns(),"fixture_dir":str(folder)}
    (LAB/"mc-smoke-publish.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    print("MC_SYNTHETIC_SMOKE_PUBLISHED",digest)


if __name__=="__main__":main()
