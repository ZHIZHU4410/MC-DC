"""Independently verify a frozen real foreground input archive, without installed games."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def journal(path):
    if path.stat().st_size > 16*1024*1024:
        raise ValueError('journal bounds')
    return [json.loads(line) for line in path.read_text().splitlines()]


def check(run):
    manifest = json.loads((run/'archive.json').read_text())
    for name, digest in manifest['files'].items():
        path = (run/name).resolve()
        if not path.is_relative_to(run.resolve()) or sha(path) != digest:
            raise ValueError('archive drift: '+name)
    meta = json.loads((run/'identity.json').read_text())
    if any(v != 0 for v in meta['exitCodes'].values()):
        raise ValueError('normal game exits required')
    with zipfile.ZipFile(run/'sources.zip') as sources:
        for name in ['mc-build.json', 'frame-build.json', 'dc-build.json', 'guard-build.json']:
            build = json.loads((run/name).read_text())
            for key, digest in {**build['sources'], **build.get('linked_sources', {})}.items():
                if hashlib.sha256(sources.read(key.replace('\\', '/'))).hexdigest() != digest:
                    raise ValueError('archived source pairing')
    mc = json.loads((run/'mc-build.json').read_text())
    dc = json.loads((run/'dc-build.json').read_text())
    if sha(run/'own.jar') != mc['sha256'] or sha(run/'own.dll') not in dc['packages'].values():
        raise ValueError('actual build pairing')
    if meta['mcBuild'] != sha(run/'own.jar') or meta['dcBuild'] != sha(run/'own.dll'):
        raise ValueError('handshake build identity')
    scene = json.loads((run/'scene.json').read_text())
    if sha(run/'scene.mcdw') != scene['fixtureSha256'] or mc['fixture_sha256'] != scene['fixtureSha256']:
        raise ValueError('geometry pairing')
    complete = json.loads((run/'complete.json').read_text())
    if complete['failed'] or not complete['serverRestored'] or complete['productionModeGranted'] or complete['source'] != 'dc-foreground-input-lab' or complete['leaseFault'] != 'release':
        raise ValueError('native completion/source')
    challenge = json.loads((run/'keyboard-experiment.json').read_text())
    if not challenge['success'] or not challenge['allInjectedKeysReleased'] or challenge['productionModeGranted'] or challenge['pid'] != meta['dcProcess']['pid']:
        raise ValueError('foreground keyboard experiment')
    host = journal(run/'native-host-input.jsonl')
    if len(host) < 50 or [v['InputSeq'] for v in host] != list(range(1, len(host)+1)):
        raise ValueError('real host input order/coverage')
    if not all(any(v['Held'] & key for v in host) for key in [1, 2, 8, 16]):
        raise ValueError('native walk/jump/depth/retreat keys')
    hero = host[0]['Hero']
    if meta.get('verifyDcSolids'):
        proof=json.loads((run/'source.json').read_text())
        if sha(run/'source.mcdw')!=proof['digest'] or proof['digest']!=scene['sourceDigest'] or any(not v['GeometryVerified'] or v['MapUid']!=proof['MapUid'] for v in host):
            raise ValueError('actual DC solid-region identity verification')
    for value in host:
        h = value['Hero']
        if any(h[key] != hero[key] for key in ['Uid', 'X', 'Y', 'Life']) or not h['Freeze'] or h['AlwaysUpdated'] or h['CanUpdate'] or h['GamePaused'] or value['productionModeGranted']:
            raise ValueError('Hero moved or whole world paused during takeover')
    states = journal(run/'native-input-states.jsonl')
    consumed=max(s['Consumed'] for s in states)
    if states[-1]['Stage'] != 'restored' or not states[-1]['InputRestored'] or not 50<=consumed<=len(host):
        raise ValueError('native input consumption/return')
    cancelled=host[consumed:]
    # An urgent RELEASE cancels queued inputs; receipt is not native consumption.
    # This challenge may only leave a neutral tail after all movement/view edges were applied.
    if any(v['Held'] or v['Pressed'] or v['Released'] or v.get('MouseX',0) or v.get('MouseY',0) or v.get('CameraCycle',False) or v.get('InventoryCycle',False) for v in cancelled):
        raise ValueError('unconsumed non-neutral challenge input')
    events = journal(run/'events.jsonl')
    if any(v['productionModeGranted'] or v['fixtureSha256'] != scene['fixtureSha256'] or v['inputSource'] != 'dc-foreground-input-lab' for v in events):
        raise ValueError('native event scope')
    if cancelled and max(v.get('consumedAck',0) for v in events)<len(host)+2:
        raise ValueError('cancelled tail/explicit RELEASE not acknowledged by native inbox')
    native_blocks=scene.get('nativeBlocks',False)
    if native_blocks:
        installed=[v for v in events if v['kind']=='native-blocks-installed']
        cleared=[v for v in events if v['kind']=='native-blocks-restored']
        if len(installed)!=1 or len(cleared)!=1 or installed[0]['blocks']!=scene['nativeBlockCount'] or installed[0]['collisionOverride'] or cleared[0]['blocks']!=scene['nativeBlockCount'] or cleared[0]['remaining']:
            raise ValueError('native block materialization/rollback')
    raw = (run/'scene.mcdw').read_bytes()
    boxes = [struct.unpack_from('<Q6dII', raw, offset)[1:7] for offset in range(96, len(raw), 64)]
    summaries = {}
    for side in ['client', 'server']:
        rows = [r for r in events if r['kind'] == 'sample' and r['side'] == side]
        if len(rows) < 60 or len({r['nativeTick'] for r in rows}) < 60:
            raise ValueError('native tick coverage')
        for r in rows:
            if any(not math.isfinite(r[k]) for k in ['x','y','z','vx','vy','vz','bodyMinX','bodyMaxX','bodyMinY','bodyMaxY','bodyMinZ','bodyMaxZ']):
                raise ValueError('native finite pose')
            if r['noPhysics'] or r['flying'] or r['health'] < 19.99 or r['originalBlockBelow'] != ('non-air' if native_blocks else 'air'):
                raise ValueError('native physics prerequisites')
            if native_blocks and (r['queries']!=0 or r['geometryImplementation']!='native-blocks'):
                raise ValueError('native block scene used diagnostic collision override')
            if any(b[0]<r['bodyMaxX']-1e-5 and b[3]>r['bodyMinX']+1e-5 and b[1]<r['bodyMaxY']-1e-5 and b[4]>r['bodyMinY']+1e-5 and b[2]<r['bodyMaxZ']-1e-5 and b[5]>r['bodyMinZ']+1e-5 for b in boxes):
                raise ValueError('DC geometry penetration')
        # ServerPlayer accepts movement packets and need not mirror the client's collision flag.
        # Both actual bodies must stop at the wall; the LocalPlayer additionally reports collision.
        wall = [r for r in rows if abs(r['bodyMaxX']-scene['wallX']) < .01]
        peak = max(r['y'] for r in rows)
        if len(wall) < 5 or not 201.1 < peak < 201.4 or max(r['x'] for r in rows)-min(r['x'] for r in rows) < 4 or max(r['z'] for r in rows)-min(r['z'] for r in rows) < .2:
            raise ValueError('native wall/jump/depth movement')
        if side == 'client' and sum(r['horizontalCollision'] for r in wall) < 5:
            raise ValueError('native local wall collision')
        summaries[side] = dict(samples=len(rows), wallContactSamples=len(wall), jumpPeakY=peak, collisionQueries=max(r['queries'] for r in rows))
    origin = next(r for r in events if r['kind'] == 'origin')
    restored = {r['side']: r for r in events if r['kind'] == 'restored'}
    if set(restored) != {'client-restored', 'server-restored'} or not restored['client-restored']['inputIdentityRestored'] or not restored['client-restored']['cameraRestored'] or restored['server-restored']['remainingFixtureDisplays'] or restored['server-restored']['gameMode'] != origin['gameMode']:
        raise ValueError('native restoration')
    for r in restored.values():
        if any(abs(r[k]-origin[k]) > .1 for k in ['x','y','z']) or not r['grounded']:
            raise ValueError('return pose')
    dc_log = (run/'dc-runtime.log').read_text(errors='replace')
    lines = [line for line in dc_log.splitlines() if 'MCDN_NATIVE_INPUT_LAB_HERO_RESTORED' in line]
    if len(lines) != 1 or 'nativereturnconfirmed=true' not in lines[0].lower():
        raise ValueError('DC confirmed return')
    returned = json.loads(lines[0].split('hero=',1)[1])
    if any(returned[k] != hero[k] for k in ['Uid','X','Y','Life']) or returned['Freeze'] or not returned['CanUpdate'] or returned['GamePaused']:
        raise ValueError('DC Hero return')
    producers = journal(run/'producer.jsonl')
    consumers = journal(run/'consumer.jsonl')
    by_id = {p['frameId']: p for p in producers}
    for value in consumers:
        source = by_id[value['frameId']]
        if any(value[k] != source[k] for k in ['session','streamEpoch','nativeTick','width','height','rawSha256','packetSha256','readyQpc']) or value['recordedReplay'] or value['eligibleForControl']:
            raise ValueError('native frame pairing')
        if not 0 < source['captureQpc'] <= source['readyQpc'] <= value['uploadedQpc']:
            raise ValueError('GPU/DC timing order')
        if value['session'] != meta['session'] or (value['uploadedQpc']-source['readyQpc'])/value['frequency'] > 1.5:
            raise ValueError('session/fresh upload')
    samples = challenge['samples']
    active = [s for s in samples if s['native']['Stage'] == 'active']
    if len(active) < 20 or any(s['foreground_pid'] != meta['dcProcess']['pid'] for s in samples) or len({s['consumer']['frameId'] for s in active}) < 5:
        raise ValueError('real foreground display progression')
    for s in samples:
        value = s['consumer']
        actual = next((v for v in consumers if v['frameId'] == value['frameId']), None)
        if actual != value:
            raise ValueError('foreground upload receipt mismatch')
    view_report = None
    if meta.get('viewControl'):
        views=[v for v in events if v['kind']=='view-consumed']
        if len(views)!=consumed or [v['inputSeq'] for v in views]!=list(range(1,consumed+1)):
            raise ValueError('native view consumption coverage')
        by_input={v['InputSeq']:v for v in host}
        for v in views:
            source=by_input[v['inputSeq']]
            if any(v[a]!=source[b] for a,b in [('mouseX','MouseX'),('mouseY','MouseY'),('cameraCycle','CameraCycle')]):
                raise ValueError('native view/input sequence pairing')
        if sum(v['cameraCycle'] for v in views)!=3:
            raise ValueError('F5 cycle edge delivery')
        cameras={v['camera'] for v in views}
        if cameras!={'FIRST_PERSON','THIRD_PERSON_BACK','THIRD_PERSON_FRONT'} or max(v['yaw'] for v in views)-min(v['yaw'] for v in views)<15 or max(v['pitch'] for v in views)-min(v['pitch'] for v in views)<5:
            raise ValueError('actual native camera/yaw/pitch progression')
        active_ids={s['consumer']['frameId'] for s in active}
        rendered=[v for v in producers if v['frameId'] in active_ids]
        if not {'FIRST_PERSON','THIRD_PERSON_BACK'}.issubset({v['cameraType'] for v in rendered}) or max(v['yaw'] for v in rendered)-min(v['yaw'] for v in rendered)<15:
            raise ValueError('DC foreground did not receive actual camera changes')
        view_report=dict(consumedViews=len(views),cameraTypes=sorted(cameras),f5Edges=3,yawRange=max(v['yaw'] for v in views)-min(v['yaw'] for v in views),pitchRange=max(v['pitch'] for v in views)-min(v['pitch'] for v in views))
    inventory_report=None
    if meta.get('inventoryControl'):
        if any(v['inventoryCycle']!=by_input[v['inputSeq']]['InventoryCycle'] for v in views):
            raise ValueError('native inventory/input sequence pairing')
        edges=[v for v in views if v['inventoryCycle']]
        if [v['screen'] for v in edges]!=['inventory','none','inventory']:
            raise ValueError('native E open/close/open delivery')
        blocked=[v for v in events if v['kind']=='sample' and v['side']=='client' and v.get('screen')=='inventory' and v['held']==17]
        if len(blocked)<8 or any(v['nativeForward'] or v['nativeJump'] or abs(v['nativeMoveX'])>1e-6 or abs(v['nativeMoveY'])>1e-6 for v in blocked):
            raise ValueError('GUI did not suppress real native forward/jump input')
        if any(max(v[k] for v in blocked)-min(v[k] for v in blocked)>.001 for k in ['x','y','z']):
            raise ValueError('native player moved during GUI input challenge')
        gui_frames=[v for v in producers if v['frameId'] in active_ids and v.get('screenType')=='inventory']
        if len(gui_frames)<2 or states[-1].get('Screen')!='none' or not (run/'input-inventory.png').is_file():
            raise ValueError('foreground native GUI frame delivery/recovery')
        inventory_report=dict(eEdges=3,blockedNativeSamples=len(blocked),foregroundGuiFrames=len(gui_frames),closedOnF7=True)
    return dict(status='native-dc-block-world-pass' if native_blocks else 'native-dc-foreground-view-pass' if view_report else 'native-dc-foreground-input-pass', session=meta['session'], inputsSent=len(host),inputsConsumed=consumed,cancelledNeutralTail=len(cancelled),heroUid=hero['Uid'], heroUnchanged=True, nativeRestored=True, dcRestored=True, producerFrames=len(producers), uploadedFrames=len(consumers), activeForegroundFrames=len({s['consumer']['frameId'] for s in active}), summaries=summaries, viewControl=view_report, inventoryControl=inventory_report, nativeBlocks=scene.get('nativeBlockCount',0), productionModeGranted=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('archive', type=Path)
    a = p.parse_args()
    print(json.dumps(check(a.archive), indent=2))


if __name__ == '__main__':
    main()
