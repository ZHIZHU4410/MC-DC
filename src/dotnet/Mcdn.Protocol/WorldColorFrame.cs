using System.Buffers.Binary;

namespace Mcdn.Protocol;

// Immutable MCWC full-scene diagnostic. Never accepted as an MCDF/MODE ready frame.
public sealed class WorldColorFrame
{
    public const int HeaderBytes=384,MaximumPixels=1024*1024*4;
    private readonly byte[] bytes;
    private WorldColorFrame(byte[] packet){bytes=packet;}
    private uint U32(int o)=>BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(o));
    private ulong U64(int o)=>BinaryPrimitives.ReadUInt64LittleEndian(bytes.AsSpan(o));
    private float F32(int o)=>BitConverter.UInt32BitsToSingle(U32(o));
    public Guid Session=>new(bytes.AsSpan(16,16),bigEndian:true);
    public ulong StreamEpoch=>U64(32);
    public ulong FrameId=>U64(56);
    public ulong NativeTick=>U64(64);
    public ulong ReadyQpc=>U64(304);
    public ulong Frequency=>U64(312);
    public int Width=>(int)U32(80);
    public int Height=>(int)U32(84);
    public byte[] Encode()=>(byte[])bytes.Clone();
    public byte[] Pixels()=>bytes.AsSpan(HeaderBytes).ToArray();
    public static WorldColorFrame Decode(ReadOnlySpan<byte> packet)
    {
        if(packet.Length<HeaderBytes||packet.Length>HeaderBytes+MaximumPixels)throw new InvalidDataException("world-color size");
        var f=new WorldColorFrame(packet.ToArray());
        if(!packet[..4].SequenceEqual("MCWC"u8)||BinaryPrimitives.ReadUInt16LittleEndian(packet[4..])!=0||BinaryPrimitives.ReadUInt16LittleEndian(packet[6..])!=1||f.U32(8)!=HeaderBytes)throw new InvalidDataException("world-color header");
        uint w=f.U32(80),h=f.U32(84);
        if(w is <1 or >1024||h is <1 or >1024||f.U32(88)!=w*4||f.U32(12)!=w*h*4||packet.Length!=HeaderBytes+w*h*4)throw new InvalidDataException("world-color dimensions");
        if(f.Session==Guid.Empty||f.StreamEpoch==0||f.FrameId==0||f.U64(40)!=0||f.U64(48)!=0||f.U32(92)!=1||f.U32(96)!=7||f.U32(100)>2||f.U32(172)!=0)throw new InvalidDataException("world-color scope/identity");
        uint sw=f.U32(104),sh=f.U32(108);
        if(sw<1||sh<1||(ulong)sw*sh>3840UL*2160||w>sw||h>sh)throw new InvalidDataException("world-color source bounds");
        for(int o=112;o<160;o+=8)if(!double.IsFinite(BitConverter.UInt64BitsToDouble(f.U64(o))))throw new InvalidDataException("world-color pose");
        for(int o=160;o<=168;o+=4)if(!float.IsFinite(f.F32(o)))throw new InvalidDataException("world-color angles");
        if(f.F32(168) is <0 or >1)throw new InvalidDataException("world-color partial tick");
        foreach(int start in new[]{176,240}){bool nonzero=false;for(int o=start;o<start+64;o+=4){float v=f.F32(o);if(!float.IsFinite(v))throw new InvalidDataException("world-color matrix");nonzero|=v!=0;}if(!nonzero)throw new InvalidDataException("world-color zero matrix");}
        if(f.U64(72)==0||f.U64(72)>long.MaxValue||f.ReadyQpc<f.U64(72)||f.ReadyQpc>long.MaxValue||f.Frequency==0||f.Frequency>long.MaxValue)throw new InvalidDataException("world-color clock");
        for(int o=324;o<HeaderBytes;o++)if(packet[o]!=0)throw new InvalidDataException("world-color reserved");
        uint crc=uint.MaxValue;foreach(byte value in packet[HeaderBytes..]){crc^=value;for(int bit=0;bit<8;bit++)crc=(crc>>1)^((crc&1)==0?0:0xedb88320u);}
        if(~crc!=f.U32(320))throw new InvalidDataException("world-color CRC");
        return f;
    }
}
