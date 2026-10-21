"""world-1 over actual C# <-> Java TCP with a separate game-consumer surrogate."""
import json
import os
import queue
import secrets
import subprocess
import threading
import uuid
import verify_world
import verify_protocol as base

def main():
    verify_world.main()
    fault_checks=base.run(["java","-cp",str(base.BUILD/"java"),"dev.mcdn.protocol.PipelineFaultBench",
                           verify_world.BUILD/"vectors/good-scene.world",verify_world.BUILD/"vectors/ready.frame"])
    root=base.ROOT; env={**os.environ,"MCDN_BENCH_SESSION":str(uuid.uuid4()),"MCDN_BENCH_NONCE":secrets.token_hex(32)}
    dll=root/"tests/dotnet/bin/Release/net10.0/Mcdn.Protocol.Bench.dll"
    host=subprocess.Popen(["dotnet",str(dll),"pipeline-serve",str(verify_world.BUILD/"vectors/good-scene.world")],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    ready=queue.Queue();threading.Thread(target=lambda:ready.put(host.stdout.readline()),daemon=True).start()
    try:
        port=int(ready.get(timeout=10).strip())
        guest=subprocess.run(["java","-cp",str(base.BUILD/"java"),"dev.mcdn.protocol.PipelineBench",str(port),str(verify_world.BUILD/"vectors/ready.frame")],cwd=root,env=env,capture_output=True,text=True,timeout=25)
        out,err=host.communicate(timeout=10)
        if guest.returncode or host.returncode: raise RuntimeError(out+err+guest.stdout+guest.stderr)
        checks=[fault_checks,out.strip(),guest.stdout.strip()]
        report={"scope":"real TCP + separate consumer thread; synthetic geometry/frame/carrier and input sink, no game launch","checks":checks,
                "source_sha256":json.loads((base.BUILD/"report.json").read_text(encoding="utf-8"))["source_sha256"]}
        dest=root/"artifacts/pipeline";dest.mkdir(exist_ok=True);(dest/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        print("\n".join(checks));print("REPORT",dest/"report.json")
    finally:
        if host.poll() is None:host.kill();host.communicate()

if __name__=="__main__":main()
