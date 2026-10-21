package dev.mcdn.protocol;

import java.nio.*;
import java.util.UUID;
import java.util.zip.CRC32;

/** Immutable full-scene diagnostic. Deliberately incompatible with MCDF player frames. */
public final class WorldColorFrame {
    public static final int HEADER_BYTES=384,MAX_PIXELS=1024*1024*4;
    private final byte[] bytes;
    private final ByteBuffer b;
    private WorldColorFrame(byte[] value){bytes=value;b=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);}
    public byte[] encode(){return bytes.clone();}
    public byte[] pixels(){return java.util.Arrays.copyOfRange(bytes,HEADER_BYTES,bytes.length);}
    public UUID session(){var n=ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN);return new UUID(n.getLong(16),n.getLong(24));}
    public long streamEpoch(){return b.getLong(32);}
    public long frameId(){return b.getLong(56);}
    public long nativeTick(){return b.getLong(64);}
    public long readyQpc(){return b.getLong(304);}
    public int width(){return b.getInt(80);}
    public int height(){return b.getInt(84);}
    public static WorldColorFrame decode(byte[] packet){
        if(packet.length<HEADER_BYTES||packet.length>HEADER_BYTES+MAX_PIXELS)throw new IllegalArgumentException("world-color size");
        var f=new WorldColorFrame(packet.clone());var b=f.b;
        if(b.getInt(0)!=0x4357434d||b.getShort(4)!=0||b.getShort(6)!=1||b.getInt(8)!=HEADER_BYTES)throw new IllegalArgumentException("world-color header");
        int w=f.width(),h=f.height();
        if(w<1||w>1024||h<1||h>1024||b.getInt(88)!=w*4||b.getInt(12)!=w*h*4||packet.length!=HEADER_BYTES+w*h*4)throw new IllegalArgumentException("world-color dimensions");
        if(f.session().equals(new UUID(0,0))||f.streamEpoch()==0||f.frameId()==0||b.getLong(40)!=0||b.getLong(48)!=0||b.getInt(92)!=1||b.getInt(96)!=7||b.getInt(100)<0||b.getInt(100)>2||b.getInt(172)!=0)throw new IllegalArgumentException("world-color scope/identity");
        int sw=b.getInt(104),sh=b.getInt(108);
        if(sw<1||sh<1||(long)sw*sh>3840L*2160||w>sw||h>sh)throw new IllegalArgumentException("world-color source bounds");
        for(int o=112;o<160;o+=8)if(!Double.isFinite(b.getDouble(o)))throw new IllegalArgumentException("world-color pose");
        for(int o=160;o<=168;o+=4)if(!Float.isFinite(b.getFloat(o)))throw new IllegalArgumentException("world-color angles");
        if(b.getFloat(168)<0||b.getFloat(168)>1)throw new IllegalArgumentException("world-color partial tick");
        for(int start:new int[]{176,240}){boolean nonzero=false;for(int o=start;o<start+64;o+=4){float v=b.getFloat(o);if(!Float.isFinite(v))throw new IllegalArgumentException("world-color matrix");nonzero|=v!=0;}if(!nonzero)throw new IllegalArgumentException("world-color zero matrix");}
        if(b.getLong(72)<=0||f.readyQpc()<b.getLong(72)||b.getLong(312)<=0)throw new IllegalArgumentException("world-color clock");
        for(int o=324;o<HEADER_BYTES;o++)if(bytesAt(packet,o)!=0)throw new IllegalArgumentException("world-color reserved");
        var crc=new CRC32();crc.update(f.bytes,HEADER_BYTES,f.bytes.length-HEADER_BYTES);
        if(crc.getValue()!=Integer.toUnsignedLong(b.getInt(320)))throw new IllegalArgumentException("world-color CRC");
        return f;
    }
    private static byte bytesAt(byte[] p,int o){return p[o];}
}
