using System.Security.Cryptography;
using System.Text.Json;
using Mono.Cecil;

// Metadata only. Never load GameProxy into the CLR, initialize the VM, or execute native rendering.
try
{
    string source=Path.GetFullPath(args[0]);using var asm=AssemblyDefinition.ReadAssembly(source);
    string[] names=["h3d.mat.Texture","h3d.mat._Texture","h2d.Tile","h2d._Tile","h2d.Bitmap","h2d.Object","h2d.Scene","hxd.Pixels","hxd._Pixels_","hxd.PixelFormat","hxd._PixelFormat","haxe.io.Bytes","haxe.io._Bytes","dc.Game","dc.pr.Game","dc.pr._Game","dc.ui.HUD","dc.libs.Process","en.Hero","Entity","Controller","hxd.Key","tool.Controller","hxd.Event","hxd.EventKind","hxd.Window","h2d.col.Point","dc.level.LevelDisp","dc.libs.tilemap.Parser","dc.level.Room","dc.level.DecoFlag","dc.level.ColType","dc.light.LightedLayers"];
    IEnumerable<TypeDefinition> Flatten(IEnumerable<TypeDefinition> types){foreach(var type in types){yield return type;foreach(var nested in Flatten(type.NestedTypes))yield return nested;}}
    var types=Flatten(asm.MainModule.Types).ToList();var selected=types.Where(type=>names.Any(name=>type.FullName==name||type.FullName.EndsWith("."+name,StringComparison.Ordinal))||type.DeclaringType?.FullName=="dc.hxd.PixelFormat"||type.FullName=="dc.pr.Level"||type.FullName=="dc.level.LevelMap").ToList();
    var report=new{
        scope="installed GameProxy metadata signatures only; no VM, texture upload, game render or runtime verification",
        assembly=source,sha256=Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(source))),
        types=selected.Select(type=>new{name=type.FullName,baseType=type.BaseType?.FullName,
            methods=type.Methods.Where(m=>m.IsPublic).Select(m=>m.FullName).ToArray(),
            properties=type.Properties.Select(p=>new{name=p.Name,type=p.PropertyType.FullName}).ToArray(),
            fields=type.Fields.Where(f=>f.IsPublic).Select(f=>new{name=f.Name,type=f.FieldType.FullName}).ToArray()}).ToArray(),
        candidateTypes=selected.Count==0?types.Where(t=>t.FullName.Contains("Texture",StringComparison.Ordinal)||t.FullName.Contains("Pixels",StringComparison.Ordinal)||t.FullName.Contains("Bitmap",StringComparison.Ordinal)).Select(t=>t.FullName).Take(60).ToArray():[]
    };
    string dest=Path.GetFullPath(args[1]);Directory.CreateDirectory(Path.GetDirectoryName(dest)!);File.WriteAllText(dest,JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
    Console.WriteLine($"DC_RENDER_SYMBOLS_READ {selected.Count} native binding types; no game calls");
}
catch(Exception ex){Console.Error.WriteLine("DC_RENDER_SYMBOLS_FAIL "+ex.Message);Environment.ExitCode=2;}
