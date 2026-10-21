using System.Buffers.Binary;

namespace Mcdn.Protocol;

// Immutable local snapshot. Shared-memory publication/locking is deliberately outside this codec.
public sealed class Frame
{
    private readonly byte[] bytes;
    public const int HeaderBytes = 256, MaxDimension = 1024;
    private Frame(byte[] bytes) { this.bytes = bytes; }
    public byte[] Encode() => (byte[])bytes.Clone();
    public Guid Session => new(bytes.AsSpan(16, 16), bigEndian: true);
    public ulong WorldEpoch => U64(32);
    public ulong ModeEpoch => U64(40);
    public ulong WorldRevision => U64(48);
    public ulong FrameId => U64(56);
    public ulong NativeTick => U64(64);
    public ulong ConsumedInputSeq => U64(72);
    public double FootX => F64(112);
    public double FootY => F64(120);
    public double FootZ => F64(128);
    public ulong CameraEpoch => U64(240);
    private uint U32(int offset) => BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(offset));
    private ulong U64(int offset) => BinaryPrimitives.ReadUInt64LittleEndian(bytes.AsSpan(offset));
    private double F64(int offset) => BitConverter.UInt64BitsToDouble(U64(offset));
    private float F32(int offset) => BitConverter.UInt32BitsToSingle(U32(offset));

    public static Frame Decode(ReadOnlySpan<byte> packet)
    {
        // Bound size before allocating a private copy.
        if (packet.Length < HeaderBytes || packet.Length > HeaderBytes + MaxDimension * MaxDimension * 4)
            throw new InvalidDataException("frame size");
        var f = new Frame(packet.ToArray());
        if (!packet[..4].SequenceEqual("MCDF"u8) || BinaryPrimitives.ReadUInt16LittleEndian(packet[4..]) != 0 ||
            BinaryPrimitives.ReadUInt16LittleEndian(packet[6..]) != 1 || f.U32(8) != HeaderBytes)
            throw new InvalidDataException("frame header/version");
        uint w = f.U32(80), h = f.U32(84);
        if (w is 0 or > MaxDimension || h is 0 or > MaxDimension || f.U32(88) != w * 4 ||
            f.U32(12) != w * h * 4 || packet.Length != HeaderBytes + w * h * 4)
            throw new InvalidDataException("frame dimensions/stride");
        if (f.U32(92) != 1 || f.U32(96) is 0 or > 3 || f.U32(100) > 1 || f.U32(104) > 1 ||
            f.U32(108) != 0 || f.U64(248) != 0 || f.U64(224) == 0)
            throw new InvalidDataException("frame format/flags/reserved/clock");
        for (int o = 112; o <= 152; o += 8)
            if (!double.IsFinite(f.F64(o))) throw new InvalidDataException("frame pose");
        for (int o = 160; o <= 172; o += 4)
            if (!float.IsFinite(f.F32(o))) throw new InvalidDataException("frame angles/pivot");
        if (!double.IsFinite(f.F64(176)) || f.F64(176) <= 0 || !double.IsFinite(f.F64(184)) || f.F64(184) <= 0 ||
            f.F32(168) is < 0 or > 1 || f.F32(172) is < 0 or > 1)
            throw new InvalidDataException("frame scale/pivot");
        if (Crc32(packet[HeaderBytes..]) != f.U32(236)) throw new InvalidDataException("pixel crc");
        return f;
    }

    public bool Matches(Guid session, ulong world, ulong mode, ulong revision, ulong camera) =>
        Session == session && WorldEpoch == world && ModeEpoch == mode && WorldRevision == revision && CameraEpoch == camera;

    private static uint Crc32(ReadOnlySpan<byte> data)
    {
        uint crc = uint.MaxValue;
        foreach (byte value in data)
        {
            crc ^= value;
            for (int bit = 0; bit < 8; bit++) crc = (crc >> 1) ^ ((crc & 1) == 0 ? 0 : 0xedb88320u);
        }
        return ~crc;
    }
}
