"""Check immutable evidence after temporary configuration/logs have been cleared or reused."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("session");a=p.parse_args();session=str(uuid.UUID(a.session))
    directory=ROOT/"artifacts/lab/live-color"/session
    archive=json.loads((directory/"archive-manifest.json").read_text())
    for name,digest in archive["files"].items():
        if Path(name).name!=name or sha(directory/name)!=digest:raise ValueError("archived evidence changed: "+name)
    report=json.loads((directory/"runtime-report.json").read_text());visible=json.loads((directory/"visible-report.json").read_text())
    if report["session"]!=session or visible["session"]!=session or visible["status"]!="live-native-world-color-visible-pass" or visible["runtime_report_sha256"]!=sha(directory/"runtime-report.json"):raise ValueError("visible/runtime identity")
    for original,digest in report["evidence_sha256"].items():
        path=Path(original)
        if path.name=="log_latest.log":path=directory/"dc-runtime.log"
        elif path.name=="latest.log":path=directory/"mc-runtime.log"
        else:path=directory/path.name
        if sha(path)!=digest:raise ValueError("runtime evidence snapshot differs: "+str(path))
    if sha(directory/"dc-launch-spec.json")!=report["dc_launch_spec_sha256"] or sha(directory/"session.json")!=report["manifest_sha256"]:raise ValueError("archived launch identity")
    if sha(directory/"mc-build-report.json")!=report["mc_build_sha256"] or sha(directory/"dc-build-report.json")!=report["dc_build_sha256"]:raise ValueError("archived build report identity")
    mc=json.loads((directory/"mc-build-report.json").read_text());dc=json.loads((directory/"dc-build-report.json").read_text());cfg=json.loads((directory/"session.json").read_text())
    if sha(directory/"mc-frame-probe.jar")!=mc["sha256"] or sha(directory/"mcdn_ipc.dll")!=cfg["dllSha256"]:raise ValueError("archived producer/native package")
    expected=next(digest for name,digest in dc["packages"].items() if name.endswith("Mcdn.DcFrameProbe.dll"))
    if sha(directory/"Mcdn.DcFrameProbe.dll")!=expected:raise ValueError("archived native display package")
    busy=json.loads((directory/"snapshot-busy-test.json").read_text())
    if busy["result"]!="pass" or not busy["snapshot_ids_unchanged"]:raise ValueError("busy snapshot test")
    for role in ["producer","consumer"]:
        if int(busy["after_while_locked"][role]["frameId"])<=int(busy["before"][role]["frameId"]):raise ValueError("native flow stopped under snapshot contention")
    print("LIVE_ARCHIVE_PASS",session,report["consumer_count"],"native uploads; visual/stop/contention evidence bound")


if __name__=="__main__":main()
