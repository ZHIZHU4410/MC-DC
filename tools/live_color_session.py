"""Create/hold one private, expiring diagnostic world-color mapping; never launch either game."""
import ctypes as c
import argparse
import secrets
import socket
import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/"artifacts/lab"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--physics',action='store_true');parser.add_argument('--full-view',action='store_true');parser.add_argument('--input-lab',action='store_true');parser.add_argument('--test-wrong-world',action='store_true');parser.add_argument('--dc-visuals',action='store_true');args=parser.parse_args()
    if args.dc_visuals and not args.input_lab:raise ValueError('DC visuals require the bounded native input scene')
    if args.test_wrong_world and not args.input_lab:raise ValueError('negative world test requires isolated input lab')
    if args.input_lab and not (args.physics and args.full_view):raise ValueError('input lab requires the full-view dedicated native scene')
    build=json.loads((ROOT/"artifacts/mailbox/build-report.json").read_text());native=Path(build["native_dll"])
    verified=json.loads((ROOT/"artifacts/world-color/report.json").read_text())
    if sha(native)!=build["native_sha256"] or verified["status"]!="pass" or verified["native_sha256"]!=sha(native):raise ValueError("verified native world-color build required")
    for name,digest in build["sources"].items():
        if sha(ROOT/name)!=digest:raise ValueError("native build source changed: "+name)
    parent=LAB/"live-color";parent.mkdir(exist_ok=True);session=uuid.uuid4();directory=parent/str(session)
    dll=c.WinDLL(str(native));dll.mcdn_private_directory.argtypes=[c.c_wchar_p];dll.mcdn_open_world_color.argtypes=[c.c_wchar_p,c.POINTER(c.c_ubyte),c.c_uint,c.c_int];dll.mcdn_open_world_color.restype=c.c_void_p;dll.mcdn_close.argtypes=[c.c_void_p]
    if dll.mcdn_private_directory(str(directory))!=1:raise ValueError("private session directory create failed")
    private_native=directory/"mcdn_ipc.dll";shutil.copyfile(native,private_native)
    identity=(c.c_ubyte*16).from_buffer_copy(session.bytes);mapping=directory/"color.map"
    handle=dll.mcdn_open_world_color(str(mapping),identity,384+1024*1024*4,1)
    if not handle:raise ValueError("native world-color create failed")
    try:
        expires=int(time.time()*1000)+900000
        manifest={"kind":"mcdn-live-world-color-diagnostic-1","session":str(session),"gameDir":str(Path(r'D:\MC\.minecraft\versions')/('MC-DC-Physics-26.3' if args.physics else 'MC-DC-Lab-26.3')),"dcGameRoot":str(LAB/"dc-game"),"map":str(mapping),"dll":str(private_native),"dllSha256":sha(private_native),"expiresUnixMs":expires,"eligibleForControl":False,"presentation":"full-scene-diagnostic" if args.full_view else "thumbnail"}
        if args.input_lab:
            scene=json.loads((ROOT/'artifacts/dc-scene/scene.json').read_text());mc=json.loads((ROOT/'artifacts/dc-scene/build-report.json').read_text());dc=json.loads((ROOT/'artifacts/dc-render-api/build-report.json').read_text())
            port=0 # The actual DC listener reserves its own OS-selected port and publishes it privately.
            manifest.update(inputLab=True,viewControl=True,inventoryControl=True,controlPort=port,controlNonce=secrets.token_hex(32),geometryDigest=scene['fixtureSha256'],geometryEpoch=scene['sourceEpoch'],mcBuild=mc['sha256'],dcBuild=next(v for k,v in dc['packages'].items() if k.endswith('Mcdn.DcFrameProbe.dll')))
            source=ROOT/'artifacts/dc-scene/source.mcdw';metadata=ROOT/'artifacts/dc-scene/source.json'
            if sha(source)!=scene['sourceDigest'] or sha(metadata)!=scene['sourceMetadataSha256']:raise ValueError('source world proof changed')
            shutil.copyfile(source,directory/'source.mcdw');shutil.copyfile(metadata,directory/'source.json')
            if args.test_wrong_world:
                bad=json.loads((directory/'source.json').read_text());bad['MapUid']+=1;(directory/'source.json').write_text(json.dumps(bad,indent=2));manifest['testWrongWorld']=True
            manifest.update(sourceWorld=str(directory/'source.mcdw'),sourceWorldSha256=sha(source),sourceMetadata=str(directory/'source.json'),sourceMetadataSha256=sha(directory/'source.json'),verifyDcSolids=True)
            if args.dc_visuals:
                visual=ROOT/'artifacts/dc-visuals/conversion-report.json';v=json.loads(visual.read_text())
                installed=json.loads((ROOT/'artifacts/dc-visuals/install.json').read_text())
                if sha(visual)!=installed['visualConfigSha256'] or sha(Path(installed['target']))!=v['packSha256'] or v['sceneDigest']!=scene['fixtureSha256']:raise ValueError('installed source art/geometry proof required')
                manifest.update(requiredDcAtlas=v['atlasName'],dcVisuals=True,captureMaxEdge=1024,visualConfigSha256=sha(visual),visualPackSha256=v['packSha256'])
        path=directory/"session.json";path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        pointer={"manifest":str(path),"sha256":sha(path)};(parent/"current-session.json").write_text(json.dumps(pointer,indent=2),encoding="utf-8")
        print("LIVE_COLOR_SESSION_READY",session,flush=True)
        while time.time()*1000<expires and not (directory/"stop-session").exists():time.sleep(.2)
    finally:dll.mcdn_close(handle)


if __name__=="__main__":main()
