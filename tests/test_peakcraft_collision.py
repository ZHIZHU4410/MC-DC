"""Topology and fail-closed checks for the PeakCraft v11 DC collision adapter."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from export_peakcraft_collision import BOX, encode, read_scene  # noqa: E402


def messages(data):
    at = 0
    while at < len(data):
        kind, n = struct.unpack_from('<II',data,at)
        payload = data[at+8:at+8+n]
        yield kind,payload
        at += (8+n+7)&~7
    if at != len(data):
        raise AssertionError('unaligned collision stream')


class PeakcraftCollisionTests(unittest.TestCase):
    def test_adjacent_blocks_across_region_boundary(self):
        stream, report = encode({(7,0,0),(8,0,0)},3)
        self.assertEqual((report['regions'],report['blocks'],report['exposedFaces'],report['triangles'],report['messages']),
                         (2,2,10,20,5))
        rows = list(messages(stream))
        self.assertEqual([kind for kind,_ in rows],[1,2,3,2,3])
        self.assertEqual(struct.unpack('<I',rows[0][1])[0],3)
        blocks = set()
        for kind,payload in rows[1:]:
            x0,y0,z0,x1,y1,z1,epoch,n = struct.unpack_from('<iiiiiiII',payload)
            self.assertEqual((x1-x0,y1-y0,z1-z0,epoch),(7,7,7,3))
            if kind == 2:
                self.assertEqual(len(payload),32+n*80)
                for pos in range(32,len(payload),80):
                    x,y,z,flags,*bits = struct.unpack_from('<iiiI8Q',payload,pos)
                    self.assertEqual((flags,bits),(0,[2**64-1]*8))
                    blocks.add((x,y,z))
            else:
                self.assertEqual(len(payload),32+n*40)
                self.assertEqual(n,10)
                for pos in range(32,len(payload),40):
                    *coords,flags = struct.unpack_from('<9fI',payload,pos)
                    self.assertEqual(flags,0)  # DC source cells are not yet editable.
                    self.assertFalse(all(v == 8 for v in coords[::3]))  # shared face was culled.
        self.assertEqual(blocks,{(7,0,0),(8,0,0)})

    def test_corrupt_source_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            records = BOX.pack(1,0,0,0,1,1,1,1,0)
            header = bytearray(96)
            struct.pack_into('<4sHHII',header,0,b'MCDW',0,1,96,1)
            header[56:88] = hashlib.sha256(records).digest()
            scene = root/'scene.mcdw'
            scene.write_bytes(header+records)
            plan = root/'scene.json'
            plan.write_text(json.dumps({'fixtureSha256':hashlib.sha256(scene.read_bytes()).hexdigest(),
                                        'nativeBlocks':True,'nativeBlockCount':1,'sourceEpoch':3,
                                        'productionModeGranted':False}))
            self.assertEqual(read_scene(scene,plan)[0],{(0,0,0)})
            data = bytearray(scene.read_bytes())
            data[-1] ^= 1
            scene.write_bytes(data)
            with self.assertRaises(ValueError):
                read_scene(scene,plan)


if __name__=='__main__':unittest.main()

