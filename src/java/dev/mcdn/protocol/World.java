package dev.mcdn.protocol;

import java.nio.*;
import java.security.*;
import java.util.*;

/** Complete immutable collision blob, not yet a WORLD_* network dispatcher. */
public final class World {
    public static final int HEADER_BYTES = 96, SHAPE_BYTES = 64, MAX_SHAPES = 4096;
    public record Box(long id, double minX, double minY, double minZ, double maxX, double maxY, double maxZ) {}
    public record Stamp(UUID session, long epoch, long revision, String digest) {}
    private final byte[] data;
    private final Stamp stamp;
    private final List<Box> boxes;
    private World(byte[] data, Stamp stamp, List<Box> boxes) { this.data = data; this.stamp = stamp; this.boxes = List.copyOf(boxes); }
    public byte[] encode() { return data.clone(); }
    public Stamp stamp() { return stamp; }
    public List<Box> boxes() { return boxes; }
    public static byte[] sha256(byte[] data) {
        try { return MessageDigest.getInstance("SHA-256").digest(data); }
        catch (NoSuchAlgorithmException ex) { throw new IllegalStateException(ex); }
    }
    public static World decode(byte[] packet) {
        if (packet.length < HEADER_BYTES || packet.length > HEADER_BYTES + SHAPE_BYTES * MAX_SHAPES)
            throw new IllegalArgumentException("world size");
        byte[] data = packet.clone(); ByteBuffer b = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
        long count = Integer.toUnsignedLong(b.getInt(12));
        if (b.getInt(0) != 0x5744434d || b.getShort(4) != 0 || b.getShort(6) != 1 || b.getInt(8) != HEADER_BYTES ||
            count > MAX_SHAPES || data.length != HEADER_BYTES + count * SHAPE_BYTES || b.getInt(48) != SHAPE_BYTES ||
            b.getInt(52) != 0 || b.getLong(88) != 0) throw new IllegalArgumentException("world layout");
        if (b.getLong(32) == 0 || b.getLong(40) == 0 || !MessageDigest.isEqual(sha256(Arrays.copyOfRange(data, HEADER_BYTES, data.length)), Arrays.copyOfRange(data, 56, 88)))
            throw new IllegalArgumentException("world context/hash");
        var boxes = new ArrayList<Box>(); var ids = new HashSet<Long>();
        for (int i = 0; i < count; i++) {
            int o = HEADER_BYTES + i * SHAPE_BYTES; long id = b.getLong(o); double[] v = new double[6];
            for (int n = 0; n < 6; n++) {
                v[n] = b.getDouble(o + 8 + n * 8);
                if (!Double.isFinite(v[n]) || Math.abs(v[n]) > 1_000_000) throw new IllegalArgumentException("world coordinate");
            }
            if (id == 0 || !ids.add(id) || v[0] >= v[3] || v[1] >= v[4] || v[2] >= v[5] || b.getInt(o+56) != 1 || b.getInt(o+60) != 0)
                throw new IllegalArgumentException("world shape");
            boxes.add(new Box(id, v[0], v[1], v[2], v[3], v[4], v[5]));
        }
        UUID session = new UUID(b.order(ByteOrder.BIG_ENDIAN).getLong(16), b.getLong(24));
        b.order(ByteOrder.LITTLE_ENDIAN);
        return new World(data, new Stamp(session, b.getLong(32), b.getLong(40), HexFormat.of().formatHex(sha256(data))), boxes);
    }
    /** Ordered bounded chunk assembly; no partial snapshot is exposed. Failed transfers cannot resume. */
    public static final class Transfer {
        private final Stamp expected;
        private final byte[] data;
        private int offset, index;
        private boolean done;
        public Transfer(Stamp expected, int totalBytes) {
            if (totalBytes < HEADER_BYTES || totalBytes > HEADER_BYTES + SHAPE_BYTES * MAX_SHAPES ||
                !expected.digest.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("transfer bounds/hash");
            this.expected = expected; data = new byte[totalBytes];
        }
        public void chunk(int chunkIndex, byte[] bytes) {
            if (done) throw new IllegalArgumentException("transfer closed");
            if (chunkIndex != index || bytes.length == 0 || bytes.length > 1024 || bytes.length > data.length - offset) {
                done = true; throw new IllegalArgumentException("transfer chunk");
            }
            System.arraycopy(bytes, 0, data, offset, bytes.length); offset += bytes.length; index++;
        }
        public World finish() {
            if (done) throw new IllegalArgumentException("transfer closed");
            done = true;
            if (offset != data.length) throw new IllegalArgumentException("incomplete world");
            World world = decode(data);
            if (!world.stamp.equals(expected)) throw new IllegalArgumentException("transfer identity/hash");
            return world;
        }
    }
}
