"""Inspect local game signatures, compile our input adapter; never run/modify the game.

Raw javap output must be kept OUTSIDE the project and never distributed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CLASSES = {
    "net.minecraft.client.player.ClientInput": ["tick", "getMoveVector"],
    "net.minecraft.client.player.KeyboardInput": ["tick"],
    "net.minecraft.client.player.LocalPlayer": ["aiStep", "sendChanges", "applyInput", "move"],
    "net.minecraft.server.network.ServerGamePacketListenerImpl": ["handlePlayerInput", "handleMovePlayer", "handlePlayerPositionChange"],
    "net.minecraft.server.level.ServerPlayer": ["setLastClientInput"],
    "net.minecraft.world.entity.Entity": ["move", "collide", "collideBoundingBox", "collectCollidersIgnoringWorldBorder"],
    "net.minecraft.world.level.CollisionGetter": ["getPreMoveCollisions", "getBlockCollisions", "getBlockCollisionsFromContext"],
}


def run(args):
    p = subprocess.run(list(map(str, args)), cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=45)
    if p.returncode: raise RuntimeError(p.stdout + p.stderr)
    return p.stdout + p.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--mc-version-dir", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--world-fixture-root", type=Path)
    args = parser.parse_args()
    private = args.private_output.resolve()
    if private == ROOT or ROOT in private.parents: raise ValueError("raw game bytecode must stay outside project")
    private.mkdir(parents=True, exist_ok=True)
    folder = args.mc_version_dir.resolve()
    jar = folder / (folder.name + ".jar")
    javap = args.java_home / "bin/javap.exe"
    javac = args.java_home / "bin/javac.exe"
    evidence = {}
    for cls, wanted in CLASSES.items():
        raw = run([javap, "-classpath", jar, "-p", "-c", "-s", cls])
        path = private / (cls + ".txt")
        path.write_text(raw, encoding="utf-8")
        blocks = re.split(r"(?=^  (?:public|protected|private) .*\([^\n]*\);\s*$)", raw, flags=re.M)
        methods = []
        for block in blocks:
            header = block.splitlines()[0] if block.splitlines() else ""
            if any(re.search(r"\b" + name + r"\(", header) for name in wanted):
                # Report symbolic references only; the private file preserves complete bytecode.
                references = sorted(set(re.findall(r"// (?:InterfaceMethod|Method|Field) ([^\n\r]+)", block)))
                methods.append({"signature": header.strip(), "references": references})
        if not methods: raise ValueError("expected methods absent: " + cls)
        evidence[cls] = {"private_bytecode": str(path), "sha256": hashlib.sha256(raw.encode()).hexdigest(), "methods": methods}
    # Compile against the actual local JAR and its installed library set, not stubs.
    meta = json.loads((folder / (folder.name + ".json")).read_text(encoding="utf-8-sig"))
    libraries = folder.parent.parent / "libraries"
    cp = [jar]
    for lib in meta["libraries"]:
        parts = lib["name"].split(":")
        group, artifact, version = parts[:3]
        classifier = "-" + parts[3] if len(parts) > 3 else ""
        path = libraries / group.replace(".", "/") / artifact / version / (artifact + "-" + version + classifier + ".jar")
        if path.exists(): cp.append(path)
    output = ROOT / "artifacts" / "mc-api"
    output.mkdir(parents=True, exist_ok=True)
    classes = output / "classes"
    sources = sorted((ROOT / "src/java").rglob("*.java")) + sorted((ROOT / "src/minecraft/java").rglob("*.java"))
    sources += sorted((ROOT / "tests/minecraft").rglob("*.java"))
    # All paths in an argfile, avoiding Windows command length and quoting limits.
    def quote(value): return '"' + str(value).replace("\\", "/").replace('"', '\\"') + '"'
    argfile = output / "javac.args"
    argfile.write_text("\n".join(["-encoding", "UTF-8", "-proc:none", "-d", quote(classes), "-classpath",
                                 quote(";".join(map(str, cp))), *map(quote, sources)]), encoding="utf-8")
    compiled = run([javac, "@" + str(argfile)])
    # Pass Unicode classpath as a structured Windows process argument. The native Java launcher
    # may read @argfiles using the Windows code page rather than javac's UTF-8 handling.
    native_types = run([args.java_home / "bin/java.exe", "-classpath", ";".join(map(str, [classes, *cp])),
                        "dev.mcdn.minecraft.NativeInputBench"]).strip()
    native_world = None
    if args.world_fixture_root:
        native_world = run([args.java_home / "bin/java.exe", "-classpath", ";".join(map(str, [classes, *cp])),
                            "dev.mcdn.minecraft.NativeWorldBench", args.world_fixture_root]).strip()
    report = {"scope": "local bytecode, adapter compile and native Input/Vec2 fixture; no loader or game launch",
              "java": run([args.java_home / "bin/java.exe", "-version"]).strip(),
              "javac": run([javac, "-version"]).strip(),
              "game_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(), "methods": evidence,
              "adapter_compile": "PASS", "compiler_output": compiled, "native_types_fixture": native_types,
              "native_world_fixture": native_world,
              "adapter_sha256": hashlib.sha256((ROOT / "src/minecraft/java/dev/mcdn/minecraft/BridgeClientInput.java").read_bytes()).hexdigest()}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MC_API_COMPILE_PASS", output / "report.json")
    print(native_types)
    if native_world: print(native_world)


if __name__ == "__main__": main()
