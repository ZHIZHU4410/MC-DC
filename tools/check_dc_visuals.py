"""Independently check source-art proof and/or native visual/input evidence; no game control."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_conversion(path):
    visual = json.loads(path.read_text())
    pack = Path(visual['packPath']).read_bytes()
    if sha(pack) != visual['packSha256']:
        raise ValueError('private source pack changed')
    with ZipFile(io.BytesIO(pack)) as archive:
        if set(archive.namelist()) != set(visual['resources']):
            raise ValueError('unexpected pack resources')
        for name, digest in visual['resources'].items():
            data = archive.read(name)
            if sha(data) != digest:
                raise ValueError('resource digest differs')
            if name.endswith('.png'):
                image = Image.open(io.BytesIO(data)).convert('RGBA')
                if image.size != (24, 24) or image.getextrema()[3] != (255, 255):
                    raise ValueError('native opaque material footprint')
        state = json.loads(archive.read('assets/minecraft/blockstates/stone.json'))
        models = state['variants']['']
        if len(models) != 10:
            raise ValueError('source wall variant count')
        for model in models:
            source = 'assets/mcdn/models/'+model['model'].split(':')[1]+'.json'
            if json.loads(archive.read(source))['parent'] != 'minecraft:block/cube_bottom_top':
                raise ValueError('native full cube model must match exact collision volume')
    return dict(status='dc-source-material-conversion-pass', sourceTiles=len(visual['sourceTiles']),
                opaqueTiles=20, nativeFullCubeModels=10, packSha256=visual['packSha256'],
                realGpuVerified=False)


def check_runtime(path):
    from check_native_input_lab import check, journal
    native = check(path)
    meta = json.loads((path/'identity.json').read_text())
    visual_bytes = (path/'visual-source.json').read_bytes()
    visual = json.loads(visual_bytes)
    if not meta.get('dcVisuals') or meta['visualConfigSha256'] != sha(visual_bytes) or meta['visualPackSha256'] != visual['packSha256'] or meta['geometryDigest'] != visual['sceneDigest']:
        raise ValueError('native art/scene/run identity')
    events = journal(path/'events.jsonl')
    layers = [event for event in events if event['kind'] == 'dc-visual-layer-state']
    if len(layers) != 2 or not layers[0]['active'] or layers[-1]['active'] or not all(event['resourcesVerified'] and event['packSha256'] == visual['packSha256'] for event in layers):
        raise ValueError('visual native activation/resource source/release')
    if layers[-1]['extractedFrames'] < 20:
        raise ValueError('native rendering did not advance')
    experiment = json.loads((path/'keyboard-experiment.json').read_text())
    ids = {sample['consumer']['frameId'] for sample in experiment['samples'] if sample['native']['Stage'] == 'active'}
    frames = [frame for frame in journal(path/'producer.jsonl') if frame['frameId'] in ids]
    if len(frames) < 10 or any(frame.get('worldVisuals') != 'dc-prison-source-materials' for frame in frames):
        raise ValueError('foreground pixels not paired with DC visual mode')
    if not {'FIRST_PERSON', 'THIRD_PERSON_BACK'}.issubset({frame['cameraType'] for frame in frames}):
        raise ValueError('native camera modes missing from displayed source-art frames')
    return dict(status='dc-source-material-native-runtime-pass-visual-inspection-required',
                nativeInput=native, foregroundSourceFrames=len(frames), renderLayer=layers[-1],
                thirdPersonDcAvatarImplemented=False, enemiesAndWorldEditsSynchronized=False,
                productionModeGranted=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path)
    a = p.parse_args()
    report = check_runtime(a.archive) if a.archive else check_conversion(ROOT/'artifacts/dc-visuals/conversion-report.json')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
