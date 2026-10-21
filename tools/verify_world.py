"""Independent world-blob oracle + C# export -> Java assembly/mode gate. No game launch."""
import hashlib
import json
from pathlib import Path
import struct
import uuid
import zlib

import verify_control
import verify_protocol as baseline

ROOT = baseline.ROOT
BUILD = ROOT / "artifacts/world"
SESSION = uuid.UUID("00112233-4455-6677-8899-aabbccddeeff").bytes


def fixtures():
    root = BUILD / "vectors"
    root.mkdir(parents=True, exist_ok=True)
    boxes = [(-4, -1, -2, 8, 0, 2), (2.25, 0, -2, 2.5, 4, 2),
             (-4, 0, 1.25, 8, 4, 1.5), (-4, 0, -1.5, 8, 4, -1.25), (-4, 3.75, -2, 8, 4, 2)]
    body = b"".join(struct.pack("<Q6dII", i+1, *v, 1, 0) for i, v in enumerate(boxes))
    header = struct.pack("<4sHHII16sQQII32sQ", b"MCDW", 0, 1, 96, len(boxes), SESSION, 1, 1, 64, 0, hashlib.sha256(body).digest(), 0)
    good = header + body
    (root / "good-scene.world").write_bytes(good)
    next_revision = bytearray(good); struct.pack_into("<Q", next_revision, 40, 2)
    (root / "good-next.world").write_bytes(next_revision)
    high = bytearray(good); struct.pack_into("<QQ", high, 32, 2**64-1, 2**63+1)
    (root / "good-u64.world").write_bytes(high)
    # Mutations to shape semantics get a corrected hash, so rejection cannot rely on CRC alone.
    mutations = [("magic", 0, "I", 0), ("version", 6, "H", 2), ("header", 8, "I", 95),
                 ("count", 12, "I", 2**32-1), ("epoch", 32, "Q", 0), ("revision", 40, "Q", 0),
                 ("record-size", 48, "I", 63), ("reserved", 52, "I", 1), ("tail", 88, "Q", 1),
                 ("zero-id", 96, "Q", 0), ("duplicate-id", 160, "Q", 1),
                 ("nan", 104, "d", float("nan")), ("range", 104, "d", -1_000_001),
                 ("inverted", 104, "d", 99), ("zero-height", 112, "d", 0),
                 ("one-way-not-supported", 152, "I", 2), ("shape-reserved", 156, "I", 1)]
    for name, offset, fmt, value in mutations:
        b = bytearray(good); struct.pack_into("<"+fmt, b, offset, value)
        if offset >= 96: b[56:88] = hashlib.sha256(b[96:]).digest()
        (root / ("bad-"+name+".world")).write_bytes(b)
    b = bytearray(good); b[-1] ^= 1
    (root / "bad-hash.world").write_bytes(b)
    (root / "bad-truncated.world").write_bytes(good[:-1])
    (root / "bad-trailing.world").write_bytes(good+b"!")
    baseline.fixtures()
    frame = bytearray((baseline.VECTORS / "good-pose.frame").read_bytes())
    struct.pack_into("<QQQ", frame, 32, 1, 1, 1)
    struct.pack_into("<3d", frame, 112, 0.55, 0, 0)
    struct.pack_into("<QQ", frame, 216, 100, 1000)
    struct.pack_into("<Q", frame, 240, 1)
    (root / "ready.frame").write_bytes(frame)
    return root


def main():
    verify_control.main()  # rebuild and complete original regression suite once
    root = fixtures()
    dll = ROOT / "tests/dotnet/bin/Release/net10.0/Mcdn.Protocol.Bench.dll"
    checks = [baseline.run(["dotnet", dll, "world-vectors", root]),
              baseline.run(["java", "-cp", baseline.BUILD / "java", "dev.mcdn.protocol.WorldModeBench", root])]
    report = {"scope": "world codecs, C# exporter, Java assembly and mode gate; synthetic geometry/evidence, no installed mod",
              "checks": checks, "source_sha256": json.loads((baseline.BUILD / "report.json").read_text(encoding="utf-8"))["source_sha256"],
              "fixture_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())}}
    (BUILD / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(checks)); print("REPORT", BUILD / "report.json")


if __name__ == "__main__": main()
