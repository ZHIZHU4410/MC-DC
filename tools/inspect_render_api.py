"""Read installed MC render APIs. Keep complete bytecode outside the mod project; never run game main."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CLASSES=["net.minecraft.client.Screenshot","net.minecraft.client.renderer.GameRenderer","net.minecraft.client.Minecraft",
         "com.mojang.blaze3d.pipeline.RenderTarget","com.mojang.blaze3d.systems.RenderSystem",
         "com.mojang.renderpearl.api.commands.CommandEncoder","com.mojang.renderpearl.api.commands.GpuFence",
         "com.mojang.renderpearl.api.device.GpuDevice","com.mojang.renderpearl.api.buffers.GpuBuffer",
         "com.mojang.renderpearl.api.buffers.GpuBufferSlice","com.mojang.renderpearl.api.buffers.GpuBufferSlice$MappedView",
         "com.mojang.renderpearl.api.textures.GpuTexture","com.mojang.renderpearl.api.textures.GpuTexture$Usage",
         "com.mojang.renderpearl.api.buffers.GpuBuffer$Usage","net.minecraft.client.Camera",
         "com.mojang.renderpearl.api.GpuFormat","net.minecraft.client.renderer.state.GameRenderState",
         "net.minecraft.client.renderer.state.level.LevelRenderState","net.minecraft.client.renderer.state.level.CameraRenderState",
         "net.minecraft.client.renderer.state.level.PlayerRenderState","net.minecraft.client.renderer.entity.state.EntityRenderState",
         "com.mojang.blaze3d.platform.NativeImage","com.mojang.renderpearl.frontend.FrontendCommandEncoder",
         "com.mojang.renderpearl.backend.opengl.GlCommandEncoder","com.mojang.blaze3d.pipeline.MainTarget"]


def main():
    p=argparse.ArgumentParser();p.add_argument("--java-home",type=Path,required=True);p.add_argument("--mc-version-dir",type=Path,required=True);p.add_argument("--private-output",type=Path,required=True);a=p.parse_args()
    private=a.private_output.resolve()
    if private==ROOT or ROOT in private.parents:raise ValueError("raw game bytecode must remain outside project")
    private.mkdir(parents=True,exist_ok=True)
    folder=a.mc_version_dir.resolve();jar=folder/(folder.name+".jar")
    def inspect(cls):
        result=subprocess.run([str(a.java_home/"bin/javap.exe"),"-classpath",str(jar),"-p","-c","-s",cls],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="strict",timeout=45)
        if result.returncode:raise RuntimeError(cls+": "+result.stderr)
        raw=result.stdout;path=private/(cls+".txt");path.write_text(raw,encoding="utf-8")
        # Only API signatures/references in the mod report; complete disassembly stays private.
        signatures=re.findall(r"^  (?:public|protected|private).+;$",raw,flags=re.M)
        return cls,{"private_bytecode":str(path),"sha256":hashlib.sha256(raw.encode()).hexdigest(),"signatures":signatures}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:entries=dict(executor.map(inspect,CLASSES))
    output=ROOT/"artifacts/render-api";output.mkdir(parents=True,exist_ok=True)
    (output/"report.json").write_text(json.dumps({"scope":"local bytecode/API only; no GPU or game runtime evidence","game_jar":str(jar),"game_sha256":hashlib.sha256(jar.read_bytes()).hexdigest(),"classes":entries},indent=2),encoding="utf-8")
    print("RENDER_API_READ_PASS",len(entries),"classes; private disassembly outside project")


if __name__=="__main__":main()
