"""Stage or replace ONLY the recorded physics addon/config, with a complete lab backup."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from prepare_dc_scene import ROOT, OUT, sha


def digest(path):return sha(path.read_bytes())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    record_path=ROOT/'artifacts/physics/install.json'
    record=json.loads(record_path.read_text());target=Path(record['target_jar']);game=target.parent.parent
    if game!=Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3') or not (game/'MCDN_PHYSICS_LAB').is_file() or digest(target)!=record['installed_sha256']:
        raise ValueError('recorded own physics package/profile required')
    build=json.loads((OUT/'build-report.json').read_text());verification=json.loads((OUT/'verification.json').read_text());source=Path(build['jar'])
    if digest(source)!=build['sha256'] or verification['nativeBuild']!=build['sha256'] or not build['transform']:
        raise ValueError('matching verified native build required')
    plan=json.loads((OUT/'scene.json').read_text())
    if digest(OUT/'scene.mcdw')!=build['fixture_sha256'] or verification['sceneDigest']!=build['fixture_sha256'] or plan['fixtureSha256']!=build['fixture_sha256'] or digest(OUT/'source.mcdw')!=plan['sourceDigest']:
        raise ValueError('prepared/verified source and scene drift')
    for name,value in build['sources'].items():
        if digest(ROOT/name)!=value:raise ValueError('source changed after build')
    config=dict(gameDir=str(game),fixture=str(OUT/'scene.mcdw'),fixtureSha256=build['fixture_sha256'],dcScene=str(OUT/'scene.json'),output=str(OUT/'observations'))
    (OUT/'runtime-config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print('DC_SCENE_INSTALL_PLAN',json.dumps(dict(target=str(target),sha256=build['sha256'],config=config)))
    if not args.install:return
    # Never swap loaded code. Inspect names only; no launch arguments/accounts are read.
    result=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process java,javaw -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,check=True)
    if result.stdout.strip()!='0':raise ValueError('close Java games normally before replacement')
    backup=ROOT/'artifacts/backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-dc-scene')
    backup.mkdir(parents=True)
    with zipfile.ZipFile(backup/'lab-before.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for p in [target,game/'mcdn-physics.json',game/'mcdn-lab.json',game/'options.txt',*list((game/'saves').rglob('*'))]:
            if p.is_file():archive.write(p,p.relative_to(game))
        archive.writestr('previous-install.json',json.dumps(record,indent=2))
    if digest(target)!=record['installed_sha256']:raise ValueError('owned package drift during backup')
    shutil.copyfile(source,target)
    shutil.copyfile(OUT/'runtime-config.json',game/'mcdn-physics.json')
    # Keep the GPU observer in the same run's evidence tree.
    (game/'mcdn-lab.json').write_text(json.dumps(dict(gameDir=str(game),outputDir=str(OUT/'observations'),captureMinY=195,captureCameraType='THIRD_PERSON_BACK'),indent=2),encoding='utf-8')
    record.update(installed_sha256=digest(target),active_build_report=str(OUT/'build-report.json'),replacement_backup=str(backup),geometrySource='archived-dc-solid-subset')
    record_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    (OUT/'install.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('DC_SCENE_INSTALLED',backup)


if __name__=='__main__':main()
