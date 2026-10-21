"""Check only our fresh load markers and bounded native PNG diagnostics; never reads launcher tokens."""
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import unquote,urlparse
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/frame-probe"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    install=json.loads((OUT/"install.json").read_text(encoding="utf-8"));target=Path(install["target"])
    if sha(target)!=install["installed_sha256"]:raise ValueError("installed frame addon differs")
    log=target.parent.parent/"logs/latest.log"
    if not log.is_file() or log.stat().st_mtime_ns<target.stat().st_mtime_ns:print("FRAME_PROBE_PENDING no new log after addon install");return
    content=log.read_bytes()
    try:lines=content.decode("utf-8").splitlines()
    except UnicodeDecodeError:lines=content.decode("gb18030").splitlines()
    markers=[line for line in lines if "MCDN_FRAME_" in line or "MCDN_NATIVE_WORLD_COLOR_" in line or "MCDN frame " in line]
    if any("disabled:" in line or "refused:" in line for line in markers):raise RuntimeError("frame probe error: "+"\n".join(markers[-8:]))
    init=next((line for line in markers if "MCDN_FRAME_PROBE_INITIALIZED" in line),"")
    match=re.search(r"source=(.+?) output=(.+?); maximum=12;",init)
    if match is None:print("FRAME_PROBE_PENDING initializer not seen");return
    path=unquote(urlparse(match[1]).path)
    if len(path)>2 and path[0]=='/' and path[2]==':':path=path[1:]
    if Path(path).resolve()!=target.resolve():raise ValueError("loaded addon source differs")
    directory=Path(match[2]).resolve();expected=ROOT/"artifacts/lab/observations/world-color"
    if directory.parent!=expected or not re.fullmatch(r"[a-f0-9-]{36}",directory.name):raise ValueError("unexpected native capture directory")
    if not any("MCDN_FRAME_HOOK_OBSERVED" in line for line in markers):print("FRAME_PROBE_PENDING render hook has not run");return
    frames=[]
    for meta_path in sorted(directory.glob("frame-*.json"),key=lambda p:int(p.stem.split('-')[-1])):
        meta=json.loads(meta_path.read_text(encoding="utf-8"));name=meta["file"]
        if not re.fullmatch(r"frame-[1-9][0-9]*\.png",name):raise ValueError("native PNG filename")
        image=directory/name
        if not image.is_file() or image.stat().st_mtime_ns<target.stat().st_mtime_ns:raise ValueError("old native frame")
        if sha(image)!=meta["sha256"] or meta["kind"]!="native-mc-world-color-probe":raise ValueError("native image identity")
        if meta["eligibleForControl"] or meta["playerLayer"] or meta["bridgeContextPaired"] or not meta["fullScene"]:raise ValueError("wrong capture scope")
        with Image.open(image) as im:
            im.load();width,height=im.size
            if (width,height)!=(meta["width"],meta["height"]) or min(width,height)<1 or max(width,height)>1024:raise ValueError("native dimensions")
            if meta.get("captureSchema")=="world-color-probe-2":
                scale=min(1,1024/max(meta["sourceWidth"],meta["sourceHeight"]))
                if meta["gpuDownscale"]!=1 or abs(width-meta["sourceWidth"]*scale)>1 or abs(height-meta["sourceHeight"]*scale)>1:raise ValueError("CPU fit mismatch")
            elif width*meta["downscale"]!=meta["sourceWidth"] or height*meta["downscale"]!=meta["sourceHeight"]:raise ValueError("downscale mismatch")
            extrema=im.convert("RGB").getextrema();nonuniform=any(high>low for low,high in extrema)
        for key in ["footX","footY","footZ","cameraX","cameraY","cameraZ","cameraYaw","cameraPitch","partialTick"]:
            if not math.isfinite(meta[key]):raise ValueError("nonfinite frozen pose")
        for key in ["viewRotationColumnMajor","projectionColumnMajor"]:
            if len(meta[key])!=16 or not all(math.isfinite(x) for x in meta[key]):raise ValueError("invalid frozen matrix")
        if int(meta["completedNanoTime"])<int(meta["requestedNanoTime"]):raise ValueError("callback clock ordering")
        frames.append({"frameId":meta["frameId"],"image":str(image),"metadata":str(meta_path),"sha256":meta["sha256"],"size":[width,height],"nonuniform":nonuniform,"nativeGameTime":meta["nativeGameTime"],"nativePlayerTick":meta["nativePlayerTick"]})
    if len(frames)>12:raise ValueError("capture exceeded bounded limit")
    passed=len(frames)>=2 and any(frame["nonuniform"] for frame in frames) and len({frame["nativePlayerTick"] for frame in frames})>1
    report={"status":"pass" if passed else "waiting","scope":"actual MC native main-target PNG capture and frozen local pose; no imported-DC visual, MCDF player layer, native IPC, final DC display or input handoff claim",
            "installed_sha256":install["installed_sha256"],"loaded_source_matches":True,"markers":markers,"log_sha256":hashlib.sha256(content).hexdigest(),"frames":frames}
    (OUT/"runtime-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("FRAME_PROBE_NATIVE_PASS" if passed else "FRAME_PROBE_PENDING",len(frames),"frames")
    if frames:print("LATEST_IMAGE",frames[-1]["image"])


if __name__=="__main__":main()
