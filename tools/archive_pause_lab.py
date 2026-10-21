"""Validate/freeze the opt-in DC pause prerequisite after normal exit; no production ownership claim."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from archive_combined_scene import exited
from prepare_dc_scene import ROOT

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--restored',type=Path,required=True);args=parser.parse_args()
    lab=ROOT/'artifacts/lab';current=json.loads((lab/'dc-frame/pause-lab/current.json').read_text());run=Path(current['directory']);process=json.loads((lab/'dc-process.json').read_text())
    if current['pid']!=process['pid']:raise ValueError('process identity')
    code=exited(process);rows=[json.loads(s) for s in (run/'events.jsonl').read_text().splitlines()]
    before=rows[0];held=[r for r in rows if r['kind']=='held'];after=rows[-1];challenge=json.loads((run/'keyboard-challenge.json').read_text())
    selective=before.get('selectiveHero',False)
    if before['kind']!='before' or before['paused'] or len(held)<30 or after['kind']!='restored' or after['paused']!=before['paused'] or after['reason']!='bounded-timeout':raise ValueError('native pause lifecycle')
    if not challenge['allReleased'] or challenge['pid']!=process['pid'] or challenge['keys']!=['W','Space']:raise ValueError('foreground input challenge')
    for row in held:
        if row['paused']==selective or not row['foreground'] or row['productionModeGranted'] or any(row[k]!=before[k] for k in ['heroUid','x','y','life']):raise ValueError('native Hero changed during pause')
        if selective and (not row['isFreeze'] or row['isAlwaysUpdated']):raise ValueError('native Hero eligibility flags')
    if selective and (after['isFreeze']!=before['isFreeze'] or after['isAlwaysUpdated']!=before['isAlwaysUpdated'] or after['otherEligibleCalls']<=0 or after['heroEligibilityCalls']<=len(held)):raise ValueError('native flag restore/other entity eligibility progression')
    build=json.loads((ROOT/'artifacts/dc-render-api/build-report.json').read_text());evidence=run/'evidence';evidence.mkdir(exist_ok=False)
    for src,name in [(lab/'dc-launch-spec.json','dc-launch-spec.json'),(lab/'dc-logs/log_latest.log','dc-runtime.log'),(ROOT/'artifacts/dc-render-api/build-report.json','build-report.json'),(lab/'dc-mods/McdnDcFrameProbe/Mcdn.DcFrameProbe.dll','own.dll'),(args.restored,'restored.png')]:shutil.copyfile(src,evidence/name)
    with zipfile.ZipFile(evidence/'sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name,digest in {**build['sources'],**build['linked_sources']}.items():
            if sha(ROOT/name)!=digest:raise ValueError('source drift')
            archive.write(ROOT/name,name.replace('\\','/'))
        for name in ['exercise_pause_lab.py','archive_pause_lab.py','configure_pause_lab.py']:archive.write(ROOT/'tools'/name,'tools/'+name)
    report=dict(status='native-hero-freeze-prerequisite-pass' if selective else 'native-game-pause-prerequisite-pass',scope='Standalone native Hero eligibility freeze, other entity eligibility continues; no MC ownership, damage bypass or production handoff' if selective else 'Standalone entire-Game pause; freezes DC world too, unsuitable as production Hero bypass; no MC ownership',nativeExitCode=code,heldFrames=len(held),heroUid=before['heroUid'],heroPosition=[before['x'],before['y']],life=before['life'],restoredPaused=after['paused'],keyboardChallenge=challenge,eventsSha256=sha(run/'events.jsonl'))
    (run/'runtime-report.json').write_text(json.dumps(report,indent=2));(run/'archive.json').write_text(json.dumps(dict(files={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file()}),indent=2));print('NATIVE_PAUSE_PREREQUISITE_ARCHIVED',run)

if __name__=='__main__':main()
