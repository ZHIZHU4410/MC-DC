"""MCWC golden/malformed vectors and real Java JNI -> C# native typed mailbox."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import uuid
import zlib
from verify_mailbox import bounded_line

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/world-color"


def main():
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path,required=True);a=p.parse_args()
    OUT.mkdir(exist_ok=True);vectors=OUT/"vectors";vectors.mkdir(exist_ok=True)
    packet=bytearray(384+4*4*3);packet[:4]=b"MCWC";struct.pack_into("<HHII",packet,4,0,1,384,48)
    packet[16:32]=uuid.uuid4().bytes
    for offset,value in [(32,1),(56,1),(64,123),(72,100),(304,200),(312,10000000)]:struct.pack_into("<Q",packet,offset,value)
    struct.pack_into("<8I",packet,80,4,3,16,1,7,0,2560,1494);struct.pack_into("<fff",packet,160,15,-5,.5)
    for start in [176,240]:
        for i in range(4):struct.pack_into("<f",packet,start+i*20,1)
    packet[384:]=bytes([12,87,212,255])*12;struct.pack_into("<I",packet,320,zlib.crc32(packet[384:]))
    (vectors/"valid-frame.bin").write_bytes(packet)
    cases=[("magic",0,"I",0),("version",6,"H",2),("header",8,"I",256),("length",12,"I",4),("stream",32,"Q",0),("reserved40",40,"Q",1),("reserved48",48,"Q",1),("id",56,"Q",0),("request",72,"Q",0),("width",80,"I",0),("hugewidth",80,"I",0xffffffff),("stride",88,"I",3),("format",92,"I",2),("flags",96,"I",1),("camera",100,"I",3),("source",104,"I",0xffffffff),("pose",112,"d",float('nan')),("angle",160,"f",float('inf')),("partial",168,"f",2),("reserved172",172,"I",1),("viewnan",176,"f",float('nan')),("projectioninf",240,"f",float('inf')),("ready",304,"Q",1),("frequency",312,"Q",0),("frequencyhigh",312,"Q",1<<63),("reservedend",380,"I",1),("crc",384,"B",99)]
    for name,offset,kind,value in cases:
        bad=packet.copy();struct.pack_into("<"+kind,bad,offset,value);(vectors/("bad-"+name+".bin")).write_bytes(bad)
    for name,start,length in [("zerosession",16,16),("zeroview",176,64),("zeroprojection",240,64)]:
        bad=packet.copy();bad[start:start+length]=bytes(length);(vectors/("bad-"+name+".bin")).write_bytes(bad)
    (vectors/"bad-truncated.bin").write_bytes(packet[:-1]);(vectors/"bad-trailing.bin").write_bytes(packet+b'\0')
    build=json.loads((ROOT/"artifacts/mailbox/build-report.json").read_text());dll=Path(build["native_dll"]);digest=build["native_sha256"]
    if hashlib.sha256(dll.read_bytes()).hexdigest()!=digest:raise ValueError("native build changed")
    env={**os.environ,"DOTNET_CLI_HOME":str(OUT/"dotnet-home"),"APPDATA":str(OUT/"appdata"),"DOTNET_CLI_TELEMETRY_OPTOUT":"1","DOTNET_CLI_UI_LANGUAGE":"en"};(OUT/"appdata").mkdir(exist_ok=True)
    project=ROOT/"tests/worldcolor/dotnet/Mcdn.WorldColor.Bench.csproj"
    def run(cmd):
        r=subprocess.run(list(map(str,cmd)),env=env,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout
    run(["dotnet","restore",project,"--configfile",ROOT/"NuGet.Config"]);run(["dotnet","build",project,"-c","Release","--no-restore","--nologo"])
    classes=OUT/"java";classes.mkdir(exist_ok=True)
    run([a.java_home/"bin/javac.exe","-Xlint:all","-Werror","-encoding","UTF-8","-cp",ROOT/"artifacts/mailbox/java","-d",classes,ROOT/"tests/worldcolor/java/dev/mcdn/tests/WorldColorBench.java"])
    server=subprocess.Popen(list(map(str,["dotnet",project.parent/"bin/Release/net10.0/Mcdn.WorldColor.Bench.dll",vectors,dll,digest,OUT])),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8")
    try:
        ready=bounded_line(server)
        java=run([a.java_home/"bin/java.exe","--enable-native-access=ALL-UNNAMED","-cp",str(classes)+";"+str(ROOT/"artifacts/mailbox/java"),"dev.mcdn.tests.WorldColorBench",vectors,dll,digest,ready["file"],ready["port"]])
        stdout,stderr=server.communicate(timeout=20)
        if server.returncode:raise RuntimeError(stderr)
        result=json.loads(stdout.strip());assert result["status"]=="pass"
        report={"status":"pass","scope":"synthetic MCWC codec/native typed mailbox; not game capture/display", "native_sha256":digest,"dotnet":result,"java":java.strip(),"vectors":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(vectors.glob('*.bin'))},"sources":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [ROOT/"src/java",ROOT/"src/ipc",ROOT/"src/native",ROOT/"src/dotnet/Mcdn.Protocol",ROOT/"src/dotnet/Mcdn.FrameMailbox",ROOT/"tests/worldcolor"] for p in folder.rglob('*') if p.suffix in ['.cs','.java','.cpp','.csproj'] and 'bin' not in p.parts and 'obj' not in p.parts}}
        (OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print("WORLD_COLOR_PASS",result,java.strip())
    finally:
        if server.poll() is None:server.terminate();server.wait(timeout=5)


if __name__=="__main__":main()
