import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import uuid

from tools.verify_dc_layout import verify


class DcSpatialLayerVerification(unittest.TestCase):
    def test_binds_three_grids_to_exact_world_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            session = uuid.uuid4()
            x, y, w, h = 4, 7, 2, 2
            collision = [3, 0, 0, 0]
            deco = [1, 2, 4, 8]
            rooms = [10, 10, 11, 11]
            layout = b'MCDL' + struct.pack('<8i', 1, 42, 8, 12, x, y, w, h)
            layout += struct.pack('<12i', *(collision + deco + rooms))
            box = struct.pack('<Q6dII', (y << 32) + x + 1, 0, 0, 0, 1, 1, 1, 1, 0)
            world = struct.pack('<4sHHII16sQQII32sQ', b'MCDW', 0, 1, 96, 1,
                                session.bytes, 2, 3, 64, 0, hashlib.sha256(box).digest(), 0) + box
            (root/'layout-2-3.mcdl').write_bytes(layout)
            (root/'world-2-3.mcdw').write_bytes(world)
            metadata = dict(kind='read-only-dc-probe', eligibleForControl=False,
                            spatialLayersAvailable=True, session=str(session), worldEpoch='2', revision='3',
                            MapUid=42, MapWidth=8, MapHeight=12, X=x, Y=y, Width=w, Height=h,
                            layoutFile='layout-2-3.mcdl', layoutDigest=hashlib.sha256(layout).hexdigest(),
                            file='world-2-3.mcdw', digest=hashlib.sha256(world).hexdigest(),
                            histogram={'3': 1, '0': 3}, unsupportedCells=0)
            source = root/'latest.json'
            source.write_text(json.dumps(metadata))
            self.assertEqual(verify(source)['roomCellValues'], 2)
            metadata['revision'] = '4'
            source.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'revision filenames'):
                verify(source)
            metadata['revision'] = '3'
            metadata['layoutDigest'] = '0'*64
            source.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                verify(source)
            wrong_box = struct.pack('<Q6dII', (y << 32) + x + 2, 0, 0, 0, 1, 1, 1, 1, 0)
            wrong_world = struct.pack('<4sHHII16sQQII32sQ', b'MCDW', 0, 1, 96, 1,
                                      session.bytes, 2, 3, 64, 0,
                                      hashlib.sha256(wrong_box).digest(), 0) + wrong_box
            (root/'world-2-3.mcdw').write_bytes(wrong_world)
            metadata['layoutDigest'] = hashlib.sha256(layout).hexdigest()
            metadata['digest'] = hashlib.sha256(wrong_world).hexdigest()
            source.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'cell identity'):
                verify(source)


if __name__ == '__main__':
    unittest.main()
