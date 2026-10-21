using System.Globalization;

namespace Mcdn.Protocol;

public static class WorldMessages
{
    private static string N(ulong n) => n.ToString(CultureInfo.InvariantCulture);
    public static byte[] Begin(World world) => Control.Encode(("revision", N(world.Revision)), ("digest", world.Digest), ("totalBytes", world.Encode().Length.ToString(CultureInfo.InvariantCulture)));
    public static byte[] Chunk(ulong revision, int index, ReadOnlySpan<byte> bytes)
    {
        if (revision == 0 || index is < 0 or > 256 || bytes.Length is 0 or > 1024) throw new InvalidDataException("world chunk");
        return Control.Encode(("revision", N(revision)), ("index", index.ToString(CultureInfo.InvariantCulture)), ("data", Convert.ToBase64String(bytes)));
    }
    public static byte[] End(World world) => Control.Encode(("revision", N(world.Revision)), ("digest", world.Digest));
    public static byte[] Prepare(World world, ulong camera, bool carrierPrepared) => Control.Encode(
        ("revision", N(world.Revision)), ("digest", world.Digest), ("cameraEpoch", N(camera)), ("carrierPrepared", carrierPrepared ? "1" : "0"));
    public static byte[] Commit(World world, ulong camera, ulong frame, ulong nativeTick) => Control.Encode(
        ("revision", N(world.Revision)), ("digest", world.Digest), ("cameraEpoch", N(camera)), ("frameId", N(frame)), ("nativeTick", N(nativeTick)));
    public static void Applied(Envelope message, World world, string side)
    {
        var f = Control.Parse(message.Body); Control.Fields(f, "revision", "digest", "side", "tick");
        if (message.Type != 8 || message.Session != world.Session || message.WorldEpoch != world.Epoch || message.ModeEpoch != 0 ||
            Control.U64(f["revision"]) != world.Revision || f["digest"] != world.Digest || f["side"] != side || Control.U64(f["tick"]) == 0)
            throw new InvalidDataException("world applied receipt");
    }
}
