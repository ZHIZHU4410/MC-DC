"""Bind actual GPU exports to this run's native ticks; visual judgment stays explicit."""
import argparse
import json
import math
import shutil
from pathlib import Path
from PIL import Image
from prepare_dc_scene import OUT, sha


def finite(value):
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('nonfinite native render metadata')
    if isinstance(value,dict):
        for child in value.values():finite(child)
    if isinstance(value,list):
        for child in value:finite(child)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--frames',type=Path,required=True);parser.add_argument('--observed',help='Explicit observation after actually viewing the exported image; omitted means visual acceptance pending');args=parser.parse_args()
    run=Path(json.loads((OUT/'observations/current-run.json').read_text())['directory'])
    motion=json.loads((run/'runtime-report.json').read_text());plan=json.loads((OUT/'scene.json').read_text())
    if motion['status']!='archived-dc-native-player-motion-pass':raise ValueError('real movement acceptance required')
    samples=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
    cleaned=[r for r in samples if r['kind']=='previous-displays-cleaned']
    if len(cleaned)!=1:raise ValueError('explicit previous-display cleanup evidence required')
    samples=[r for r in samples if r['kind']=='sample' and r['side']=='client']
    frames=[];hashes=set();last_tick=-1
    destination=run/'render';destination.mkdir(exist_ok=True)
    for path in sorted(args.frames.glob('frame-*.json'),key=lambda p:int(p.stem.split('-')[1])):
        meta=json.loads(path.read_text());finite(meta)
        name=meta['file']
        if Path(name).name!=name:raise ValueError('frame path')
        image=args.frames/name;digest=sha(image.read_bytes())
        if digest!=meta['sha256'] or meta['cameraType']!='THIRD_PERSON_BACK' or meta['eligibleForControl'] or meta['bridgeContextPaired']:raise ValueError('native frame scope/hash')
        if meta['nativePlayerTick']<=last_tick or not 195<meta['footY']<205:raise ValueError('native tick/scene coverage')
        last_tick=meta['nativePlayerTick']
        matching=[r for r in samples if r['nativeTick']==last_tick]
        if len(matching)!=1:raise ValueError('unique same-native-tick client sample required')
        sample=matching[0]
        # Native render pose is interpolated, while client tick samples are discrete.
        # The known walking speed bounds this difference; this is not a production frame-pose pairing ACK.
        if abs(meta['footX']-sample['x'])>.23 or abs(meta['footY']-sample['y'])>.43 or abs(meta['footZ']-sample['z'])>.01:raise ValueError('GPU foot differs from native trajectory')
        with Image.open(image) as native:
            if native.size!=(meta['width'],meta['height']):raise ValueError('native PNG dimensions')
        shutil.copyfile(path,destination/path.name);shutil.copyfile(image,destination/name)
        frames.append(dict(metadata='render/'+path.name,image='render/'+name,sha256=digest,nativeTick=last_tick,scriptPhase=sample['phase']))
        hashes.add(digest)
    if len(frames)<4 or len(hashes)<4:raise ValueError('bounded changing GPU frame coverage')
    report=dict(status='native-dc-scene-render-ticks-pass',scope='MC native GPU scene with archived DC solid geometry; no DC upload or production context pairing',
                sourceDigest=plan['sourceDigest'],sceneDigest=plan['fixtureSha256'],eventsSha256=sha((run/'events.jsonl').read_bytes()),
                removedPreviousDiagnosticDisplays=cleaned[0]['removed'],frames=frames,visualAcceptance=bool(args.observed),
                visualObservation=args.observed or 'pending: native ticks and hashes cannot establish visual acceptance')
    (run/'render-evidence.json').write_text(json.dumps(report,indent=2));print('DC_SCENE_GPU_TICKS_PASS',len(frames),'actual GPU frames')


if __name__=='__main__':main()
