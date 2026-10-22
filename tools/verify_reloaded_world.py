"""Compare actual native pre-save restoration with the next process's reloaded lab origin."""
import argparse
import json
from pathlib import Path
from check_native_input_lab import check,sha,journal
from check_world_guard_negative import check as negative_check


def main():
    p=argparse.ArgumentParser();p.add_argument('previous',type=Path);p.add_argument('reloaded',type=Path);a=p.parse_args()
    negative_check(a.previous);check(a.reloaded)
    old=json.loads((a.previous/'identity.json').read_text());new=json.loads((a.reloaded/'identity.json').read_text())
    if old['mcBuild']!=new['mcBuild'] or old['mcProcess']['profile']!=new['mcProcess']['profile'] or old['mcProcess']['pid']==new['mcProcess']['pid'] or old['mcProcess']['started_at_ns']>=new['mcProcess']['started_at_ns']:raise ValueError('native reload identity/order')
    returned=next(v for v in journal(a.previous/'events.jsonl') if v['kind']=='restored' and v['side']=='server-restored')
    origin=next(v for v in journal(a.reloaded/'events.jsonl') if v['kind']=='origin')
    if any(abs(origin[k]-returned[k])>.01 for k in ['x','y','z']) or origin['gameMode']!=returned['gameMode'] or not origin['grounded'] or origin['health']<19.99:raise ValueError('saved player origin not restored on actual reload')
    installed=next(v for v in journal(a.reloaded/'events.jsonl') if v['kind']=='native-blocks-installed')
    report=dict(status='native-world-reload-continuity-pass',previousSession=old['session'],reloadedSession=new['session'],previousArchiveSha256=sha(a.previous/'archive.json'),reloadedArchiveSha256=sha(a.reloaded/'archive.json'),origin={k:origin[k] for k in ['x','y','z','gameMode','grounded','health']},pristineAirTargetsReinstalled=installed['blocks'],scope='Actual next process reload at the restored native origin; all scene targets passed pristine-air checks before reinstall. No crash recovery or production world-edit claim.')
    out=Path(__file__).resolve().parents[1]/'artifacts/native-input'/('reload-'+new['session']+'.json');out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
