"""Bind actual native GPU publications to actual DC uploads. Visual checks remain separate."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def journal(path):
    if path.stat().st_size>2*1024*1024:raise ValueError("bounded journal size")
    raw=path.read_bytes();lines=raw.splitlines();result=[]
    for index,line in enumerate(lines):
        try:result.append(json.loads(line))
        except json.JSONDecodeError:
            if index==len(lines)-1 and not raw.endswith(b'\n'):break
            raise
    if len(result)>1200:raise ValueError("bounded journal count")
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument("--require-stopped",action="store_true");a=p.parse_args()
    pointer=json.loads((LAB/"live-color/current-session.json").read_text());manifest=Path(pointer["manifest"]);directory=manifest.parent
    if not manifest.resolve().is_relative_to(LAB/"live-color") or sha(manifest)!=pointer["sha256"]:raise ValueError("live identity")
    cfg=json.loads(manifest.read_text());spec=json.loads((LAB/"dc-launch-spec.json").read_text());process=json.loads((LAB/"dc-process.json").read_text());mc_process=json.loads((LAB/"mc-live-process.json").read_text(encoding="utf-8-sig"))
    if spec["environment"].get("MCDN_DC_LIVE_COLOR_SHA256")!=pointer["sha256"]:raise ValueError("DC live manifest binding")
    for name,digest in spec["package_files"].items():
        if sha(LAB/name)!=digest:raise ValueError("DC package changed")
    physics=Path(cfg['gameDir']).name=='MC-DC-Physics-26.3'
    install=json.loads((ROOT/('artifacts/dc-scene/install.json' if physics else 'artifacts/frame-probe/install.json')).read_text());build=json.loads((ROOT/('artifacts/dc-scene/build-report.json' if physics else 'artifacts/frame-probe/build-report.json')).read_text())
    if sha(Path(install['target_jar'] if physics else install["target"]))!=install["installed_sha256"] or build["sha256"]!=install["installed_sha256"]:raise ValueError("MC installed build")
    for name,digest in {**build["sources"],**build.get("linked_sources",{})}.items():
        if sha(ROOT/name)!=digest:raise ValueError("MC source changed after transform")
    dc_build=json.loads((ROOT/"artifacts/dc-render-api/build-report.json").read_text())
    for name,digest in {**dc_build["sources"],**dc_build.get("linked_sources",{}),**dc_build["packages"]}.items():
        if sha(ROOT/name)!=digest:raise ValueError("DC source/package changed after build")
    producers=journal(directory/"producer.jsonl");consumers=journal(directory/"consumer.jsonl")
    if len(producers)<20 or len(consumers)<20:raise ValueError("need at least 20 real publications/uploads")
    def ordered(items):
        prior=0;epoch=0
        for f in items:
            fid=int(f["frameId"]);current=int(f["streamEpoch"])
            if f["session"]!=cfg["session"] or fid<=prior or current<epoch or f["eligibleForControl"] or f["width"] not in range(1,1025) or f["height"] not in range(1,1025):raise ValueError("frame identity/order/scope")
            prior=fid;epoch=current
    ordered(producers);ordered(consumers);by_id={f["frameId"]:f for f in producers};latencies=[]
    for item in consumers:
        source=by_id.get(item["frameId"])
        if source is None:raise ValueError("upload without authoritative producer receipt")
        if item["recordedReplay"] or item["kind"]!="dc-live-native-world-color-upload" or source["kind"]!="live-native-mc-world-color-published":raise ValueError("live scope")
        if any(item[k]!=source[k] for k in ["streamEpoch","nativeTick","width","height","rawSha256","packetSha256","readyQpc"]):raise ValueError("pixels/pose/header source pairing")
        if not 0<source["captureQpc"]<=source["readyQpc"]<=item["uploadedQpc"] or item["frequency"]<=0:raise ValueError("QPC ordering")
        if (item["uploadedQpc"]-item["readyQpc"])/item["frequency"]>1.5:raise ValueError("stale frame uploaded")
        latencies.append((item["uploadedQpc"]-source["captureQpc"])*1000/item["frequency"])
    if len({f['nativeTick'] for f in producers})<10 or len({f['rawSha256'] for f in consumers})<2:raise ValueError("native tick/pixel progression missing")
    with Image.open(directory/"first-native-frame.png") as image:
        if image.size!=(producers[0]["width"],producers[0]["height"]) or hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()!=producers[0]["rawSha256"]:raise ValueError("native PNG/RGBA byte order differs")
    dc_log=LAB/"dc-logs/log_latest.log";mc_log=Path(cfg["gameDir"])/"logs/latest.log"
    dc=dc_log.read_text(encoding="utf-8",errors="replace");mc=mc_log.read_text(encoding="utf-8",errors="replace")
    for marker in ["MCDN_DC_LAB_GUARD_READY","MCDN_DC_LIVE_COLOR_INITIALIZED","MCDN_DC_ORIGINAL_ENTRY_RELEASED"]:
        if marker not in dc:raise ValueError("DC runtime marker missing")
    if cfg["session"] not in mc or "MCDN_LIVE_COLOR_OPEN" not in mc or "disabled:" in dc or "live color disabled:" in mc:raise ValueError("runtime failure or wrong session")
    stopped="MCDN_LIVE_COLOR_PRODUCER_STOPPED" in mc and "MCDN_LIVE_COLOR_PREVIEW_CLEARED" in dc
    if a.require_stopped and not stopped:raise ValueError("producer stop / preview clear pending")
    samples_path=directory/"foreground-samples.json";samples=json.loads(samples_path.read_text())
    if len(samples)<3 or any(s["foreground_pid"]!=process["pid"] for s in samples):raise ValueError("DC foreground evidence missing")
    if int(samples[-1]["producer"]["frameId"])<=int(samples[0]["producer"]["frameId"]) or int(samples[-1]["consumer"]["frameId"])<=int(samples[0]["consumer"]["frameId"]):raise ValueError("background native producer/upload did not advance")
    report={"status":"live-native-upload-pass-visual-pending","scope":"real MC GPU -> typed Win32 mapping -> real DC native Texture; no guest input/Hero takeover or production world-color negotiation", "geometrySource":"archived-dc-solid-subset" if physics else "mc-native-world","presentation":cfg.get('presentation','thumbnail'),"session":cfg["session"],"manifest_sha256":sha(manifest),"dc_launch_spec_sha256":sha(LAB/"dc-launch-spec.json"),"mc_build_sha256":sha(ROOT/('artifacts/dc-scene/build-report.json' if physics else "artifacts/frame-probe/build-report.json")),"dc_build_sha256":sha(ROOT/"artifacts/dc-render-api/build-report.json"),"mc_process":mc_process,"dc_process":process,"producer_count":len(producers),"consumer_count":len(consumers),"distinct_uploaded_pixel_hashes":len({f['rawSha256'] for f in consumers}),"output_dimensions":[producers[0]['width'],producers[0]['height']],"capture_to_upload_return_ms":{"median":statistics.median(latencies),"max":max(latencies),"note":"software request-QPC to native-upload-return; not presentation/photon or input latency"},"background_samples":samples,"producer_stopped_preview_cleared_markers":stopped,"visible_display_verified":False,"evidence_sha256":{str(p):sha(p) for p in [manifest,directory/"producer.jsonl",directory/"consumer.jsonl",directory/"first-native-frame.png",samples_path,dc_log,mc_log]}}
    (directory/"runtime-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8");(ROOT/"artifacts/world-color/runtime-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("LIVE_NATIVE_UPLOAD_PASS",len(consumers),"uploads; background progression; visual inspection separate; stopped=",stopped)


if __name__=="__main__":main()
