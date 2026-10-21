"""Verify combined immutable evidence without current game/config state."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from PIL import Image
from prepare_dc_scene import ROOT

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('session');args=parser.parse_args()
    import uuid
    session=str(uuid.UUID(args.session));directory=ROOT/'artifacts/lab/live-color'/session
    archive=json.loads((directory/'archive-combined.json').read_text())
    for name,digest in archive['files'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory) or sha(path)!=digest:raise ValueError('archive changed: '+name)
    report=json.loads((directory/'runtime-report.json').read_text());visible=json.loads((directory/'visible-report.json').read_text())
    if report['session']!=session or visible['session']!=session or visible['runtimeReportSha256']!=sha(directory/'runtime-report.json') or not report['producer_stopped_preview_cleared_markers']:raise ValueError('live identity/stop')
    mc=json.loads((directory/'mc-build-report.json').read_text());dc=json.loads((directory/'dc-build-report.json').read_text())
    if sha(directory/'mc-native-scene.jar')!=mc['sha256'] or sha(directory/'mc-build-report.json')!=report['mc_build_sha256']:raise ValueError('native producer build')
    if sha(directory/'Mcdn.DcFrameProbe.dll')!=next(v for k,v in dc['packages'].items() if k.endswith('Mcdn.DcFrameProbe.dll')):raise ValueError('native display build')
    with zipfile.ZipFile(directory/'display-sources.zip') as source:
        for name,digest in {**dc['sources'],**dc['linked_sources']}.items():
            if hashlib.sha256(source.read(name.replace('\\','/'))).hexdigest()!=digest:raise ValueError('display source drift')
    motion=json.loads((directory/'native-run/runtime-report.json').read_text());completion=json.loads((directory/'native-run/complete.json').read_text())
    if motion['eventsSha256']!=sha(directory/'native-run/events.jsonl') or motion['status']!='archived-dc-native-player-motion-pass' or not completion['serverRestored'] or completion['failed']:raise ValueError('native motion evidence')
    producers={r['frameId']:r for r in map(json.loads,(directory/'producer.jsonl').read_text().splitlines())};consumers=list(map(json.loads,(directory/'consumer.jsonl').read_text().splitlines()))
    if len(consumers)<20:raise ValueError('live coverage')
    for row in consumers:
        source=producers[row['frameId']]
        if any(source[k]!=row[k] for k in ['streamEpoch','nativeTick','width','height','rawSha256','packetSha256','readyQpc']):raise ValueError('native frame upload differs')
    if len(report['background_samples'])<3 or any(r['foreground_pid']!=report['dc_process']['pid'] for r in report['background_samples']):raise ValueError('DC foreground evidence')
    for name,digest in visible['captures'].items():
        if sha(directory/name)!=digest:raise ValueError('window capture changed')
        with Image.open(directory/name) as image:
            if image.width<2000 or image.height<1400:raise ValueError('DPI-correct full-window capture expected')
    print('COMBINED_ARCHIVE_PASS',session,len(consumers),'native DC uploads; motion, source, full-window and recovery evidence verified')

if __name__=='__main__':main()
