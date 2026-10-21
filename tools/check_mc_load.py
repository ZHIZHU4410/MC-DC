"""Read-only load smoke check. Retains only our three markers, never full launcher logs."""
import hashlib
import argparse
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="store_true", help="check the independent MC-DC lab profile")
    args = parser.parse_args()
    manifest_name = "mc-profile-install.json" if args.profile else "mc-install.json"
    manifest = json.loads((ROOT / "artifacts/lab" / manifest_name).read_text(encoding="utf-8"))
    target = Path(manifest["target"])
    log = target.parent.parent / "logs/latest.log"
    expected = manifest["installed_sha256"]
    installed = hashlib.sha256(target.read_bytes()).hexdigest()
    if installed != expected:
        raise RuntimeError("installed probe hash differs from install manifest")
    if not log.exists() or log.stat().st_mtime_ns < target.stat().st_mtime_ns:
        print("MC_LOAD_PENDING no new log since probe installation")
        return
    content = log.read_bytes()
    # Windows launcher logging can use the system GBK codepage for a raw file URL.
    # Never replace undecodable bytes: that would silently corrupt the source identity.
    encoding = "utf-8"
    try:
        lines = content.decode(encoding).splitlines()
    except UnicodeDecodeError:
        encoding = "gb18030"
        lines = content.decode(encoding).splitlines()
    markers = [line for line in lines if "MCDN_LOAD_CHECK" in line or "MCDN_CLIENT_TICK_OBSERVED" in line
               or "MCDN Fabric probe 0.5.0 initialized" in line]
    load = next((line for line in markers if "MCDN_LOAD_CHECK" in line), "")
    source = load.split(" source=", 1)[-1] if " source=" in load else ""
    path = unquote(urlparse(source).path)
    if len(path) > 2 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    source_matches = bool(path) and Path(path).resolve() == target.resolve()
    passed = ("collisionMixin=true tickMixin=true" in load and source_matches
              and any("MCDN_CLIENT_TICK_OBSERVED" in line for line in markers))
    report = {"scope": "MC client startup only; no native world/physics/input/frame validation; offline start is user declared",
              "status": "pass" if passed else "waiting-or-failed", "installed_sha256": installed,
              "loaded_source_matches_install_target": source_matches, "log_encoding": encoding, "markers": markers,
              "log_sha256": hashlib.sha256(content).hexdigest(), "log_mtime_ns": log.stat().st_mtime_ns}
    dest = ROOT / "artifacts/lab" / ("mc-profile-load-report.json" if args.profile else "mc-load-report.json")
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MC_LOAD_PASS" if passed else "MC_LOAD_WAITING_OR_FAILED")
    for line in markers:
        print(line.encode("ascii", errors="backslashreplace").decode("ascii"))
    print("REPORT", dest)


if __name__ == "__main__":
    main()
