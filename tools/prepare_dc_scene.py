"""Freeze an actual DC export for native-player testing. No game/profile writes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/dc-scene'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(metadata):
    raw_meta = metadata.read_bytes()
    meta = json.loads(raw_meta)
    name = meta['file']
    if Path(name).name != name or not name.endswith('.mcdw'):
        raise ValueError('local immutable world filename required')
    data = (metadata.parent / name).read_bytes()
    if sha(data) != meta['digest'] or data[:4] != b'MCDW':
        raise ValueError('DC source digest')
    count = struct.unpack_from('<I', data, 12)[0]
    if len(data) != 96 + count * 64 or not 1 <= count <= 4096:
        raise ValueError('DC source layout')
    if (str(uuid.UUID(bytes=data[16:32])) != meta['session'] or
        struct.unpack_from('<QQ',data,32) != (int(meta['worldEpoch']),int(meta['revision'])) or
        struct.unpack_from('<HHI',data,4) != (0,1,96) or
        struct.unpack_from('<II',data,48) != (64,0) or data[88:96] != bytes(8)):
        raise ValueError('DC source identity/layout')
    if data[56:88] != hashlib.sha256(data[96:]).digest():
        raise ValueError('DC records digest')
    # Rigid translation only: preserve every ID, cell, gap, thickness and world identity.
    dy = 200.0 - float(meta['mcOriginY'])
    translated = bytearray(data)
    boxes = []
    for offset in range(96, len(data), 64):
        identity, *values, flags, reserved = struct.unpack_from('<Q6dII', data, offset)
        if flags != 1 or reserved or not all(math.isfinite(v) for v in values):
            raise ValueError('unsupported shape')
        values[1] += dy
        values[4] += dy
        struct.pack_into('<Q6dII', translated, offset, identity, *values, flags, reserved)
        boxes.append(values)
    translated[56:88] = hashlib.sha256(translated[96:]).digest()

    def intersects(x0, y0, z0, x1, y1, z1):
        return any(b[0] < x1 and b[3] > x0 and b[1] < y1 and b[4] > y0 and b[2] < z1 and b[5] > z0 for b in boxes)

    z = float(meta['mcOriginZ'])
    # Choose a real supported floor and an unmodified two-block-high wall to its right.
    candidates = []
    for b in boxes:
        x, y = (b[0] + b[3]) / 2, b[4]
        if y != 200 or not b[2] < z < b[5] or intersects(x-.3, y, z-.3, x+.3, y+3.1, z+.3):
            continue
        for wall in boxes:
            distance = wall[0] - x
            if 3 < distance < 7 and wall[1] <= y and wall[4] >= y+1 and wall[2] < z < wall[5]:
                # Check the full swept body and support; no artificial rails or floors.
                if intersects(x-.3, y, z-.3, wall[0], y+3.1, z+.3):
                    continue
                samples = [x + (wall[0]-.3-x)*i/80 for i in range(81)]
                if all(any(q[0] <= sx <= q[3] and q[4] == y and q[2] <= z-.3 and q[5] >= z+.3 for q in boxes) for sx in samples):
                    candidates.append((abs(distance-5), x, y, wall[0]))
    if not candidates:
        raise ValueError('no supported floor/wall corridor; do not fabricate one')
    _, x, y, wall_x = min(candidates)
    plan = dict(kind='archived-real-dc-solid-scene', sourceMetadataSha256=sha(raw_meta),
                sourceDigest=sha(data), fixtureSha256=sha(translated), sourceSession=meta['session'],
                sourceEpoch=meta['worldEpoch'], sourceRevision=meta['revision'], mapUid=meta['MapUid'],
                translation=[0, dy, 0], shapeCount=count, unsupportedCells=meta['unsupportedCells'],
                spawn=[x,y+.5,z], groundY=y, wallX=wall_x, productionModeGranted=False,
                inputSource='local-script', note='Archived DC solid subset, rigid translation; not live DC control or complete world semantics')
    return raw_meta, data, bytes(translated), plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--metadata', type=Path, required=True)
    args = parser.parse_args()
    raw_meta, source, scene, plan = prepare(args.metadata.resolve())
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in [('source.json',raw_meta),('source.mcdw',source),('scene.mcdw',scene)]:
        (OUT/name).write_bytes(data)
    (OUT/'scene.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print('DC_SCENE_PREPARED',json.dumps(plan))


if __name__ == '__main__':
    main()
