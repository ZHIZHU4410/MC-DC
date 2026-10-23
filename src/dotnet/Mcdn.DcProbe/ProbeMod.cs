using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading.Channels;
using Mcdn.Protocol;
using ModCore.Mods;
using ModCore.Events.Interfaces.Game;
using ModCore.Events.Interfaces.Game.Hero;

namespace Mcdn.DcProbe;

// Capture is read-only. The explicitly isolated DC lab additionally redirects saves and blocks Cloud.
public sealed class ProbeMod(ModInfo info) : ModBase(info), IOnHeroInit, IOnHeroDispose, IOnHeroUpdate, IOnGameExit
{
    private sealed record Capture(ulong Epoch, int MapUid, int MapWidth, int MapHeight, int X, int Y, int Width, int Height,
        int[] Cells, int[]? DecoFlags, int[]? RoomCells, double AnchorX, double AnchorY, double HeroX, double HeroY);
    private readonly Channel<Capture> captures = Channel.CreateBounded<Capture>(new BoundedChannelOptions(1)
        { FullMode = BoundedChannelFullMode.DropOldest, SingleWriter = true, SingleReader = true });
    private readonly Guid session = Guid.NewGuid();
    private string? output;
    private ulong epoch;
    private int mapUid;
    private nint collisionPointer;
    private double anchorX, anchorY;
    private long next;
    private bool spatialWarningLogged;
    private Task? writer;
    private double mcOriginX,mcOriginY,mcOriginZ;
    internal static bool IsInitialized { get; private set; }
    public override void Initialize()
    {
        if(Environment.GetEnvironmentVariable("MCDN_DC_ISOLATED_LAB")=="1"&&!LabSaveGuard.IsInstalled)
        { Logger.Error("MCDN DC lab refused: independent startup guard missing");Environment.Exit(2); }
        var root = Environment.GetEnvironmentVariable("MCDN_LAB_ROOT");
        if (string.IsNullOrWhiteSpace(root)) { Logger.Information("MCDN probe disabled: set MCDN_LAB_ROOT to an isolated lab directory"); return; }
        bool Origin(string axis,out double value) => double.TryParse(Environment.GetEnvironmentVariable("MCDN_MC_ORIGIN_"+axis)??"0",NumberStyles.Float,CultureInfo.InvariantCulture,out value)&&double.IsFinite(value)&&Math.Abs(value)<999000;
        if(!Origin("X",out mcOriginX)||!Origin("Y",out mcOriginY)||!Origin("Z",out mcOriginZ)) { Logger.Error("MCDN probe disabled: invalid fixed MC origin");return; }
        output = Path.Combine(Path.GetFullPath(root), "dc-probe", session.ToString("N"));
        Directory.CreateDirectory(output); writer = Task.Run(WriteLoop);
        Logger.Information("MCDN read-only probe {Session} -> {Output}", session, output);
        IsInitialized=true;
    }
    void IOnHeroInit.OnHeroInit() { checked { epoch++; } mapUid = 0; collisionPointer = 0; }
    void IOnHeroDispose.OnHeroDispose() { checked { epoch++; } mapUid = 0; collisionPointer = 0; }
    void IOnHeroUpdate.OnHeroUpdate(double dt)
    {
        if (output == null || writer?.IsCompleted == true || Stopwatch.GetTimestamp() < next) return;
        next = Stopwatch.GetTimestamp() + Stopwatch.Frequency / 10;
        try
        {
            var hero = ModCore.Modules.Game.Instance.HeroInstance;
            if (hero == null || hero.destroyed || hero._level == null) return;
            var map = hero._level.map;
            int wid = map.wid, hei = map.hei;
            if (wid <= 0 || hei <= 0 || (long)wid * hei > 10_000_000 || map.collisions.length < (long)wid * hei || map.collisions.bytes == 0) return;
            if (mapUid != map.__uid || collisionPointer != map.collisions.bytes)
            {
                checked { epoch++; } mapUid = map.__uid; collisionPointer = map.collisions.bytes;
                anchorX = hero.cx + hero.xr; anchorY = hero.cy + hero.yr;
            }
            int x = Math.Clamp(hero.cx - 32, 0, Math.Max(0, wid - 64)), y = Math.Clamp(hero.cy - 24, 0, Math.Max(0, hei - 48));
            int w = Math.Min(64, wid - x), h = Math.Min(48, hei - y); var cells = new int[w * h];
            for (int row = 0; row < h; row++) Marshal.Copy(map.collisions.bytes + checked(((y+row)*wid+x)*4), cells, row*w, w);
            int[]? decoFlags = null, roomCells = null;
            // These are DC's own spatial labels, not rendered decoration sprites or interpreted door semantics.
            try
            {
                var deco = map.decoGrid; var rooms = map.cellToRoom;
                if (deco != null && rooms != null && deco.bytes != 0 && rooms.bytes != 0 &&
                    deco.length >= (long)wid * hei && rooms.length >= (long)wid * hei)
                {
                    decoFlags = new int[w*h]; roomCells = new int[w*h];
                    for (int row = 0; row < h; row++)
                    {
                        int offset = checked(((y+row)*wid+x)*4);
                        Marshal.Copy(deco.bytes + offset, decoFlags, row*w, w);
                        Marshal.Copy(rooms.bytes + offset, roomCells, row*w, w);
                    }
                }
            }
            catch (Exception ex)
            {
                if (!spatialWarningLogged) { Logger.Warning("MCDN optional spatial layers unavailable: {Message}",ex.Message);spatialWarningLogged=true; }
                decoFlags=null;roomCells=null;
            }
            captures.Writer.TryWrite(new(epoch, mapUid, wid, hei, x, y, w, h, cells, decoFlags, roomCells,
                anchorX, anchorY, hero.cx+hero.xr, hero.cy+hero.yr));
        }
        catch (Exception ex) { Logger.Warning("MCDN capture refused: {Message}", ex.Message); }
    }
    private async Task WriteLoop()
    {
        ulong previousEpoch = 0, revision = 0; string? previousHash = null;
        try
        {
            await foreach (var capture in captures.Reader.ReadAllAsync())
            {
                byte[]? layout = null;
                if (capture.DecoFlags != null && capture.RoomCells != null)
                {
                    using var stream = new MemoryStream();
                    using (var writer = new BinaryWriter(stream, System.Text.Encoding.ASCII, leaveOpen:true))
                    {
                        writer.Write(System.Text.Encoding.ASCII.GetBytes("MCDL"));writer.Write(1);
                        foreach (int value in new[]{capture.MapUid,capture.MapWidth,capture.MapHeight,capture.X,capture.Y,capture.Width,capture.Height}) writer.Write(value);
                        foreach (var grid in new[]{capture.Cells,capture.DecoFlags,capture.RoomCells})
                            foreach (int value in grid) writer.Write(value);
                    }
                    layout=stream.ToArray();
                }
                var raw = MemoryMarshal.AsBytes(capture.Cells.AsSpan()).ToArray();
                string hash = Convert.ToHexStringLower(SHA256.HashData(layout ?? raw)) + $":{capture.X}:{capture.Y}:{capture.MapUid}";
                if (previousEpoch == capture.Epoch && previousHash == hash) continue;
                if (previousEpoch != capture.Epoch) revision = 0;
                revision++; previousEpoch = capture.Epoch; previousHash = hash;
                var boxes = new List<World.Box>(); var histogram = new Dictionary<int,int>(); int unsupported = 0;
                for (int row=0; row<capture.Height; row++) for(int col=0; col<capture.Width; col++)
                {
                    int cell = capture.Cells[row*capture.Width+col]; histogram[cell] = histogram.GetValueOrDefault(cell)+1;
                    int x = capture.X+col, y = capture.Y+row;
                    if (cell is 3 or 35) // local ColType.Plain/Invisible exact encodings; NOT a generic bit-1 test
                        boxes.Add(World.FromDc(((ulong)(uint)y<<32)+(uint)x+1, x,y,x+1,y+1,capture.AnchorX,capture.AnchorY,mcOriginX,mcOriginY,1,mcOriginZ-2,mcOriginZ+2));
                    else if (cell != 0) unsupported++;
                }
                var world = World.Create(session,capture.Epoch,revision,boxes); string name=$"world-{capture.Epoch}-{revision}.mcdw";
                await File.WriteAllBytesAsync(Path.Combine(output!,name), world.Encode());
                string? layoutName = null, layoutDigest = null;
                if (layout != null)
                {
                    layoutName = $"layout-{capture.Epoch}-{revision}.mcdl";
                    layoutDigest = Convert.ToHexStringLower(SHA256.HashData(layout));
                    await File.WriteAllBytesAsync(Path.Combine(output!,layoutName),layout);
                }
                // Immutable blob first; pointer/metadata last. A reader must validate its digest.
                var metadata = new { kind="read-only-dc-probe", session, worldEpoch=capture.Epoch.ToString(), revision=revision.ToString(),
                    file=name, digest=world.Digest, capture.MapUid,capture.MapWidth,capture.MapHeight,
                    capture.X,capture.Y,capture.Width,capture.Height, layoutFile=layoutName,layoutDigest,
                    spatialLayersAvailable=layout!=null,
                    capture.AnchorX,capture.AnchorY,capture.HeroX,capture.HeroY, histogram, unsupportedCells=unsupported,
                    mcOriginX,mcOriginY,mcOriginZ,
                    eligibleForControl=false, note="diagnostic solid subset; one-way/roll/ladder/slope and full world safety not implemented" };
                string temporary=Path.Combine(output!,"latest.json.tmp");
                await File.WriteAllTextAsync(temporary,JsonSerializer.Serialize(metadata,new JsonSerializerOptions{WriteIndented=true}));
                File.Move(temporary,Path.Combine(output!,"latest.json"),true);
            }
        }
        catch(Exception ex) { Logger.Error("MCDN export worker stopped: {Message}",ex.Message); }
    }
    void IOnGameExit.OnGameExit() { captures.Writer.TryComplete(); } // do not wait on disk from the game thread
}
