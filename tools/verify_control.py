"""Control slice: strict schemas, native-input inbox faults, and authenticated TCP peers."""
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import struct
import subprocess
import threading
import uuid

import verify_protocol as baseline

ROOT = baseline.ROOT
BUILD = ROOT / "artifacts/control"


def fixtures():
    root = BUILD / "vectors"
    root.mkdir(parents=True, exist_ok=True)
    manifest = []

    def save(name, kind, valid, body):
        filename = name + ".json"
        if isinstance(body, dict): body = json.dumps(body, separators=(",", ":")).encode("ascii")
        elif isinstance(body, str): body = body.encode("ascii")
        (root / filename).write_bytes(body)
        manifest.append({"file": filename, "kind": kind, "valid": valid})

    hello = {"schema": "control-1", "role": "mc", "nonce": "a" * 64,
             "layout": "mcdn-64-256-control-1", "build": "b" * 64,
             "pid": "123", "startTime": "456", "javaMajor": "25", "capabilities": "1"}
    save("hello", "hello", True, hello)
    save("hello-u64", "hello", True, {**hello, "pid": str(2**32-1), "startTime": str(2**64-1)})
    for key, value in [("schema", "control-2"), ("role", "dc"), ("nonce", "c"*64), ("build", "c"*64),
                       ("nonce", "F"*64), ("layout", "old"), ("capabilities", "3"), ("javaMajor", "21"),
                       ("pid", "0"), ("pid", str(2**32)), ("startTime", "0"), ("startTime", "01")]:
        save("hello-bad-" + key + "-" + str(len(manifest)), "hello", False, {**hello, key: value})
    for key in hello:
        save("hello-missing-" + key, "hello", False, {k: v for k, v in hello.items() if k != key})
    save("hello-extra", "hello", False, {**hello, "unsupported": "1"})
    compact = json.dumps(hello, separators=(",", ":"))
    save("hello-duplicate", "hello", False, compact[:-1] + ',"nonce":"' + "a"*64 + '"}')
    save("hello-escape", "hello", False, compact.replace('"nonce"', '"n\\u006fnce"'))
    save("hello-bom", "hello", False, b"\xef\xbb\xbf" + compact.encode())
    save("hello-utf8", "hello", False, compact.encode().replace(b"mc", b"\xc0\xaf"))
    inp = {"inputSeq": "1", "hostTick": "1", "eventSeq": "1", "held": "16", "pressed": "16", "released": "0"}
    save("input", "input", True, inp)
    save("input-u64", "input", True, {**inp, "inputSeq": str(2**64-1), "hostTick": str(2**63+1)})
    save("input-zero", "input", True, {"inputSeq": "1", "hostTick": "0", "eventSeq": "0", "held": "0", "pressed": "0", "released": "0"})
    for key, value in [("inputSeq", "01"), ("inputSeq", "-1"), ("inputSeq", "+1"), ("inputSeq", str(2**64)),
                       ("hostTick", "1.0"), ("hostTick", "NaN"), ("eventSeq", ""), ("held", "128"),
                       ("pressed", "1"), ("released", "16")]:
        save("input-bad-" + key + "-" + str(len(manifest)), "input", False, {**inp, key: value})
    text = json.dumps(inp, separators=(",", ":"))
    for name, body in [("number", text.replace('"16"', "16")), ("null", text.replace('"16"', "null")),
                       ("array", "[]"), ("trailing", text+"x"), ("trailing-comma", text[:-1]+",}"),
                       ("unterminated", text[:-1]), ("depth", '{"inputSeq":{"value":"1"}}'),
                       ("large", " "*16385), ("long-value", '{"inputSeq":"' + "1"*2049 + '"}')]:
        save("syntax-" + name, "input", False, body)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (root / "manifest.tsv").write_text("\n".join(("good" if x["valid"] else "bad") + "\t" + x["kind"] + "\t" + x["file"] for x in manifest), encoding="utf-8")
    return root, len(manifest)


def server(dll, env):
    process = subprocess.Popen(["dotnet", str(dll), "control-serve"], cwd=ROOT, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = queue.Queue()
    threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
    try: return process, int(ready.get(timeout=10).strip())
    except Exception:
        process.kill(); process.communicate(); raise


def main():
    # Rebuild all standalone sources and preserve the original wire/TCP regression checks.
    baseline.main()
    root, count = fixtures()
    dll = ROOT / "tests/dotnet/bin/Release/net10.0/Mcdn.Protocol.Bench.dll"
    java = ["java", "-cp", str(baseline.BUILD / "java"), "dev.mcdn.protocol.ControlBench"]
    checks = [baseline.run(["dotnet", dll, "control-vectors", root]),
              baseline.run([*java, "vectors", root]), baseline.run([*java, "selftest"])]
    env = {**os.environ, "MCDN_BENCH_SESSION": str(uuid.uuid4()), "MCDN_BENCH_NONCE": secrets.token_hex(32)}
    host, port = server(dll, env)
    try:
        guest = subprocess.run([*java, "connect", str(port)], cwd=ROOT, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=20)
        if guest.returncode: raise RuntimeError(guest.stdout + guest.stderr)
        stdout, stderr = host.communicate(timeout=10)
        if host.returncode: raise RuntimeError(stdout + stderr)
        checks += [stdout.strip(), guest.stdout.strip()]
    finally:
        if host.poll() is None: host.kill(); host.communicate()
    # Wrong nonce must result in EOF and no HELLO_ACK/input, not a partially authorized session.
    host, port = server(dll, env)
    try:
        bad = {"schema": "control-1", "role": "mc", "nonce": "0"*64, "layout": "mcdn-64-256-control-1",
               "build": "b"*64, "pid": "123", "startTime": "456", "javaMajor": "25", "capabilities": "1"}
        body = json.dumps(bad, separators=(",", ":")).encode()
        header = struct.pack("<4sHHHHI16sQQQQ", b"MCDN", 0, 1, 1, 0, len(body),
                             uuid.UUID(env["MCDN_BENCH_SESSION"]).bytes, 0, 0, 1, 0)
        with socket.create_connection(("127.0.0.1", port), timeout=5) as conn:
            conn.settimeout(5); conn.sendall(header + body)
            assert conn.recv(1) == b"", "unauthorized peer received data"
        stdout, stderr = host.communicate(timeout=10)
        assert host.returncode == 0 and stdout.strip() == "CONTROL_TCP_AUTH_REJECTED" and not stderr
        checks.append("CONTROL_TCP_AUTH_REJECT_PASS wrong nonce received no reply/input")
    finally:
        if host.poll() is None: host.kill(); host.communicate()
    report = {"scope": "synthetic control peers/native-input sink; no installed mod or native physics run",
              "vector_count": count, "checks": checks,
              "source_sha256": json.loads((baseline.BUILD / "report.json").read_text(encoding="utf-8"))["source_sha256"]}
    (BUILD / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(checks)); print("REPORT", BUILD / "report.json")


if __name__ == "__main__": main()
