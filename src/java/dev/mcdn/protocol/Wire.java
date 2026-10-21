package dev.mcdn.protocol;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.UUID;
import java.util.function.Consumer;

/** Binary transport only; body schemas and game-thread consumption are separate layers. */
public final class Wire {
    public static final int HEADER_BYTES = 64, MAX_BODY_BYTES = 1 << 20;
    private Wire() {}
    public record Envelope(int type, UUID session, long worldEpoch, long modeEpoch,
                           long sequence, long ackSequence, byte[] body) {}
    private static ByteBuffer le(byte[] bytes) { return ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN); }
    public static int validateHeader(byte[] bytes) {
        if (bytes.length < HEADER_BYTES || bytes[0] != 'M' || bytes[1] != 'C' || bytes[2] != 'D' || bytes[3] != 'N')
            throw new IllegalArgumentException("header/magic");
        ByteBuffer b = le(bytes);
        if (b.getShort(4) != 0 || b.getShort(6) != 1) throw new IllegalArgumentException("version");
        int type = Short.toUnsignedInt(b.getShort(8));
        if (type < 1 || type > 22 || b.getShort(10) != 0) throw new IllegalArgumentException("type/flags");
        long length = Integer.toUnsignedLong(b.getInt(12));
        if (length > MAX_BODY_BYTES) throw new IllegalArgumentException("body limit");
        return (int)length;
    }
    public static byte[] encode(Envelope m) {
        if (m.body.length > MAX_BODY_BYTES || m.type < 1 || m.type > 22) throw new IllegalArgumentException("type/body");
        byte[] data = new byte[HEADER_BYTES + m.body.length];
        ByteBuffer b = le(data);
        b.put(new byte[]{'M', 'C', 'D', 'N'}).putShort((short)0).putShort((short)1)
            .putShort((short)m.type).putShort((short)0).putInt(m.body.length);
        // UUID is network order, independently of the surrounding little-endian integers.
        b.order(ByteOrder.BIG_ENDIAN).putLong(m.session.getMostSignificantBits()).putLong(m.session.getLeastSignificantBits());
        b.order(ByteOrder.LITTLE_ENDIAN).putLong(m.worldEpoch).putLong(m.modeEpoch)
            .putLong(m.sequence).putLong(m.ackSequence).put(m.body);
        return data;
    }
    public static Envelope decode(byte[] data) {
        int length = validateHeader(data);
        if (data.length != HEADER_BYTES + length) throw new IllegalArgumentException("packet size");
        ByteBuffer b = le(data);
        UUID session = new UUID(b.order(ByteOrder.BIG_ENDIAN).getLong(16), b.getLong(24));
        b.order(ByteOrder.LITTLE_ENDIAN);
        return new Envelope(Short.toUnsignedInt(b.getShort(8)), session, b.getLong(32), b.getLong(40),
            b.getLong(48), b.getLong(56), Arrays.copyOfRange(data, 64, data.length));
    }
    public static final class StreamDecoder {
        private final byte[] buffer = new byte[HEADER_BYTES + MAX_BODY_BYTES];
        private int used, target = HEADER_BYTES;
        private boolean failed;
        public void feed(byte[] bytes, int offset, int length, Consumer<Envelope> deliver) {
            if (failed) throw new IllegalArgumentException("decoder failed");
            try {
                java.util.Objects.checkFromIndexSize(offset, length, bytes.length);
                while (length > 0) {
                    int count = Math.min(target - used, length);
                    System.arraycopy(bytes, offset, buffer, used, count);
                    used += count; offset += count; length -= count;
                    if (used < target) continue;
                    if (target == HEADER_BYTES) {
                        target += validateHeader(buffer);
                        if (used < target) continue;
                    }
                    Envelope message = decode(Arrays.copyOf(buffer, target));
                    used = 0; target = HEADER_BYTES;
                    deliver.accept(message);
                }
            } catch (RuntimeException ex) { failed = true; throw ex; }
        }
        public void complete() {
            if (failed || used != 0) { failed = true; throw new IllegalArgumentException("truncated/failed stream"); }
        }
    }
    public static final class ReceiveGate {
        private final UUID session;
        private final long worldEpoch, modeEpoch;
        private long lastSequence;
        public ReceiveGate(UUID session, long worldEpoch, long modeEpoch) {
            this.session = session; this.worldEpoch = worldEpoch; this.modeEpoch = modeEpoch;
        }
        public void accept(Envelope m) {
            if (!m.session.equals(session) || m.worldEpoch != worldEpoch || m.modeEpoch != modeEpoch ||
                Long.compareUnsigned(m.sequence, lastSequence) <= 0)
                throw new IllegalArgumentException("identity/epoch/sequence");
            lastSequence = m.sequence;
        }
    }
}
