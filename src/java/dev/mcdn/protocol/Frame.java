package dev.mcdn.protocol;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.UUID;
import java.util.zip.CRC32;

/** Local immutable frame+pose snapshot, not a shared-memory concurrency implementation. */
public final class Frame {
    public static final int HEADER_BYTES = 256, MAX_DIMENSION = 1024;
    private final byte[] bytes;
    private final ByteBuffer b;
    private Frame(byte[] bytes) { this.bytes = bytes; b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN); }
    public byte[] encode() { return bytes.clone(); }
    public UUID session() {
        ByteBuffer network = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN);
        return new UUID(network.getLong(16), network.getLong(24));
    }
    public long worldEpoch() { return b.getLong(32); }
    public long modeEpoch() { return b.getLong(40); }
    public long worldRevision() { return b.getLong(48); }
    public long frameId() { return b.getLong(56); }
    public long nativeTick() { return b.getLong(64); }
    public long consumedInputSeq() { return b.getLong(72); }
    public double footX() { return b.getDouble(112); }
    public double footY() { return b.getDouble(120); }
    public double footZ() { return b.getDouble(128); }
    public long cameraEpoch() { return b.getLong(240); }
    public long readyQpc() { return b.getLong(216); }
    public long qpcFrequency() { return b.getLong(224); }
    public static Frame decode(byte[] packet) {
        if (packet.length < HEADER_BYTES || packet.length > HEADER_BYTES + MAX_DIMENSION * MAX_DIMENSION * 4)
            throw new IllegalArgumentException("frame size");
        Frame f = new Frame(packet.clone());
        ByteBuffer b = f.b;
        if (b.getInt(0) != 0x4644434d || b.getShort(4) != 0 || b.getShort(6) != 1 || b.getInt(8) != HEADER_BYTES)
            throw new IllegalArgumentException("frame header/version");
        long w = Integer.toUnsignedLong(b.getInt(80)), h = Integer.toUnsignedLong(b.getInt(84));
        if (w == 0 || w > MAX_DIMENSION || h == 0 || h > MAX_DIMENSION || b.getInt(88) != w * 4 ||
            b.getInt(12) != w * h * 4 || packet.length != HEADER_BYTES + w * h * 4)
            throw new IllegalArgumentException("frame dimensions/stride");
        if (b.getInt(92) != 1 || b.getInt(96) < 1 || b.getInt(96) > 3 ||
            Integer.compareUnsigned(b.getInt(100), 1) > 0 || Integer.compareUnsigned(b.getInt(104), 1) > 0 ||
            b.getInt(108) != 0 || b.getLong(248) != 0 || b.getLong(224) == 0)
            throw new IllegalArgumentException("frame format/flags/reserved/clock");
        for (int o = 112; o <= 152; o += 8)
            if (!Double.isFinite(b.getDouble(o))) throw new IllegalArgumentException("frame pose");
        for (int o = 160; o <= 172; o += 4)
            if (!Float.isFinite(b.getFloat(o))) throw new IllegalArgumentException("frame angles/pivot");
        if (!Double.isFinite(b.getDouble(176)) || b.getDouble(176) <= 0 ||
            !Double.isFinite(b.getDouble(184)) || b.getDouble(184) <= 0 ||
            b.getFloat(168) < 0 || b.getFloat(168) > 1 || b.getFloat(172) < 0 || b.getFloat(172) > 1)
            throw new IllegalArgumentException("frame scale/pivot");
        CRC32 crc = new CRC32(); crc.update(f.bytes, HEADER_BYTES, f.bytes.length - HEADER_BYTES);
        if (crc.getValue() != Integer.toUnsignedLong(b.getInt(236))) throw new IllegalArgumentException("pixel crc");
        return f;
    }
    public boolean matches(UUID session, long world, long mode, long revision, long camera) {
        return session().equals(session) && worldEpoch() == world && modeEpoch() == mode &&
            worldRevision() == revision && cameraEpoch() == camera;
    }
}
