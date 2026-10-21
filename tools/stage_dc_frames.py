"""Convert the already verified native MC PNGs into a bounded recorded RGBA diagnostic playlist."""
import hashlib
import json
from pathlib import Path
import uuid
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/lab/dc-frame"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report_path=ROOT/"artifacts/frame-probe/runtime-report.json";report=json.loads(report_path.read_text(encoding="utf-8"))
    if report["status"]!="pass" or not report["loaded_source_matches"] or not 1<=len(report["frames"])<=12:raise ValueError("verified bounded native GPU capture required")
    entries=[];source=None;previous=0
    for frame in report["frames"]:
        image=Path(frame["image"]).resolve();metadata=Path(frame["metadata"]).resolve();parent=image.parent
        if parent.parent!=ROOT/"artifacts/lab/observations/world-color" or image.parent!=metadata.parent:raise ValueError("native source outside expected capture tree")
        run=str(uuid.UUID(parent.name))
        if source is not None and source!=run:raise ValueError("mixed native capture runs")
        source=run;meta=json.loads(metadata.read_text(encoding="utf-8"));frame_id=int(meta["frameId"])
        if frame_id<=previous or sha(image)!=meta["sha256"] or meta["sha256"]!=frame["sha256"]:raise ValueError("native source changed/order")
        previous=frame_id
        if meta["kind"]!="native-mc-world-color-probe" or meta["eligibleForControl"] or meta["bridgeContextPaired"]:raise ValueError("unexpected source claim")
        with Image.open(image) as im:
            w,h=im.size
            if min(w,h)<1 or max(w,h)>1024:raise ValueError("bounded pixels required")
            data=im.convert("RGBA").tobytes()
        raw_name=f"frame-{frame_id}.rgba";directory=OUT/run;directory.mkdir(parents=True,exist_ok=True);raw=directory/raw_name
        if raw.exists():
            if raw.read_bytes()!=data:raise ValueError("immutable recorded frame differs")
        else:
            with raw.open("xb") as stream:stream.write(data)
        entries.append({"frameId":str(frame_id),"width":w,"height":h,"rawFile":raw_name,"rawSha256":sha(raw),"pngSha256":meta["sha256"],"nativePlayerTick":meta["nativePlayerTick"]})
    playlist={"kind":"recorded-native-mc-world-color-diagnostic","eligibleForControl":False,"sourceRun":source,
        "sourceReportSha256":sha(report_path),"sourcePackageSha256":report["installed_sha256"],"scope":"recorded 12-frame GPU diagnostic replay, not a live world-color protocol or player layer","frames":entries}
    target=OUT/"playlist.json";temporary=OUT/"playlist.json.tmp";temporary.write_text(json.dumps(playlist,indent=2),encoding="utf-8");temporary.replace(target)
    print("DC_RECORDED_FRAMES_STAGED",len(entries),"SHA256",sha(target))


if __name__=="__main__":main()
