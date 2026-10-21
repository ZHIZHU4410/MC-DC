using ModCore.Storage;
using ModCore.Utilities;
using dc.steam;
using dc.tool;
using Path = System.IO.Path;

namespace Mcdn.DcProbe;

// Only enabled in the separately marked disposable DC runtime. Not part of the production bridge.
internal static class LabSaveGuard
{
    private static string? save;
    private static bool installed;
    internal static bool IsInstalled => installed;
    internal static string Install(string root)
    {
        if (installed) return save!;
        string game = Path.GetFullPath(Path.Combine(root, "dc-game"));
        save = Path.Combine(game, "save");
        if (!System.IO.File.Exists(Path.Combine(game,"MCDN_ISOLATED_DC_LAB")) ||
            !Same(FolderInfo.GameRoot.FullPath,game) || !Same(FolderInfo.SaveRoot.FullPath,save))
            throw new InvalidOperationException("DC lab game/save root or marker mismatch");
        Directory.CreateDirectory(save);
        // Stop cloud access at both the enable checks and every read/write/delete endpoint.
        Hook__Cloud.enable += (_, _) => { };
        Hook__Cloud.isEnabled += _ => false;
        Hook__Cloud.isEnabledForApp += _ => false;
        Hook__Cloud.exists += (_, _) => false;
        Hook__Cloud.read += (_, _) => null!;
        Hook__Cloud.write += (_, _, _) => false;
        Hook__Cloud.delete += (_, _) => false;
        Hook__File.canTransfer += _ => false;
        Hook__File.transferCloudToLocal += _ => false;
        Hook__File.transferLocalToCloud += _ => false;
        Hook__File.getSteamCloudStatus += _ => null;
        Hook__File.saveSteamCloudStatus += _ => { };
        // Reassert the absolute private path at every local save entry, even if vanilla resets PATH.
        Hook__File.exists += (orig,name) => { Local(name); return orig(name); };
        Hook__File.getBytes += (orig,name) => { Local(name); return orig(name); };
        Hook__File.saveBytes += (orig,name,bytes) => { Local(name); orig(name,bytes); };
        Hook__File.delete += (orig,name) => { Local(name); orig(name); };
        Hook__File.listFiles += orig => { Local(); return orig(); };
        Hook__File.dailyBackup += orig => { Local(); orig(); };
        Hook__File.purgeOldBackups += orig => { Local(); orig(); };
        Hook__File.pathToBackupZip += (orig,date,id) => { Local(); return orig(date,id); };
        Local();
        // Actual native dispatch must observe the hooks before the original game entry continues.
        if (Cloud.Class.isEnabled() || Cloud.Class.isEnabledForApp() ||
            dc.tool.File.Class.getSteamCloudStatus() != null || !Same(dc.tool.File.Class.PATH.ToString(),save))
            throw new InvalidOperationException("DC local-save/cloud guard self-check failed");
        string sentinel = "mcdn_guard_"+Guid.NewGuid().ToString("N")+".tmp";
        var nativeName=sentinel.AsHaxeString();
        dc.tool.File.Class.saveBytes(nativeName,dc.haxe.io.Bytes.Class.alloc(0));
        if (!System.IO.File.Exists(Path.Combine(save,sentinel)) || !dc.tool.File.Class.exists(nativeName) ||
            dc.tool.File.Class.getBytes(nativeName).length!=0)
            throw new InvalidOperationException("DC native local save/read probe failed");
        dc.tool.File.Class.delete(nativeName);
        if (System.IO.File.Exists(Path.Combine(save,sentinel)))throw new InvalidOperationException("DC native local delete probe failed");
        installed = true;
        return save;
    }
    private static bool Same(string a,string b) =>
        string.Equals(Path.TrimEndingDirectorySeparator(Path.GetFullPath(a)),Path.TrimEndingDirectorySeparator(Path.GetFullPath(b)),StringComparison.OrdinalIgnoreCase);
    private static void Local(dc.String? name=null)
    {
        if (save == null) throw new InvalidOperationException("DC lab save root absent");
        if (name != null)
        {
            string path = Path.GetFullPath(Path.Combine(save,name.ToString()));
            if (!path.StartsWith(save+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("save filename escapes the DC lab");
        }
        dc.tool.File.Class.PATH = save.AsHaxeString();
    }
}
