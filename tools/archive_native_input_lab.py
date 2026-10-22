"""Freeze the completed diagnostic input experiment; deliberately excludes private manifest/nonce."""
import json
import argparse
import re
from pathlib import Path
import shutil
import zipfile
from archive_combined_scene import exited
from check_native_input_lab import check, sha

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT/'artifacts/lab'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--failure',action='store_true');parser.add_argument('--world-negative',action='store_true');args=parser.parse_args()
    pointer = json.loads((LAB/'live-color/current-session.json').read_text())
    cfg = json.loads(Path(pointer['manifest']).read_text())
    live = Path(pointer['manifest']).parent
    native = Path(json.loads((ROOT/'artifacts/dc-scene/observations/current-run.json').read_text())['directory'])
    destination = ROOT/'artifacts/native-input'/cfg['session']
    dc = json.loads((LAB/'dc-process.json').read_text())
    mc = json.loads((ROOT/'artifacts/physics/process.json').read_text(encoding='utf-8-sig'))
    codes = dict(dc=exited(dc), mc=exited(mc))
    destination.mkdir(parents=True, exist_ok=False)
    identity = dict(session=cfg['session'], testWrongWorld=cfg.get('testWrongWorld',False),verifyDcSolids=cfg.get('verifyDcSolids',False),viewControl=cfg.get('viewControl',False),geometryDigest=cfg['geometryDigest'], mcBuild=cfg['mcBuild'], dcBuild=cfg['dcBuild'], dcProcess=dc, mcProcess=mc, exitCodes=codes)
    (destination/'identity.json').write_text(json.dumps(identity, indent=2))
    identity['inventoryControl']=cfg.get('inventoryControl',False)
    identity['dcVisuals']=cfg.get('dcVisuals',False)
    if identity['dcVisuals']:
        identity.update(visualConfigSha256=cfg['visualConfigSha256'],visualPackSha256=cfg['visualPackSha256'],requiredDcAtlas=cfg['requiredDcAtlas'])
        shutil.copyfile(ROOT/'artifacts/dc-visuals/conversion-report.json',destination/'visual-source.json')
    (destination/'identity.json').write_text(json.dumps(identity, indent=2))
    sources = {}
    for name, original in [('mc-build.json', ROOT/'artifacts/dc-scene/build-report.json'), ('frame-build.json', ROOT/'artifacts/frame-probe/build-report.json'), ('dc-build.json', ROOT/'artifacts/dc-render-api/build-report.json'), ('guard-build.json', LAB/'dc-build-report.json')]:
        build = json.loads(original.read_text())
        shutil.copyfile(original, destination/name)
        for key, digest in {**build['sources'], **build.get('linked_sources', {})}.items():
            if sha(ROOT/key) != digest:
                raise ValueError('source drift: '+key)
            sources[key.replace('\\','/')] = ROOT/key
    with zipfile.ZipFile(destination/'sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for key, source in sources.items():
            archive.write(source, key)
        for name in ['archive_native_input_lab.py','check_native_input_lab.py','exercise_native_input_lab.py','check_world_guard_negative.py']:
            archive.write(ROOT/'tools'/name, 'tools/'+name)
        if identity['dcVisuals']:
            for name in ['build_dc_visual_pack.py','install_dc_visuals.py','check_dc_visuals.py']:
                archive.write(ROOT/'tools'/name,'tools/'+name)
    for name in ['producer.jsonl','consumer.jsonl','native-host-input.jsonl','native-input-states.jsonl','keyboard-experiment.json','input-ready.png','input-wall.png','input-jump.png','input-returned.png']:
        if (args.failure or args.world_negative) and not (live/name).exists():continue
        shutil.copyfile(live/name, destination/name)
    if cfg.get('viewControl'):
        for name in ['input-look-third.png','input-look-first.png']:
            if (args.failure or args.world_negative) and not (live/name).exists():continue
            shutil.copyfile(live/name,destination/name)
    if cfg.get('inventoryControl') and not args.world_negative and (live/'input-inventory.png').exists():
        shutil.copyfile(live/'input-inventory.png',destination/'input-inventory.png')
    for name in ['complete.json','events.jsonl']:
        if args.world_negative and name=='complete.json' and not (native/name).exists():continue
        shutil.copyfile(native/name, destination/name)
    if args.world_negative:shutil.copyfile(live/'input-world-refused.png',destination/'input-world-refused.png')
    for name in ['scene.mcdw','scene.json']:
        shutil.copyfile(ROOT/'artifacts/dc-scene'/name, destination/name)
    if cfg.get('verifyDcSolids'):
        for name in ['source.mcdw','source.json']:shutil.copyfile(live/name,destination/name)
    install = json.loads((ROOT/'artifacts/dc-scene/install.json').read_text())
    shutil.copyfile(install['target_jar'], destination/'own.jar')
    shutil.copyfile(LAB/'dc-mods/McdnDcFrameProbe/Mcdn.DcFrameProbe.dll', destination/'own.dll')
    shutil.copyfile(LAB/'dc-logs/log_latest.log', destination/'dc-runtime.log')
    if args.world_negative:
        match=re.search(r'MCDN read-only probe\s+"?([0-9a-f-]{36})', (destination/'dc-runtime.log').read_text(errors='replace'))
        if not match:raise ValueError('actual current DC probe session missing')
        proof=LAB/'dc-probe'/match[1].replace('-','')/'latest.json';actual=json.loads(proof.read_text())
        if Path(actual['file']).name!=actual['file']:raise ValueError('current DC source filename')
        shutil.copyfile(proof,destination/'dc-current-source.json');shutil.copyfile(proof.parent/actual['file'],destination/'dc-current-source.mcdw')
    shutil.copyfile(Path(cfg['gameDir'])/'logs/latest.log', destination/'mc-runtime.log')
    (destination/'archive.json').write_text(json.dumps(dict(files={p.name:sha(p) for p in destination.iterdir() if p.is_file()}), indent=2))
    if args.failure:
        (destination/'failure.json').write_text(json.dumps(dict(status='not-accepted',reason=json.loads((live/'keyboard-experiment.json').read_text()).get('error')),indent=2))
        print('FAILED_NATIVE_INPUT_EXPERIMENT_PRESERVED',destination);return
    if args.world_negative:
        from check_world_guard_negative import check as negative_check
        report=negative_check(destination)
        (destination/'runtime-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return
    report = check(destination)
    (destination/'runtime-report.json').write_text(json.dumps(report, indent=2))
    print('NATIVE_INPUT_ARCHIVED', destination)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
