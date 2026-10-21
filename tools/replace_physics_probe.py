"""Replace only the recorded own physics JAR, after normal game exit, with backup."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/physics"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    record=json.loads((OUT/"install.json").read_text());target=Path(record['target_jar']);game=target.parent.parent
    if game!=Path(r'D:\MC\.minecraft\versions\MC-DC-Physics-26.3') or not (game/'MCDN_PHYSICS_LAB').is_file() or sha(target)!=record['installed_sha256']:raise ValueError('only the recorded owned physics JAR may be replaced')
    build=json.loads((OUT/'build-report.json').read_text());source=Path(build['jar'])
    if sha(source)!=build['sha256'] or not build['transform']:raise ValueError('matching transformed build required')
    for name,digest in build['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('source changed since build')
    backup=ROOT/'artifacts/backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-physics-own-replace');backup.mkdir(parents=True)
    with zipfile.ZipFile(backup/'lab-before.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for p in [target,game/'mcdn-physics.json',game/'options.txt',*list((game/'saves').rglob('*'))]:
            if p.is_file():archive.writestr(str(p.relative_to(game)),p.read_bytes())
        archive.writestr('previous-install.json',json.dumps(record,indent=2))
    if sha(target)!=record['installed_sha256']:raise ValueError('owned JAR changed during backup')
    temporary=target.with_name(target.name+'.mcdn-new')
    with temporary.open('xb') as stream:stream.write(source.read_bytes())
    temporary.replace(target)
    record.update(installed_sha256=sha(target),build_report_sha256=sha(OUT/'build-report.json'),replacement_backup=str(backup));(OUT/'install.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('PHYSICS_OWNED_REPLACE_PASS',backup)


if __name__=='__main__':main()
