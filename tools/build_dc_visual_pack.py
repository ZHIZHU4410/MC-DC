"""Convert owned DC art to a private MC material pack. Never ship assets or edit a profile."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAME = 'mcdn-dc-prison.zip'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(assets, output, game_jar, scene):
    assets, output = assets.resolve(), output.resolve()
    if assets == ROOT or ROOT in assets.parents or output == ROOT or ROOT in output.parents:
        raise ValueError('extracted and converted game assets must stay outside the source project')
    plan = json.loads(scene.read_text(encoding='utf-8'))
    if not plan.get('nativeBlocks') or plan['productionModeGranted']:
        raise ValueError('explicit native DC scene required')
    if sha(scene.with_name('scene.mcdw').read_bytes()) != plan['fixtureSha256']:
        raise ValueError('scene digest changed')
    with ZipFile(game_jar) as game:
        version = json.loads(game.read('version.json'))
    if version['id'] != '26.3':
        raise ValueError('this converter targets the inspected native 26.3 model format')
    cdb = json.loads((assets/'data.cdb').read_text(encoding='utf-8'))
    biomes = [line for sheet in cdb['sheets'] if sheet['name'] == 'biome' for line in sheet['lines']
              if line.get('atlasName') == 'prison']
    # Explicit material theme; no claim that an archived collision export contains decoration data.
    biome = next(line for line in biomes if line['id'] == 'PrisonStart')
    entries, sources = {}, {}

    def put_json(name, value):
        entries[name] = json.dumps(value, separators=(',', ':')).encode()

    def read_image(name):
        path = assets/'expanded-prison'/name
        data = path.read_bytes()
        sources[name] = sha(data)
        image = Image.open(io.BytesIO(data)).convert('RGBA')
        if image.size != (24, 24):
            raise ValueError('expected an actual 24x24 DC tile: '+name)
        return image

    def put_image(name, value):
        # Keep original pixel dimensions; no generated art, filtering or palette substitution.
        buffer = io.BytesIO()
        value.save(buffer, format='PNG')
        entries['assets/mcdn/textures/block/'+name+'.png'] = buffer.getvalue()

    models = []
    for i in range(10):
        wall = read_image(f'backWall_{i}-=-0-=-.png')
        if wall.getextrema()[3] != (255, 255):
            raise ValueError('solid carrier requires opaque source tiles')
        floor = wall.copy()
        floor.alpha_composite(read_image(f'floorStamp_{i}-=-0-=-.png'))
        put_image(f'dc_prison_wall_{i}', wall)
        put_image(f'dc_prison_floor_{i}', floor)
        model = f'mcdn:block/dc_prison_{i}'
        put_json(f'assets/mcdn/models/block/dc_prison_{i}.json', {
            'parent': 'minecraft:block/cube_bottom_top',
            'textures': {'side': f'mcdn:block/dc_prison_wall_{i}',
                         'top': f'mcdn:block/dc_prison_floor_{i}',
                         'bottom': f'mcdn:block/dc_prison_wall_{i}'}})
        models.append({'model': model})
    # Stone remains the exact full-cube native collision carrier. Only this private pack changes its model.
    put_json('assets/minecraft/blockstates/stone.json', {'variants': {'': models}})
    major, minor = version['pack_version']['resource_major'], version['pack_version']['resource_minor']
    put_json('pack.mcmeta', {'pack': {'description': 'Private owned Dead Cells prison material conversion',
                                    'min_format': [major, minor], 'max_format': [major, minor]}})
    output.mkdir(parents=True, exist_ok=True)
    target = output/NAME
    with ZipFile(target, 'w', ZIP_DEFLATED) as pack:
        for name, data in sorted(entries.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            pack.writestr(info, data)
    report = {'kind': 'owned-dc-visual-scene-1', 'packFile': NAME, 'packPath': str(target),
              'packSha256': sha(target.read_bytes()), 'packId': 'file/'+NAME,
              'sceneDigest': plan['fixtureSha256'], 'atlasName': 'prison', 'biomeId': biome['id'],
              'fogColor': biome['fog'], 'ambientColor': biome['ambient'], 'sourceAtlasSha256': sha((assets/'atlas/prison.atlas').read_bytes()),
              'sourceCdbSha256': sha((assets/'data.cdb').read_bytes()),
              'sourceGameSha256': sha(game_jar.read_bytes()), 'sourceTiles': sources,
              'resources': {name: sha(data) for name, data in entries.items()},
              'scope': 'DC source material theme on proven solid geometry; no decoration/enemy/edit synchronization',
              'productionModeGranted': False}
    (output/'visual-scene.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--mc-jar', type=Path, required=True)
    p.add_argument('--scene', type=Path, default=ROOT/'artifacts/dc-scene/scene.json')
    a = p.parse_args()
    report = build(a.assets, a.output, a.mc_jar, a.scene)
    evidence = ROOT/'artifacts/dc-visuals'
    evidence.mkdir(exist_ok=True)
    (evidence/'conversion-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('DC_VISUAL_CONVERSION_PASS', report['packSha256'], 'tiles', len(report['sourceTiles']))


if __name__ == '__main__':
    main()
