using System.Buffers.Binary;

namespace Mcdn.Protocol;

// Body bytes remain opaque here. A validated message schema/handshake must precede game use.
public sealed record Envelope(ushort Type, Guid Session, ulong WorldEpoch, ulong ModeEpoch,
    ulong Sequence, ulong AckSequence, byte[] Body);

public static class Wire
{
    public const int HeaderBytes = 64, MaxBodyBytes = 1 << 20;

    public static int ValidateHeader(ReadOnlySpan<byte> h)
    {
        if (h.Length < HeaderBytes || !h[..4].SequenceEqual("MCDN"u8))
            throw new InvalidDataException("header/magic");
        if (BinaryPrimitives.ReadUInt16LittleEndian(h[4..]) != 0 ||
            BinaryPrimitives.ReadUInt16LittleEndian(h[6..]) != 1)
            throw new InvalidDataException("version");
        var type = BinaryPrimitives.ReadUInt16LittleEndian(h[8..]);
        if (type is < 1 or > 22 || BinaryPrimitives.ReadUInt16LittleEndian(h[10..]) != 0)
            throw new InvalidDataException("type/flags");
        uint length = BinaryPrimitives.ReadUInt32LittleEndian(h[12..]);
        if (length > MaxBodyBytes) throw new InvalidDataException("body limit");
        return (int)length;
    }

    public static byte[] Encode(Envelope m)
    {
        if (m.Body.Length > MaxBodyBytes) throw new InvalidDataException("body limit");
        byte[] data = new byte[HeaderBytes + m.Body.Length];
        var h = data.AsSpan();
        "MCDN"u8.CopyTo(h);
        BinaryPrimitives.WriteUInt16LittleEndian(h[6..], 1);
        BinaryPrimitives.WriteUInt16LittleEndian(h[8..], m.Type);
        BinaryPrimitives.WriteUInt32LittleEndian(h[12..], (uint)m.Body.Length);
        m.Session.TryWriteBytes(h[16..32], bigEndian: true, out _);
        BinaryPrimitives.WriteUInt64LittleEndian(h[32..], m.WorldEpoch);
        BinaryPrimitives.WriteUInt64LittleEndian(h[40..], m.ModeEpoch);
        BinaryPrimitives.WriteUInt64LittleEndian(h[48..], m.Sequence);
        BinaryPrimitives.WriteUInt64LittleEndian(h[56..], m.AckSequence);
        m.Body.CopyTo(h[64..]);
        ValidateHeader(h);
        return data;
    }

    public static Envelope Decode(ReadOnlySpan<byte> data)
    {
        int length = ValidateHeader(data);
        if (data.Length != HeaderBytes + length) throw new InvalidDataException("packet size");
        return new(BinaryPrimitives.ReadUInt16LittleEndian(data[8..]), new Guid(data[16..32], bigEndian: true),
            BinaryPrimitives.ReadUInt64LittleEndian(data[32..]), BinaryPrimitives.ReadUInt64LittleEndian(data[40..]),
            BinaryPrimitives.ReadUInt64LittleEndian(data[48..]), BinaryPrimitives.ReadUInt64LittleEndian(data[56..]),
            data[64..].ToArray());
    }
}

// One bounded partial packet; delivery is synchronous on the caller (socket worker) thread.
// Any error poisons this connection. Create a new decoder after reconnecting.
public sealed class StreamDecoder
{
    private readonly byte[] buffer = new byte[Wire.HeaderBytes + Wire.MaxBodyBytes];
    private int used, target = Wire.HeaderBytes;
    private bool failed;

    public void Feed(ReadOnlySpan<byte> bytes, Action<Envelope> deliver)
    {
        if (failed) throw new InvalidDataException("decoder failed");
        try
        {
            while (!bytes.IsEmpty)
            {
                int count = Math.Min(target - used, bytes.Length);
                bytes[..count].CopyTo(buffer.AsSpan(used));
                used += count;
                bytes = bytes[count..];
                if (used < target) continue;
                if (target == Wire.HeaderBytes)
                {
                    target += Wire.ValidateHeader(buffer);
                    if (used < target) continue;
                }
                var message = Wire.Decode(buffer.AsSpan(0, target));
                used = 0;
                target = Wire.HeaderBytes;
                deliver(message);
            }
        }
        catch { failed = true; throw; }
    }

    public void Complete()
    {
        if (failed || used != 0) { failed = true; throw new InvalidDataException("truncated/failed stream"); }
    }
}

// Per-direction replay/identity filter. This does not grant control or acknowledge game consumption.
public sealed class ReceiveGate(Guid session, ulong worldEpoch, ulong modeEpoch)
{
    private ulong lastSequence;
    public void Accept(Envelope m)
    {
        if (m.Session != session || m.WorldEpoch != worldEpoch || m.ModeEpoch != modeEpoch ||
            m.Sequence <= lastSequence) throw new InvalidDataException("identity/epoch/sequence");
        lastSequence = m.Sequence;
    }
}
