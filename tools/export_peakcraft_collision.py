"""Convert a pinned DC MCDW solid scene into PeakCraft/SkyCraft v11 collision messages.

PeakCraft (aeironnsarmiento) and SkyCraft (chasmlol) are MIT licensed; this
independent adapter follows their public protocol at commit d07030ee527e.
The result is an offline input fixture, not a live host connection or proof of
DC decoration, enemies, doors, digging, or gameplay synchronization.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = 'd07030ee527ee2a2facc989f5acae8a317968c02'
PROTOCOL_VERSION = 11
COL_CLEAR, COL_REGION, COL_TRIS = 1, 2, 3
FULL = (1 << 64) - 1
BOX = struct.Struct('<Q6dII')
REGION = struct.Struct('<iiiiiiII')
BLOCK = struct.Struct('<iiiI8Q')
TRI = struct.Struct('<9fI')


def verify_upstream(path):
    result = subprocess.run(['git','-c',f'safe.directory={path}','rev-parse','HEAD'],
                            cwd=path,capture_output=True,text=True,check=True)
    if result.stdout.strip() != UPSTREAM_COMMIT:
        raise ValueError('PeakCraft source commit changed')
    proto = (path/'fabric/src/main/java/dev/skycraft/link/Proto.java').read_bytes()
    header = (path/'protocol/skycraft_protocol.h').read_bytes()
    if (b'VERSION = 11;' not in proto or b'COL_REGION = 2;' not in proto or
        b'COL_TRIS = 3;' not in proto or b'COL_BLOCK_BYTES = 80;' not in proto or
        b'COL_TRI_BYTES = 40;' not in proto or b'kVersion = 11;' not in header):
        raise ValueError('PeakCraft v11 collision layout differs')
    if b'MIT License' not in (path/'LICENSE').read_bytes():
        raise ValueError('PeakCraft source license differs')
    return {'protoSha256':digest(proto),'headerSha256':digest(header)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_scene(scene, plan):
    raw = scene.read_bytes()
    meta = json.loads(plan.read_text(encoding='utf-8'))
    if meta.get('fixtureSha256') != digest(raw) or not meta.get('nativeBlocks') or meta.get('productionModeGranted'):
        raise ValueError('pinned archived native-block DC scene required')
    if len(raw) < 96 or raw[:4] != b'MCDW' or struct.unpack_from('<HHI', raw, 4) != (0, 1, 96):
        raise ValueError('MCDW header')
    count = struct.unpack_from('<I', raw, 12)[0]
    if not 1 <= count <= 4096 or len(raw) != 96 + count * BOX.size or raw[56:88] != hashlib.sha256(raw[96:]).digest():
        raise ValueError('MCDW records/layout digest')
    cells = set()
    for offset in range(96, len(raw), BOX.size):
        _, x0, y0, z0, x1, y1, z1, flags, reserved = BOX.unpack_from(raw, offset)
        bounds = (x0, y0, z0, x1, y1, z1)
        if flags != 1 or reserved or any(not -2**20 < n < 2**20 or n != int(n) for n in bounds):
            raise ValueError('unsupported or noninteger DC volume')
        x0, y0, z0, x1, y1, z1 = map(int, bounds)
        if not (x0 < x1 and y0 < y1 and z0 < z1):
            raise ValueError('empty DC volume')
        if (x1-x0)*(y1-y0)*(z1-z0) > 4096:
            raise ValueError('unbounded DC volume')
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    if (x, y, z) in cells:
                        raise ValueError('overlapping DC solid cells')
                    cells.add((x, y, z))
    if len(cells) != meta['nativeBlockCount']:
        raise ValueError('DC block count drift')
    epoch = int(meta['sourceEpoch'])
    if not 0 < epoch < 2**32:
        raise ValueError('collision epoch')
    return cells, meta, epoch


def region_key(cell):
    return tuple(v // 8 for v in cell)


def face_quad(x, y, z, side):
    # Coordinate order is MC X/Y/Z; only the exposed full-cube surface is sent.
    if side == (1, 0, 0):
        return ((x+1,y,z),(x+1,y+1,z),(x+1,y+1,z+1),(x+1,y,z+1))
    if side == (-1, 0, 0):
        return ((x,y,z),(x,y,z+1),(x,y+1,z+1),(x,y+1,z))
    if side == (0, 1, 0):
        return ((x,y+1,z),(x,y+1,z+1),(x+1,y+1,z+1),(x+1,y+1,z))
    if side == (0, -1, 0):
        return ((x,y,z),(x+1,y,z),(x+1,y,z+1),(x,y,z+1))
    if side == (0, 0, 1):
        return ((x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1))
    if side == (0, 0, -1):
        return ((x,y,z),(x,y+1,z),(x+1,y+1,z),(x+1,y,z))
    raise ValueError('invalid face')


SIDES = ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))


def encode(cells, epoch):
    occupancy = defaultdict(list)
    triangles = defaultdict(list)
    face_count = 0
    for x, y, z in sorted(cells, key=lambda p:(p[1], p[2], p[0])):
        region = region_key((x,y,z))
        occupancy[region].append(BLOCK.pack(x,y,z,0,*([FULL]*8)))
        for dx,dy,dz in SIDES:
            if (x+dx,y+dy,z+dz) in cells:
                continue
            quad = face_quad(x,y,z,(dx,dy,dz))
            for a,b,c in ((quad[0],quad[1],quad[2]),(quad[0],quad[2],quad[3])):
                triangles[region].append(TRI.pack(*(a+b+c),0))
            face_count += 1
    messages = [(COL_CLEAR,struct.pack('<I',epoch))]
    for rx,ry,rz in sorted(occupancy):
        header = REGION.pack(rx*8,ry*8,rz*8,rx*8+7,ry*8+7,rz*8+7,epoch,len(occupancy[(rx,ry,rz)]))
        messages.append((COL_REGION,header+b''.join(occupancy[(rx,ry,rz)])))
        messages.append((COL_TRIS,header[:-4]+struct.pack('<I',len(triangles[(rx,ry,rz)]))+b''.join(triangles[(rx,ry,rz)])))
    stream = bytearray()
    for kind,payload in messages:
        stream.extend(struct.pack('<II',kind,len(payload)))
        stream.extend(payload)
        stream.extend(bytes((-len(stream)) % 8))
    return bytes(stream), {'regions':len(occupancy),'blocks':len(cells),'exposedFaces':face_count,
                           'triangles':face_count*2,'messages':len(messages),'epoch':epoch}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scene',type=Path,default=ROOT/'artifacts/dc-scene/scene.mcdw')
    parser.add_argument('--plan',type=Path,default=ROOT/'artifacts/dc-scene/scene.json')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/peakcraft/collision-v11.bin')
    parser.add_argument('--upstream',type=Path,required=True)
    args=parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT) and not args.output.resolve().is_relative_to((ROOT/'artifacts').resolve()):
        raise ValueError('private DC-derived geometry must stay in artifacts or outside the project')
    upstream=verify_upstream(args.upstream.resolve())
    cells, meta, epoch = read_scene(args.scene,args.plan)
    stream, report = encode(cells,epoch)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(stream)
    report.update(kind='peakcraft-v11-archived-dc-collision-fixture',upstreamCommit=UPSTREAM_COMMIT,
                  protocolVersion=PROTOCOL_VERSION,upstreamProtocol=upstream,sceneSha256=meta['fixtureSha256'],
                  streamSha256=digest(stream),streamBytes=len(stream),realMcConsumerVerified=False,
                  liveDcWorldVerified=False,productionModeGranted=False)
    args.output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PEAKCRAFT_COLLISION_FIXTURE_PASS',json.dumps(report))


if __name__=='__main__':main()

