using Mono.Cecil;

try
{
    if(args.Length!=2)throw new ArgumentException("source and destination required");
    string source=Path.GetFullPath(args[0]),dest=Path.GetFullPath(args[1]);
    if(source.Equals(dest,StringComparison.OrdinalIgnoreCase))throw new ArgumentException("source is read-only");
    using var asm=AssemblyDefinition.ReadAssembly(source);
    var legacy=asm.MainModule.AssemblyReferences.Single(r=>r.Name=="mscorlib");
    var runtime=asm.MainModule.AssemblyReferences.SingleOrDefault(r=>r.Name=="System.Private.CoreLib");
    if(runtime!=null)
    {
        // Same reference-only retargeting as DCCM's GenerateGamePersudoCommand cleanup.
        runtime.Name=legacy.Name;runtime.Version=legacy.Version;runtime.Culture=legacy.Culture;
        runtime.Attributes=legacy.Attributes;runtime.PublicKeyToken=legacy.PublicKeyToken;runtime.PublicKey=legacy.PublicKey;
        runtime.Hash=legacy.Hash;runtime.HashAlgorithm=legacy.HashAlgorithm;
    }
    Directory.CreateDirectory(Path.GetDirectoryName(dest)!);asm.Write(dest);
    Console.WriteLine("GAME_PROXY_COMPILE_REF_PASS private copy; runtime original unchanged");
}
catch(Exception ex){Console.Error.WriteLine($"REFERENCE_BUILD_FAIL {ex.GetType().Name}: {ex.Message}");Environment.ExitCode=1;}
