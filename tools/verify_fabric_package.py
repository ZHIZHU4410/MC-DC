"""Reject ordinary classes in Mixin's reserved package before installing an archive."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile


def verify(path):
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("corrupt probe archive")
        names = set(archive.namelist())
        mod = json.loads(archive.read("fabric.mod.json"))
        for config in mod["mixins"]:
            mixin = json.loads(archive.read(config))
            prefix = mixin["package"].replace(".", "/") + "/"
            declared = {prefix + name.replace(".", "/") for kind in ["mixins", "client", "server"] for name in mixin.get(kind, [])}
            if not declared or any(name + ".class" not in names for name in declared):
                raise ValueError("missing declared Mixin class")
            for name in names:
                if name.startswith(prefix) and name.endswith(".class") and name[:-6].split("$")[0] not in declared:
                    raise ValueError("ordinary class in reserved Mixin package: " + name)
            for entries in mod.get("entrypoints", {}).values():
                for entry in entries:
                    value = entry if isinstance(entry, str) else entry["value"]
                    value = value.split("::", 1)[0].replace(".", "/")
                    if value.startswith(prefix):
                        raise ValueError("entrypoint in reserved Mixin package: " + value)
                    if value + ".class" not in names:
                        raise ValueError("missing entrypoint class: " + value)
    return "FABRIC_PACKAGE_PASS entrypoints/helpers outside reserved Mixin package; declared hooks present"


if __name__ == "__main__":
    print(verify(Path(sys.argv[1])))
