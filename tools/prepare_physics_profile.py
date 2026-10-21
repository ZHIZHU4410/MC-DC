"""Create a new standalone physics profile from owned installed files; never merge an existing directory."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/physics"
NAME="MC-DC-Physics-26.3"
SOURCE=Path(r"D:\MC\.minecraft\versions\MC-DC-Lab-26.3")
TARGET=SOURCE.parent/NAME


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--install",action="store_true");a=p.parse_args()
    build=json.loads((OUT/"build-report.json").read_text());jar=Path(build["jar"])
    if sha(jar)!=build["sha256"] or sha(SOURCE/(SOURCE.name+".jar"))!=build["game_sha256"] or not build["transform"]:raise ValueError("pinned tested package/game required")
    for name,digest in build["sources"].items():
        if sha(ROOT/name)!=digest:raise ValueError("physics source changed since transform")
    if TARGET.exists():raise ValueError("new profile only; do not merge or replace an existing physics world")
    meta=json.loads((SOURCE/(SOURCE.name+".json")).read_text(encoding="utf-8-sig"));meta["id"]=NAME
    meta["arguments"]["jvm"]=[s for s in meta["arguments"]["jvm"] if not (isinstance(s,str) and s.startswith(('-Dmcdn.lab.manifest=','-Dmcdn.physics.manifest=')))]+['-Dmcdn.lab.manifest='+str(TARGET/'mcdn-lab.json'),'-Dmcdn.physics.manifest='+str(TARGET/'mcdn-physics.json')]
    config={'gameDir':str(TARGET),'fixture':str(OUT/'fixture-world.mcdw'),'fixtureSha256':build['fixture_sha256'],'output':str(OUT/'observations')}
    frame={'gameDir':str(TARGET),'outputDir':str(OUT/'observations')}
    stage=OUT/'profile-stage';stage.mkdir(exist_ok=True)
    (stage/(NAME+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');(stage/'mcdn-physics.json').write_text(json.dumps(config,indent=2),encoding='utf-8');(stage/'mcdn-lab.json').write_text(json.dumps(frame,indent=2),encoding='utf-8')
    (stage/'MCDN_ISOLATED_LAB').write_text('Own isolated physics game directory\n');(stage/'MCDN_PHYSICS_LAB').write_text('Native player fixture only; not production DC control\n')
    (stage/'PCL').mkdir(exist_ok=True);shutil.copyfile(SOURCE/'PCL/Setup.ini',stage/'PCL/Setup.ini');shutil.copyfile(SOURCE/'options.txt',stage/'options.txt')
    rows=(stage/'options.txt').read_text(encoding='utf-8').splitlines();rows=[r for r in rows if not r.startswith('pauseOnLostFocus:')];rows.append('pauseOnLostFocus:false');(stage/'options.txt').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    (stage/'mods').mkdir(exist_ok=True);shutil.copyfile(jar,stage/'mods'/jar.name)
    plan={'scope':'new dedicated laboratory; no original saves, account, launcher settings or existing profile modified','target':str(TARGET),'files':{str(p.relative_to(stage)):sha(p) for p in stage.rglob('*') if p.is_file()},'game_sha256':build['game_sha256'],'build_report_sha256':sha(OUT/'build-report.json'),'world':'Create single-player superflat MCDN-Physics, then wait for the probe ready marker; begin requires an explicit per-run file'}
    (OUT/'profile-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    if not a.install:print('PHYSICS_PROFILE_READY');return
    backup=ROOT/'artifacts/backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-new-physics-profile');backup.mkdir(parents=True)
    with zipfile.ZipFile(backup/'source-config.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for file in [SOURCE/(SOURCE.name+'.json'),SOURCE/'options.txt',SOURCE/'PCL/Setup.ini']:archive.write(file,file.relative_to(SOURCE))
    TARGET.mkdir()
    for p in stage.rglob('*'):
        if p.is_file():target=TARGET/p.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    shutil.copyfile(SOURCE/(SOURCE.name+'.jar'),TARGET/(NAME+'.jar'))
    for name,digest in plan['files'].items():
        if sha(TARGET/name)!=digest:raise ValueError('installed file mismatch')
    if sha(TARGET/(NAME+'.jar'))!=plan['game_sha256']:raise ValueError('installed game mismatch')
    (OUT/'install.json').write_text(json.dumps({**plan,'installed':True,'backup':str(backup),'target_jar':str(TARGET/'mods'/jar.name),'installed_sha256':sha(TARGET/'mods'/jar.name)},indent=2),encoding='utf-8');print('PHYSICS_PROFILE_INSTALLED',TARGET,'BACKUP',backup)


if __name__=='__main__':main()
