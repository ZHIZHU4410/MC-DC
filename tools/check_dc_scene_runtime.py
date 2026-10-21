"""Accept only real MC client/server motion over the frozen DC collision subset."""
import json
import argparse
import math
import struct
import zipfile
from pathlib import Path
from prepare_dc_scene import ROOT, OUT, sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);args=parser.parse_args()
    current=json.loads((args.archive/'evidence/run.json' if args.archive else OUT/'observations/current-run.json').read_text())
    run=Path(current['directory']).resolve()
    if not run.is_relative_to((OUT/'observations').resolve()):raise ValueError('run path')
    if args.archive and run!=args.archive.resolve():raise ValueError('archive identity')
    base=run/'evidence' if args.archive else OUT
    plan=json.loads((base/'scene.json').read_text());build=json.loads((base/'build-report.json').read_text());install=json.loads((base/'install.json').read_text())
    scene=(base/'scene.mcdw').read_bytes()
    if current['fixtureSha256']!=plan['fixtureSha256'] or sha(scene)!=plan['fixtureSha256']:raise ValueError('scene pairing')
    if sha((base/'own.jar' if args.archive else Path(install['target_jar'])).read_bytes())!=build['sha256'] or install['installed_sha256']!=build['sha256']:raise ValueError('installed build')
    if args.archive:
        with zipfile.ZipFile(base/'sources.zip') as sources:
            for name,digest in build['sources'].items():
                if sha(sources.read(name.replace('\\','/')))!=digest:raise ValueError('archived source drift')
            if (base/'frame-build-report.json').is_file():
                frame=json.loads((base/'frame-build-report.json').read_text())
                if frame['sha256']!=build['linked_frame_jar_sha256']:raise ValueError('archived frame build pairing')
                for name,digest in {**frame['sources'],**frame['linked_sources']}.items():
                    if sha(sources.read(name.replace('\\','/')))!=digest:raise ValueError('archived frame source drift')
        manifest=json.loads((run/'archive.json').read_text())
        for name,digest in manifest['files'].items():
            path=(run/name).resolve()
            if not path.is_relative_to(run) or sha(path.read_bytes())!=digest:raise ValueError('archive file drift')
    else:
        for name,digest in build['sources'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError('source drift')
    complete=json.loads((run/'complete.json').read_text())
    if complete['failed'] or not complete['serverRestored'] or complete['productionModeGranted'] or complete['source']!='local-script' or complete['leaseFault']!='input-lease-expired':raise ValueError('completion/lease/source')
    event_file=run/'events.jsonl'
    if event_file.stat().st_size>4*1024*1024:raise ValueError('event bounds')
    rows=[json.loads(line) for line in event_file.read_text().splitlines()]
    if len(rows)>2048 or any(r['productionModeGranted'] or r['fixtureSha256']!=plan['fixtureSha256'] or r['geometrySource']!='archived-dc-solid-subset' or r['dcSourceDigest']!=plan['sourceDigest'] for r in rows):raise ValueError('event provenance')
    boxes=[struct.unpack_from('<Q6dII',scene,o)[1:7] for o in range(96,len(scene),64)]
    summaries={}
    samples={side:[r for r in rows if r['kind']=='sample' and r['side']==side] for side in ['client','server']}
    for side,items in samples.items():
        if len(items)<150 or len({r['nativeTick'] for r in items})<120:raise ValueError('native tick coverage')
        for r in items:
            if any(not math.isfinite(r[k]) for k in ['x','y','z','vx','vy','vz','bodyMinX','bodyMaxX','bodyMinY','bodyMaxY','bodyMinZ','bodyMaxZ']):raise ValueError('pose finite')
            if r['flying'] or r['noPhysics'] or r['health']<19.99 or r['originalBlockBelow']!='air':raise ValueError('native physics preconditions')
            if any(b[0]<r['bodyMaxX']-1e-5 and b[3]>r['bodyMinX']+1e-5 and b[1]<r['bodyMaxY']-1e-5 and b[4]>r['bodyMinY']+1e-5 and b[2]<r['bodyMaxZ']-1e-5 and b[5]>r['bodyMinZ']+1e-5 for b in boxes):raise ValueError('penetrated actual DC geometry')
        def phases(lo,hi):
            found=[r for r in items if lo<=r['phase']<=hi]
            if not found:raise ValueError('phase coverage')
            return found
        wall=phases(77,89)
        if not all(abs(r['bodyMaxX']-plan['wallX'])<.01 for r in wall):raise ValueError('actual DC wall not reached')
        peak=max(r['y'] for r in phases(91,119))
        if not 201.1<peak<201.4 or not all(abs(r['y']-200)<.005 and r['grounded'] for r in phases(110,119)+phases(190,199)):raise ValueError('native jump/landing')
        if max(r['x'] for r in items)-min(r['x'] for r in items)<4:raise ValueError('actual movement')
        if max(r['queries'] for r in items)<=0:raise ValueError('native collision queries')
        summaries[side]=dict(samples=len(items),wallMaxX=wall[-1]['bodyMaxX'],jumpPeakY=peak,queries=max(r['queries'] for r in items))
    client=samples['client']
    if max(r['consumedInput'] for r in client)!=170 or not all(r['held']==0 and r['inputIdentityRestored'] and r['fault']=='input-lease-expired' for r in client if r['phase']>=190):raise ValueError('native input consumption/lease/identity')
    c=client[-1];s=samples['server'][-1]
    if max(abs(c[k]-s[k]) for k in ['x','y','z'])>.02:raise ValueError('settled server disagreement')
    origin=next(r for r in rows if r['kind']=='origin');restored={r['side']:r for r in rows if r['kind']=='restored'}
    if not origin['grounded'] or set(restored)!= {'client-restored','server-restored'}:raise ValueError('origin/restoration evidence')
    if not restored['client-restored']['inputIdentityRestored'] or not restored['client-restored']['cameraRestored'] or restored['server-restored']['remainingFixtureDisplays']!=0 or restored['server-restored']['gameMode']!=origin['gameMode']:raise ValueError('native restoration')
    for r in restored.values():
        if max(abs(r[k]-origin[k]) for k in ['x','y','z'])>.1 or not r['grounded'] or r['health']<19.99:raise ValueError('restored native pose')
    report=dict(status='archived-dc-native-player-motion-pass',scope='Archived real DC solid subset; native MC client/server and local scripted input. No live DC controls, Hero takeover or production MODE.',run=str(run),sceneDigest=sha(scene),sourceDigest=plan['sourceDigest'],summaries=summaries,consumedInputs=170,restored=True,eventsSha256=sha(event_file.read_bytes()))
    if args.archive:
        if report!=json.loads((run/'runtime-report.json').read_text()):raise ValueError('archived runtime report differs')
    else:
        (run/'runtime-report.json').write_text(json.dumps(report,indent=2));(OUT/'runtime-report.json').write_text(json.dumps(report,indent=2))
    print('DC_SCENE_NATIVE_MOTION_PASS',json.dumps(summaries))


if __name__=='__main__':main()
