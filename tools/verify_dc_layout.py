"""Validate a read-only DC collision/deco/room capture against its immutable MCDW revision."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import uuid


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local_blob(directory, name, suffix):
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(suffix):
        raise ValueError('immutable local blob name required')
    path = directory / name
    limit = 36 + 64*48*12 if suffix == '.mcdl' else 96 + 4096*64
    if path.stat().st_size > limit:
        raise ValueError('DC immutable blob exceeds format bound')
    return path.read_bytes()


def verify(metadata):
    meta = json.loads(metadata.read_text(encoding='utf-8'))
    if meta.get('kind') != 'read-only-dc-probe' or meta.get('eligibleForControl') is not False:
        raise ValueError('read-only DC source required')
    if meta.get('spatialLayersAvailable') is not True:
        raise ValueError('DC spatial layers were unavailable in this revision')
    layout = local_blob(metadata.parent, meta['layoutFile'], '.mcdl')
    world = local_blob(metadata.parent, meta['file'], '.mcdw')
    if meta['layoutFile'] != f"layout-{meta['worldEpoch']}-{meta['revision']}.mcdl" or \
            meta['file'] != f"world-{meta['worldEpoch']}-{meta['revision']}.mcdw":
        raise ValueError('DC immutable revision filenames')
    if digest(layout) != meta['layoutDigest'] or digest(world) != meta['digest']:
        raise ValueError('immutable blob digest mismatch')
    if len(layout) < 36 or layout[:4] != b'MCDL':
        raise ValueError('DC spatial layer header')
    version, uid, map_w, map_h, x, y, w, h = struct.unpack_from('<8i', layout, 4)
    if version != 1 or (uid, map_w, map_h, x, y, w, h) != tuple(meta[k] for k in
        ('MapUid', 'MapWidth', 'MapHeight', 'X', 'Y', 'Width', 'Height')):
        raise ValueError('DC spatial layer identity')
    if not (0 <= x < map_w and 0 <= y < map_h and 0 < w <= 64 and 0 < h <= 48 and
            x+w <= map_w and y+h <= map_h and len(layout) == 36 + w*h*12):
        raise ValueError('DC spatial layer bounds')
    grids = [struct.unpack_from(f'<{w*h}i', layout, 36 + i*w*h*4) for i in range(3)]
    collision, deco, room = grids
    histogram = Counter(collision)
    if {str(k): v for k, v in histogram.items()} != {str(k): v for k, v in meta['histogram'].items()}:
        raise ValueError('DC collision histogram changed')
    if sum(v for k, v in histogram.items() if k not in (0, 3, 35)) != meta['unsupportedCells']:
        raise ValueError('unsupported collision count changed')
    if len(world) < 96:
        raise ValueError('MCDW header')
    magic, major, minor, header_bytes, shape_count, session_bytes, epoch, revision, shape_bytes, flags, records_digest, reserved = \
        struct.unpack_from('<4sHHII16sQQII32sQ', world)
    if (magic, major, minor, header_bytes, shape_bytes, flags, reserved) != (b'MCDW', 0, 1, 96, 64, 0, 0) or \
            records_digest != hashlib.sha256(world[96:]).digest():
        raise ValueError('MCDW header')
    if len(world) != 96 + shape_count*64 or shape_count != histogram[3]+histogram[35]:
        raise ValueError('MCDW/collision cell count')
    expected = {((y+row) << 32) + x+col+1 for row in range(h) for col in range(w)
                if collision[row*w+col] in (3, 35)}
    actual = {struct.unpack_from('<Q', world, 96+i*64)[0] for i in range(shape_count)}
    if actual != expected or len(actual) != shape_count:
        raise ValueError('MCDW/collision cell identity')
    if session_bytes != uuid.UUID(meta['session']).bytes or \
            (epoch, revision) != (int(meta['worldEpoch']), int(meta['revision'])):
        raise ValueError('MCDW revision identity')
    return dict(kind='verified-dc-spatial-layers', session=meta['session'],
                worldEpoch=meta['worldEpoch'], revision=meta['revision'], mapUid=uid,
                mapSize=[map_w, map_h], window=[x, y, w, h], solidCells=shape_count,
                unsupportedCells=meta['unsupportedCells'], decoFlagValues=len(set(deco)),
                roomCellValues=len(set(room)), layoutDigest=meta['layoutDigest'],
                worldDigest=meta['digest'], scope='raw DC spatial labels; no sprite placement or door semantics inferred')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('metadata', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(args.metadata.resolve())
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('DC_SPATIAL_LAYERS_PASS', json.dumps(result))


if __name__ == '__main__':
    main()
