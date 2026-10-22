"""Verify real wrong-map refusal and pre-save native block rollback after normal MC close."""
import argparse
import json
from pathlib import Path
import zipfile
import hashlib
from check_native_input_lab import sha, journal


def check(run):
    for name,digest in json.loads((run/'archive.json').read_text())['files'].items():
        p=(run/name).resolve()
        if not p.is_relative_to(run.resolve()) or sha(p)!=digest:raise ValueError('archive drift')
    meta=json.loads((run/'identity.json').read_text())
    if not meta['testWrongWorld'] or not meta['verifyDcSolids'] or any(v!=0 for v in meta['exitCodes'].values()):raise ValueError('negative identity/exit')
    for artifact,build in [('own.jar','mc-build.json'),('own.dll','dc-build.json')]:
        value=json.loads((run/build).read_text())
        if sha(run/artifact) not in ([value['sha256']] if artifact.endswith('jar') else value['packages'].values()):raise ValueError('actual native build')
    with zipfile.ZipFile(run/'sources.zip') as z:
        for name in ['mc-build.json','dc-build.json','guard-build.json','frame-build.json']:
            build=json.loads((run/name).read_text())
            for source,digest in {**build['sources'],**build.get('linked_sources',{})}.items():
                if hashlib.sha256(z.read(source.replace('\\','/'))).hexdigest()!=digest:raise ValueError('source drift')
    expected=json.loads((run/'source.json').read_text());actual=json.loads((run/'dc-current-source.json').read_text())
    if expected['MapUid']!=actual['MapUid']+1 or sha(run/'dc-current-source.mcdw')!=actual['digest']:raise ValueError('actual DC map mismatch proof')
    challenge=json.loads((run/'keyboard-experiment.json').read_text())
    if not challenge['success'] or not challenge['allInjectedKeysReleased'] or challenge['pid']!=meta['dcProcess']['pid']:raise ValueError('foreground challenge')
    if any(s['foreground_pid']!=challenge['pid'] for s in challenge['samples']) or (run/'native-host-input.jsonl').exists():raise ValueError('unexpected control entry')
    states=journal(run/'native-input-states.jsonl')
    if not states or any(v['Stage']!='ready' or v['Consumed'] or not v['InputRestored'] for v in states):raise ValueError('native ownership granted to wrong world')
    dc=(run/'dc-runtime.log').read_text(errors='replace')
    if 'MCDN_NATIVE_INPUT_LAB_ENTRY_REFUSED dc-world-identity' not in dc or 'MCDN_NATIVE_INPUT_LAB_ACTIVE' in dc:raise ValueError('real native DC refusal missing')
    events=journal(run/'events.jsonl');plan=json.loads((run/'scene.json').read_text())
    installed=[v for v in events if v['kind']=='native-blocks-installed'];stopping=[v for v in events if v['kind']=='shutdown-restore' and v['trigger'] in ['player-remove-before-save','server-stop']];cleared=[v for v in events if v['kind']=='native-blocks-restored']
    if len(installed)!=1 or len(stopping)!=1 or len(cleared)!=1 or stopping[0]['phase']!=-1 or installed[0]['blocks']!=plan['nativeBlockCount'] or cleared[0]['blocks']!=plan['nativeBlockCount'] or cleared[0]['remaining'] or installed[0]['collisionOverride']:raise ValueError('pre-save rollback')
    if not events.index(installed[0])<events.index(stopping[0])<events.index(cleared[0]):raise ValueError('shutdown ordering')
    origin=next(v for v in events if v['kind']=='origin');returned=next(v for v in events if v['kind']=='restored' and v['side']=='server-restored')
    if max(abs(returned[k]-origin[k]) for k in ['x','y','z'])>.01 or returned['gameMode']!=origin['gameMode']:raise ValueError('pre-save return pose/mode')
    mc=(run/'mc-runtime.log').read_text(errors='replace')
    if stopping[0]['trigger']=='server-stop' and not mc.index('MCDN_PHYSICS_SERVER_RESTORED')<mc.index('Saving players'):raise ValueError('server fallback ran after player save')
    return dict(status='actual-world-refusal-and-pre-save-rollback-pass',session=meta['session'],actualMapUid=actual['MapUid'],rejectedExpectedMapUid=expected['MapUid'],nativeInputs=0,heroOwnershipGranted=False,restoredNativeBlocks=cleared[0]['blocks'],restoreTrigger=stopping[0]['trigger'],serverPoseRestored=True,exitCodes=meta['exitCodes'],productionModeGranted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args();print(json.dumps(check(a.archive),indent=2))
