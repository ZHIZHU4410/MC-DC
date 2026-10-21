"""Independently check exact source geometry preservation, plus fail-closed provenance."""
import json
import struct
import tempfile
from pathlib import Path
from prepare_dc_scene import ROOT, OUT, prepare, sha


def main():
    plan=json.loads((OUT/'scene.json').read_text())
    source=(OUT/'source.mcdw').read_bytes();scene=(OUT/'scene.mcdw').read_bytes()
    meta=json.loads((OUT/'source.json').read_text())
    if sha(source)!=plan['sourceDigest'] or sha(scene)!=plan['fixtureSha256'] or sha((OUT/'source.json').read_bytes())!=plan['sourceMetadataSha256']:
        raise ValueError('provenance hashes')
    if source[:56]!=scene[:56] or source[88:96]!=scene[88:96]:
        raise ValueError('world identity/layout changed')
    count=struct.unpack_from('<I',source,12)[0]
    for i in range(count):
        a=struct.unpack_from('<Q6dII',source,96+i*64);b=struct.unpack_from('<Q6dII',scene,96+i*64)
        expected=(a[0],a[1],a[2]+plan['translation'][1],a[3],a[4],a[5]+plan['translation'][1],a[6],a[7],a[8])
        if expected!=b:raise ValueError('original cell geometry/ID altered')
    # Reproduce from the frozen original, and exercise bad-source refusals without altering evidence.
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        directory=Path(directory);metadata=directory/'latest.json';blob=directory/meta['file']
        metadata.write_bytes((OUT/'source.json').read_bytes());blob.write_bytes(source)
        if prepare(metadata)[2:]!=(scene,plan):raise ValueError('nonreproducible scene plan')
        bad_cases=[dict(meta,file='../outside.mcdw'),dict(meta,digest='0'*64)]
        for bad in bad_cases:
            metadata.write_text(json.dumps(bad))
            try:prepare(metadata)
            except ValueError:pass
            else:raise ValueError('bad provenance accepted')
        metadata.write_bytes((OUT/'source.json').read_bytes());blob.write_bytes(source[:-1])
        try:prepare(metadata)
        except ValueError:pass
        else:raise ValueError('truncated source accepted')
    build=json.loads((OUT/'build-report.json').read_text())
    if build['fixture_sha256']!=sha(scene) or sha(Path(build['jar']).read_bytes())!=build['sha256'] or build['geometrySource']!='archived-dc-solid-subset':raise ValueError('native build pairing')
    for name,digest in build['sources'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('native build source drift')
    report=dict(status='dc-scene-source-and-native-preflight-pass',shapes=count,
                sourceDigest=sha(source),sceneDigest=sha(scene),nativeBuild=build['sha256'],
                exactRigidTranslation=True,worldIdentityPreserved=True,negativeCases=3,
                realPlayerMotionVerified=False,productionModeGranted=False)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2))
    print('DC_SCENE_SOURCE_PASS',json.dumps(report))


if __name__=='__main__':main()
