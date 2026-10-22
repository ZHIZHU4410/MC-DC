"""Build a standalone real-player integration test. Never modifies or starts a game profile."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import uuid
from zipfile import ZipFile,ZIP_DEFLATED
from verify_fabric_package import verify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/physics"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path,required=True);p.add_argument("--mc-version-dir",type=Path,required=True);p.add_argument('--dc-scene',action='store_true');a=p.parse_args()
    if a.dc_scene:OUT=ROOT/'artifacts/dc-scene'
    OUT.mkdir(exist_ok=True);version=a.mc_version_dir.resolve();gamejar=version/(version.name+".jar");cp=[gamejar]
    meta=json.loads((version/(version.name+".json")).read_text(encoding="utf-8-sig"));libs=version.parent.parent/"libraries"
    for lib in meta["libraries"]:
        group,artifact,ver,*classifier=lib["name"].split(":");path=libs/group.replace('.','/')/artifact/ver/(artifact+'-'+ver+('-'+classifier[0] if classifier else '')+'.jar')
        if path.exists():cp.append(path)
    boxes=[(1,-4,199,-1.25,4,200,2.25),(2,2.25,200,-1.25,2.75,204,2.25),(3,-1,202.5,-1.25,1,203,2.25),(4,-4,200,-1.75,4,204,-1.25),(5,-4,200,2.25,4,204,2.75)]
    records=b''.join(struct.pack('<Q6dII',*box,1,0) for box in boxes);identity=uuid.uuid5(uuid.NAMESPACE_URL,'mcdn-native-physics-fixture-1')
    blob=struct.pack('<4sHHII16sQQII32sQ',b'MCDW',0,1,96,len(boxes),identity.bytes,1,1,64,0,hashlib.sha256(records).digest(),0)+records
    fixture=OUT/"fixture-world.mcdw"
    if a.dc_scene:
        blob=(OUT/'scene.mcdw').read_bytes()
        plan=json.loads((OUT/'scene.json').read_text())
        if sha(OUT/'scene.mcdw')!=plan['fixtureSha256']:raise ValueError('prepared DC scene required')
    fixture.write_bytes(blob)
    def run(cmd):
        r=subprocess.run(list(map(str,cmd)),cwd=OUT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout+r.stderr
    jar=OUT/"mcdn-native-physics-0.1.0.jar";sources=[*sorted((ROOT/"src/physics/java").rglob('*.java')),*sorted((ROOT/"src/java").rglob('*.java')),*sorted((ROOT/"src/minecraft/java").rglob('*.java'))]
    frame=json.loads((ROOT/"artifacts/frame-probe/build-report.json").read_text());framejar=Path(frame["jar"])
    if sha(framejar)!=frame["sha256"]:raise ValueError("known native frame addon required")
    with tempfile.TemporaryDirectory(dir=OUT,prefix='classes-') as temporary:
        classes=Path(temporary);q=lambda v:'"'+str(v).replace('\\','/')+'"'
        args=OUT/"javac.args";args.write_text('\n'.join(['-encoding','UTF-8','-proc:none','-Xlint:all,-classfile','-Werror','-cp',q(';'.join(map(str,[*cp,framejar]))),'-d',q(classes),*map(q,sources)]),encoding='utf-8')
        run([a.java_home/'bin/javac.exe','-J-Duser.language=en','@'+str(args)])
        with ZipFile(jar,'w',ZIP_DEFLATED) as z:
            for path in classes.rglob('*.class'):z.write(path,path.relative_to(classes).as_posix())
            for path in (ROOT/'src/physics/resources').iterdir():
                if path.name=='fabric.mod.json':
                    mod=json.loads(path.read_text());mod['entrypoints']['client'].append('dev.mcdn.frameprobe.FrameProbe');mod['mixins'].append('mcdn-frame.mixins.json');z.writestr(path.name,json.dumps(mod))
                else:z.write(path,path.name)
            # Reuse our exact compiled GPU diagnostic, without the unrelated geometry addon's metadata dependency.
            with ZipFile(framejar) as framez:
                for name in framez.namelist():
                    if name.startswith(('dev/mcdn/frameprobe/','dev/mcdn/ipc/')) or name=='mcdn-frame.mixins.json':z.writestr(name,framez.read(name))
    package=verify(jar)
    game=OUT/'transform-game';(game/'mods').mkdir(parents=True,exist_ok=True);(game/'mods'/jar.name).write_bytes(jar.read_bytes());(game/'MCDN_PHYSICS_LAB').write_text('Transform-only physics lab\n')
    # Transform preflight uses the exact required name but never constructs a game/client.
    named=OUT/'MC-DC-Physics-26.3';(named/'mods').mkdir(parents=True,exist_ok=True);(named/'mods'/jar.name).write_bytes(jar.read_bytes());(named/'MCDN_PHYSICS_LAB').write_text('Transform-only physics lab\n')
    config={'gameDir':str(named),'fixture':str(fixture),'fixtureSha256':sha(fixture),'output':str(OUT/'transform-observations')}
    if a.dc_scene:config['dcScene']=str(OUT/'scene.json')
    manifest=OUT/'transform-config.json';manifest.write_text(json.dumps(config),encoding='utf-8')
    bench=OUT/'bench';bench.mkdir(exist_ok=True)
    run([a.java_home/'bin/javac.exe','-encoding','UTF-8','-proc:none','-cp',';'.join(map(str,cp)),'-d',bench,ROOT/'tests/physics/dev/mcdn/tests/PhysicsTransformBench.java'])
    output=run([a.java_home/'bin/java.exe','-Djava.awt.headless=true','-Dfabric.log.disableAnsi=true','-Dmcdn.physics.manifest='+str(manifest),'-cp',str(bench)+';'+';'.join(map(str,cp)),'dev.mcdn.tests.PhysicsTransformBench',named,fixture,*([OUT/'scene.json'] if a.dc_scene else [])]);(OUT/'transform.log').write_text(output,encoding='utf-8')
    marker=next((l for l in output.splitlines() if l.startswith('PHYSICS_TRANSFORM_PASS')),None)
    if marker is None:raise ValueError('native physics hook preflight missing')
    report={'scope':'actual MC26.3 compile/Knot transformation, not player movement','geometrySource':'archived-dc-solid-subset' if a.dc_scene else 'synthetic-fixture','jar':str(jar),'sha256':sha(jar),'game_sha256':sha(gamejar),'fixture_sha256':sha(fixture),'package':package,'transform':marker,'linked_frame_jar_sha256':sha(framejar),'sources':{str(p.relative_to(ROOT)):sha(p) for p in sources+list((ROOT/'src/physics/resources').iterdir())+[ROOT/'tests/physics/dev/mcdn/tests/PhysicsTransformBench.java']}}
    (OUT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PHYSICS_BUILD_PASS',jar);print(marker)


if __name__=='__main__':main()
