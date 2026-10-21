"""Read actual native DC upload receipts. Visible presentation is a separate inspection step."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec=json.loads((LAB/"dc-launch-spec.json").read_text(encoding="utf-8"));process=json.loads((LAB/"dc-process.json").read_text(encoding="utf-8"))
    playlist_path=LAB/"dc-frame/playlist.json";playlist=json.loads(playlist_path.read_text(encoding="utf-8"))
    if not spec.get("include_frame_probe") or sha(playlist_path)!=spec["environment"]["MCDN_DC_FRAME_PLAYLIST_SHA256"]:raise ValueError("frame diagnostic launch identity")
    for name,digest in spec["package_files"].items():
        if sha(LAB/name)!=digest:raise ValueError("DC package changed")
    raw=(LAB/"dc-logs/log_latest.log").read_bytes()
    try:lines=raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:lines=raw.decode("gb18030").splitlines()
    markers=[line for line in lines if "MCDN" in line]
    for marker in ["MCDN_DC_LAB_GUARD_READY","MCDN_DC_FRAME_PROBE_INITIALIZED","MCDN_DC_ORIGINAL_ENTRY_RELEASED"]:
        if not any(marker in line for line in markers):print("DC_FRAME_PENDING",marker);return
    errors=[line for line in markers if "disabled:" in line or "cleanup:" in line]
    if errors:raise RuntimeError("DC native display failed: "+"\n".join(errors))
    receipts=[]
    for path in sorted((LAB/"dc-frame").glob("upload-*.json"),key=lambda p:int(p.stem.split('-')[-1])):
        if path.stat().st_mtime_ns<process["started_at_ns"]:continue
        item=json.loads(path.read_text(encoding="utf-8"));index=item["index"]
        if index<0 or index>=len(playlist["frames"]):raise ValueError("upload index")
        source=playlist["frames"][index]
        if item["kind"]!="dc-native-texture-upload-diagnostic" or not item["recordedReplay"] or item["eligibleForControl"]:raise ValueError("upload scope")
        if item["sourceRun"]!=playlist["sourceRun"] or any(item[k]!=source[k] for k in ["frameId","width","height","rawSha256","pngSha256"]):raise ValueError("native source/upload pairing")
        if item["gameThreadUploadTimestamp"]<=0:raise ValueError("native upload timestamp")
        receipts.append(item)
    if [item["index"] for item in receipts]!=list(range(len(receipts))):raise ValueError("upload receipt hole")
    report={"status":"native-upload-pass-display-pending" if len(receipts)>=2 else "waiting",
            "scope":"actual native DC Texture/Bitmap upload returns and sequential GPU-capture replay receipts; visible draw requires desktop inspection; no live/native-IPC/input/world-color protocol claim",
            "launch_spec_sha256":sha(LAB/"dc-launch-spec.json"),"playlist_sha256":sha(playlist_path),"process":process,"receipts":receipts,"markers":markers,
            "visible_display_verified":False}
    (LAB/"dc-frame/runtime-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("DC_NATIVE_TEXTURE_UPLOAD_PASS" if len(receipts)>=2 else "DC_FRAME_PENDING",len(receipts),"recorded frames; display inspection pending")


if __name__=="__main__":main()
