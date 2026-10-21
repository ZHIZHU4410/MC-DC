"""Read only the named installations; write fingerprints into this project's artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": h.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc-version-dir", required=True, type=Path)
    parser.add_argument("--coremod-dir", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    folder = args.mc_version_dir.resolve()
    meta_path = folder / (folder.name + ".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    jar = folder / (folder.name + ".jar")
    java = subprocess.run(["java", "-version"], capture_output=True, text=True, errors="replace", timeout=10)
    loader_jars = []
    for library in meta.get("libraries", []):
        if library["name"].startswith("net.fabricmc:"):
            group, artifact, version = library["name"].split(":")[:3]
            library_path = folder.parent.parent / "libraries" / group.replace(".", "/") / artifact / version / (artifact + "-" + version + ".jar")
            loader_jars.append(fingerprint(library_path) if library_path.exists()
                               else {"library": library["name"], "fingerprint": "not located"})
    class_sample = None
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if name.endswith(".class") and not name.startswith("META-INF/"):
                with archive.open(name) as stream:
                    header = stream.read(8)
                magic, minor, major = struct.unpack(">IHH", header)
                if magic != 0xCAFEBABE:
                    raise ValueError("invalid class file")
                class_sample = {"entry": name, "class_major": major, "java_release": major - 44}
                break
    report = {
        "scope": "local files only; not loaded-runtime identity or adapter compatibility proof",
        "minecraft": {"id": meta.get("id"), "mainClass": meta.get("mainClass"),
                      "javaVersion": meta.get("javaVersion"), "version_json": fingerprint(meta_path),
                      "game_jar": fingerprint(jar), "class_sample": class_sample,
                      "loader_libraries": [v["name"] for v in meta.get("libraries", [])
                                           if v["name"].startswith("net.fabricmc:")],
                      "loader_jars": loader_jars,
                      "mod_jars": [fingerprint(p) for p in sorted((folder / "mods").glob("*.jar"))]},
        "dccm": {"version": (args.coremod_dir / "ModCoreVersion.txt").read_text().strip(),
                 "assemblies": [fingerprint(args.coremod_dir / name) for name in
                                ("core/host/ModCore.dll", "core/host/ModCore.Common.dll", "cache/GameProxy.dll")]},
        "java_on_path": (java.stdout + java.stderr).strip(),
        "gaps": ["Java on PATH is not the launcher's runtime identity",
                 "No matching MC game adapter has been built or loaded",
                 "No DC hook/MDK binding or actual loaded assembly verification",
                 "No saves/configuration have been changed"]}
    output = ROOT / "artifacts" / "environment.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
