using System.Buffers.Binary;
using System.Security.Cryptography;

namespace Mcdn.Protocol;

// A complete immutable collision blob. WORLD_* control transport is a separate layer.
public sealed class World
{
    public const int HeaderBytes = 96, ShapeBytes = 64, MaxShapes = 4096;
    public sealed record Box(ulong Id, double MinX, double MinY, double MinZ, double MaxX, double MaxY, double MaxZ);
    private readonly byte[] data;
    public Guid Session { get; }
    public ulong Epoch { get; }
    public ulong Revision { get; }
    public IReadOnlyList<Box> Boxes { get; }
    public string Digest => Convert.ToHexStringLower(SHA256.HashData(data));
    private World(byte[] data, Guid session, ulong epoch, ulong revision, Box[] boxes)
    { this.data = data; Session = session; Epoch = epoch; Revision = revision; Boxes = Array.AsReadOnly(boxes); }
    public byte[] Encode() => (byte[])data.Clone();
    public static World Create(Guid session, ulong epoch, ulong revision, IEnumerable<Box> boxes)
    {
        // Bound enumeration too: do not materialize unbounded exporter output.
        Box[] shapes = boxes.Take(MaxShapes + 1).ToArray();
        if (shapes.Length > MaxShapes) throw new InvalidDataException("world shape limit");
        byte[] packet = new byte[HeaderBytes + shapes.Length * ShapeBytes];
        var b = packet.AsSpan(); "MCDW"u8.CopyTo(b);
        BinaryPrimitives.WriteUInt16LittleEndian(b[6..], 1);
        BinaryPrimitives.WriteUInt32LittleEndian(b[8..], HeaderBytes);
        BinaryPrimitives.WriteUInt32LittleEndian(b[12..], (uint)shapes.Length);
        session.TryWriteBytes(b[16..32], true, out _);
        BinaryPrimitives.WriteUInt64LittleEndian(b[32..], epoch);
        BinaryPrimitives.WriteUInt64LittleEndian(b[40..], revision);
        BinaryPrimitives.WriteUInt32LittleEndian(b[48..], ShapeBytes);
        for (int i = 0; i < shapes.Length; i++)
        {
            var s = shapes[i]; var r = b[(HeaderBytes + i * ShapeBytes)..];
            BinaryPrimitives.WriteUInt64LittleEndian(r, s.Id);
            double[] values = [s.MinX, s.MinY, s.MinZ, s.MaxX, s.MaxY, s.MaxZ];
            for (int n = 0; n < values.Length; n++) BinaryPrimitives.WriteDoubleLittleEndian(r[(8 + n * 8)..], values[n]);
            BinaryPrimitives.WriteUInt32LittleEndian(r[56..], 1); // solid only; one-way not silently solidified
        }
        SHA256.HashData(b[HeaderBytes..]).CopyTo(b[56..88]);
        return Decode(packet);
    }
    public static World Decode(ReadOnlySpan<byte> packet)
    {
        if (packet.Length < HeaderBytes || packet.Length > HeaderBytes + ShapeBytes * MaxShapes)
            throw new InvalidDataException("world size");
        var b = packet;
        uint count = BinaryPrimitives.ReadUInt32LittleEndian(b[12..]);
        if (!b[..4].SequenceEqual("MCDW"u8) || BinaryPrimitives.ReadUInt16LittleEndian(b[4..]) != 0 ||
            BinaryPrimitives.ReadUInt16LittleEndian(b[6..]) != 1 || BinaryPrimitives.ReadUInt32LittleEndian(b[8..]) != HeaderBytes ||
            count > MaxShapes || b.Length != HeaderBytes + count * ShapeBytes || BinaryPrimitives.ReadUInt32LittleEndian(b[48..]) != ShapeBytes ||
            BinaryPrimitives.ReadUInt32LittleEndian(b[52..]) != 0 || BinaryPrimitives.ReadUInt64LittleEndian(b[88..]) != 0)
            throw new InvalidDataException("world layout");
        ulong epoch = BinaryPrimitives.ReadUInt64LittleEndian(b[32..]), revision = BinaryPrimitives.ReadUInt64LittleEndian(b[40..]);
        if (epoch == 0 || revision == 0 || !CryptographicOperations.FixedTimeEquals(SHA256.HashData(b[HeaderBytes..]), b[56..88]))
            throw new InvalidDataException("world context/hash");
        var shapes = new Box[count]; var ids = new HashSet<ulong>();
        for (int i = 0; i < shapes.Length; i++)
        {
            var r = b[(HeaderBytes + i * ShapeBytes)..]; ulong id = BinaryPrimitives.ReadUInt64LittleEndian(r);
            double[] v = new double[6];
            for (int n = 0; n < 6; n++) v[n] = BinaryPrimitives.ReadDoubleLittleEndian(r[(8 + n * 8)..]);
            if (id == 0 || !ids.Add(id) || v.Any(x => !double.IsFinite(x) || Math.Abs(x) > 1_000_000) ||
                v[0] >= v[3] || v[1] >= v[4] || v[2] >= v[5] || BinaryPrimitives.ReadUInt32LittleEndian(r[56..]) != 1 ||
                BinaryPrimitives.ReadUInt32LittleEndian(r[60..]) != 0) throw new InvalidDataException("world shape");
            shapes[i] = new(id, v[0], v[1], v[2], v[3], v[4], v[5]);
        }
        return new(packet.ToArray(), new Guid(b[16..32], true), epoch, revision, shapes);
    }
    // DC qY points down; all bounds remain fractional. Depth is explicit MC block space.
    public static Box FromDc(ulong id, double left, double top, double right, double bottom,
        double dcX, double dcY, double mcX, double mcY, double scale, double minZ, double maxZ)
    {
        double[] values = [left, top, right, bottom, dcX, dcY, mcX, mcY, scale, minZ, maxZ];
        if (values.Any(x => !double.IsFinite(x)) || scale <= 0 || left >= right || top >= bottom || minZ >= maxZ)
            throw new InvalidDataException("DC transform");
        return new(id, mcX + scale * (left - dcX), mcY - scale * (bottom - dcY), minZ,
            mcX + scale * (right - dcX), mcY - scale * (top - dcY), maxZ);
    }
}
