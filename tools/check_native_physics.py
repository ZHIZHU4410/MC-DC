"""Validate real client/server trajectories. Synthetic fixture, local script, no DC control claim."""
import hashlib
import argparse
import json
import math
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/physics'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path);args=parser.parse_args()
    directory=args.archive.resolve() if args.archive else Path(json.loads((OUT/'observations/current-run.json').read_text())['directory']).resolve()
    if not directory.is_relative_to((OUT/'observations').resolve()):raise ValueError('run path')
    current=json.loads((directory/'evidence/run.json').read_text()) if args.archive else json.loads((OUT/'observations/current-run.json').read_text())
    complete=json.loads((directory/'complete.json').read_text())
    if complete['failed'] or not complete['serverRestored'] or complete['productionModeGranted'] or complete['source']!='local-script' or complete['leaseFault']!='input-lease-expired':raise ValueError('test completion/lease/source')
    path=directory/'events.jsonl'
    if path.stat().st_size>4*1024*1024:raise ValueError('event bound')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    if len(rows)>2048 or any(r['productionModeGranted'] or r['fixtureSha256']!=current['fixtureSha256'] for r in rows):raise ValueError('event scope/fixture')
    if sum(r['kind']=='world-prepared' and r['difficulty']=='peaceful' for r in rows)!=1:raise ValueError('native peaceful fixture preparation')
    samples={side:[r for r in rows if r['kind']=='sample' and r['side']==side] for side in ['client','server']}
    def phase(side,lo,hi):
        found=[r for r in samples[side] if lo<=r['phase']<=hi]
        if not found:raise ValueError(f'missing {side} phase {lo}..{hi}')
        return found
    summaries={}
    for side,items in samples.items():
        if len(items)<150 or len({r['nativeTick'] for r in items})<120:raise ValueError('actual native tick coverage')
        for r in items:
            if any(not math.isfinite(r[k]) for k in ['x','y','z','vx','vy','vz','bodyMinX','bodyMaxX','bodyMinY','bodyMaxY']):raise ValueError('nonfinite native pose')
            if r['originalBlockBelow']!='air' or r['flying'] or r['noPhysics'] or r['health']<19.99:raise ValueError('native air/survival/health precondition')
        ground=phase(side,10,19)
        if not all(abs(r['y']-200)<.005 and r['grounded'] for r in ground):raise ValueError('native ground contact')
        wall=phase(side,56,69)
        if not all(abs(r['bodyMaxX']-2.25)<.01 and r['horizontalCollision'] or abs(r['bodyMaxX']-2.25)<.01 and r['grounded'] for r in wall):raise ValueError('fractional wall clamp')
        if any(r['bodyMaxX']>2.251 for r in items):raise ValueError('wall penetration')
        free=phase(side,71,109);low=phase(side,131,165);free_peak=max(r['y'] for r in free);low_peak=max(r['y'] for r in low)
        if not 201.1<free_peak<201.4:raise ValueError('native free jump peak '+str(free_peak))
        if not 200.5<low_peak<=200.701 or max(r['bodyMaxY'] for r in low)>202.501:raise ValueError('native ceiling '+str(low_peak))
        if not all(r['grounded'] and abs(r['y']-200)<.005 for r in phase(side,104,109)+phase(side,160,165)):raise ValueError('native jump landing')
        if max(r['queries'] for r in items)<=0:raise ValueError('actual collision callback not observed')
        summaries[side]={'samples':len(items),'wall_max_x':max(r['bodyMaxX'] for r in wall),'free_jump_peak_y':free_peak,'low_ceiling_peak_y':low_peak,'queries':max(r['queries'] for r in items)}
    client=phase('client',186,199)
    if not all(r['held']==0 and r['inputIdentityRestored'] and r['fault']=='input-lease-expired' for r in client) or max(r['consumedInput'] for r in samples['client'])!=170:raise ValueError('lease clear/input identity/consume')
    c=phase('client',190,199)[-1];s=phase('server',190,199)[-1]
    if max(abs(c[k]-s[k]) for k in ['x','y','z'])>.02:raise ValueError('settled native client/server disagreement')
    origin=next(r for r in rows if r['kind']=='origin');restored={r['side']:r for r in rows if r['kind']=='restored'}
    if not origin['grounded'] or origin['health']<19.99:raise ValueError('living grounded native return position required')
    if not restored['client-restored']['inputIdentityRestored'] or not restored['client-restored']['cameraRestored'] or restored['server-restored']['remainingFixtureDisplays']!=0 or restored['server-restored']['gameMode']!=origin['gameMode']:raise ValueError('native restoration')
    for r in restored.values():
        if max(abs(r[k]-origin[k]) for k in ['x','y','z'])>.1:raise ValueError('initial native position not restored')
    base=directory/'evidence' if args.archive else OUT
    build=json.loads((base/'build-report.json').read_text());install=json.loads((base/'install.json').read_text())
    jar=base/'own.jar' if args.archive else Path(install['target_jar'])
    if sha(jar)!=build['sha256'] or install['installed_sha256']!=build['sha256']:raise ValueError('installed native test build')
    if args.archive:
        with zipfile.ZipFile(base/'sources.zip') as source:
            for name,digest in build['sources'].items():
                if hashlib.sha256(source.read(name.replace('\\','/'))).hexdigest()!=digest:raise ValueError('archived transformed source')
        if sha(base/'fixture-world.mcdw')!=current['fixtureSha256']:raise ValueError('archived fixture')
        manifest=json.loads((directory/'archive.json').read_text())
        for name,digest in manifest['files'].items():
            entry=(directory/name).resolve()
            if not entry.is_relative_to(directory) or sha(entry)!=digest:raise ValueError('archive integrity '+name)
    else:
        for name,digest in build['sources'].items():
            if sha(ROOT/name)!=digest:raise ValueError('source changed after transform')
    report={'status':'native-player-physics-fixture-pass','scope':'real MC client/integrated server, synthetic MCDW solid fixture, scripted local input; no DC controls or production MODE/physics isolation claim','fixture_sha256':current['fixtureSha256'],'installed_sha256':install['installed_sha256'],'summaries':summaries,'consumed_inputs':170,'input_lease_and_original_identity_restored':True,'server_original_pose_mode_and_fixture_cleanup':True,'events_sha256':sha(path),'completion_sha256':sha(directory/'complete.json'),'run':str(directory)}
    if args.archive:
        if report!=json.loads((directory/'runtime-report.json').read_text()):raise ValueError('archived semantic report differs')
    else:
        (directory/'runtime-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(OUT/'runtime-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('NATIVE_PLAYER_PHYSICS_FIXTURE_PASS',summaries)


if __name__=='__main__':main()
