"""Stage a new isolated MC 26.3 profile from the pinned PeakCraft Fabric build.

Never merges with an existing profile or installs alongside MCDN's physics mod.
The upstream MIT source and game binaries remain outside this source project.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile
from xml.etree import ElementTree

from export_peakcraft_collision import ROOT, UPSTREAM_COMMIT, verify_upstream

MC_ROOT = Path(r'D:\MC\.minecraft')
SOURCE = MC_ROOT/'versions/MC-DC-Lab-26.3'
TARGET = MC_ROOT/'versions/MC-DC-PeakBase-26.3'
API = MC_ROOT/'versions/MC-PEAK-Bridge-26.3/mods/fabric-api.jar'
GAME_SHA = '4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d'
NAME = TARGET.name


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(upstream):
    proof = verify_upstream(upstream)
    if not (SOURCE/'MCDN_ISOLATED_LAB').is_file() or sha(SOURCE/(SOURCE.name+'.jar')) != GAME_SHA:
        raise ValueError('marked pinned MC 26.3 source laboratory required')
    if TARGET.exists():
        raise ValueError('PeakCraft target exists; never merge an existing MC profile')
    jar = upstream/'fabric/build/libs/skycraft-0.1.2.jar'
    if not jar.is_file():
        raise ValueError('build the pinned PeakCraft Fabric mod first')
    with ZipFile(jar) as archive:
        if archive.testzip() is not None:
            raise ValueError('corrupt pinned Fabric artifact')
        mod = json.loads(archive.read('fabric.mod.json'))
    if mod['id']!='skycraft' or mod['version']!='0.1.2' or mod['depends']['minecraft']!='~26.3':
        raise ValueError('upstream Fabric artifact identity')
    with ZipFile(API) as archive:
        api = json.loads(archive.read('fabric.mod.json'))
    if api['id']!='fabric-api' or api['version']!='0.161.0+26.3':
        raise ValueError('known matching Fabric API required')
    test_dir=upstream/'fabric/build/test-results/test'
    suites=[ElementTree.parse(path).getroot() for path in test_dir.glob('TEST-*.xml')]
    tests=sum(int(s.get('tests','0')) for s in suites)
    if tests!=21 or any(int(s.get(k,'0')) for s in suites for k in ('failures','errors','skipped')):
        raise ValueError('pinned upstream native-physics tests required')
    version=json.loads((SOURCE/(SOURCE.name+'.json')).read_text(encoding='utf-8-sig'))
    if version['id']!=SOURCE.name or not any('fabric-loader:0.20.0' in lib['name'] for lib in version['libraries']):
        raise ValueError('isolated Fabric loader source')
    version['id']=NAME
    version['arguments']['jvm']=[v for v in version['arguments']['jvm']
                                if not (isinstance(v,str) and v.startswith(('-Dmcdn.','-Dskycraft.')))]
    version['arguments']['jvm'] += ['--enable-native-access=ALL-UNNAMED',
                                   '-Dskycraft.link=Local\\MCDN_PeakBase_v11',
                                   '-Dskycraft.quitWithSkyrim=false']
    out=ROOT/'artifacts/peakcraft/profile-stage'
    out.mkdir(parents=True,exist_ok=True)
    (out/(NAME+'.json')).write_text(json.dumps(version,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'MCDN_ISOLATED_LAB').write_text('New private PeakCraft MC guest, no DC host installed\n')
    (out/'MCDN_PEAKCRAFT_BASE').write_text(UPSTREAM_COMMIT+'\n')
    options=(SOURCE/'options.txt').read_text(encoding='utf-8').splitlines()
    options=[row for row in options if not row.startswith('pauseOnLostFocus:')]
    options.append('pauseOnLostFocus:false')
    (out/'options.txt').write_text('\n'.join(options)+'\n',encoding='utf-8')
    (out/'PCL').mkdir(exist_ok=True)
    shutil.copyfile(SOURCE/'PCL/Setup.ini',out/'PCL/Setup.ini')
    (out/'mods').mkdir(exist_ok=True)
    shutil.copyfile(jar,out/'mods/skycraft-0.1.2.jar')
    shutil.copyfile(API,out/'mods/fabric-api.jar')
    shutil.copyfile(upstream/'LICENSE',out/'LICENSE-PeakCraft-SkyCraft.txt')
    report={'kind':'pinned-peakcraft-private-mc-profile','sourceCommit':UPSTREAM_COMMIT,
            'sourceProtocol':proof,'sourceGameSha256':GAME_SHA,'skycraftJarSha256':sha(jar),
            'fabricApiSha256':sha(API),'upstreamTests':tests,'target':str(TARGET),
            'stage':str(out),'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},
            'realClientLoaded':False,'dcHostConnected':False,'productionModeGranted':False}
    (ROOT/'artifacts/peakcraft/profile-plan.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return out,report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--upstream',type=Path,required=True)
    parser.add_argument('--install',action='store_true')
    args=parser.parse_args()
    out,report=stage(args.upstream.resolve())
    if args.install:
        TARGET.mkdir()
        for path in out.rglob('*'):
            if path.is_file():
                dest=TARGET/path.relative_to(out)
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,dest)
        shutil.copyfile(SOURCE/(SOURCE.name+'.jar'),TARGET/(NAME+'.jar'))
        if sha(TARGET/(NAME+'.jar'))!=GAME_SHA or any(sha(TARGET/name)!=value for name,value in report['files'].items()):
            raise ValueError('private installed profile differs from staged proof')
        report['installed']=True
        (ROOT/'artifacts/peakcraft/profile-plan.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('PEAKCRAFT_MC_PROFILE_INSTALLED',TARGET)
    else:
        print('PEAKCRAFT_MC_PROFILE_STAGED',json.dumps({k:report[k] for k in ('sourceCommit','skycraftJarSha256','upstreamTests','target')}))


if __name__=='__main__':main()

