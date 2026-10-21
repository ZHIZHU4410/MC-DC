package dev.mcdn.protocol;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** control-1: bounded flat JSON, unescaped ASCII string keys/values only. */
public final class Control {
    public static final String LAYOUT = "mcdn-64-256-control-1";
    public static final String WORLD_LAYOUT = "mcdn-64-256-world-1";
    private Control() {}
    public static final class Peer {
        private final UUID session;
        private final String role, build;
        private final long pid, startTime, capabilities;
        private Peer(UUID session, String role, String build, long pid, long startTime, long capabilities) {
            this.session = session; this.role = role; this.build = build; this.pid = pid; this.startTime = startTime; this.capabilities = capabilities;
        }
        public UUID session() { return session; }
        public String role() { return role; }
        public String build() { return build; }
        public long pid() { return pid; }
        public long startTime() { return startTime; }
        public long capabilities() { return capabilities; }
    }
    /** Per-connection, one-shot authentication. A failed or repeated HELLO closes this gate. */
    public static final class Handshake {
        private boolean used;
        public Peer accept(Wire.Envelope m, UUID session, int type, String role, String nonce, String build) {
            return accept(m, session, type, role, nonce, build, 1);
        }
        public Peer accept(Wire.Envelope m, UUID session, int type, String role, String nonce, String build, long capabilities) {
            if (used) throw new IllegalArgumentException("handshake already used");
            used = true; return verifyHello(m, session, type, role, nonce, build, capabilities);
        }
    }
    /** Socket-worker owned. Only emitted messages may be acknowledged by the remote consumer. */
    public static final class AckWindow {
        private long sent, ack;
        public void sent(long sequence) {
            if (Long.compareUnsigned(sequence, sent) <= 0) throw new IllegalArgumentException("send sequence");
            sent = sequence;
        }
        public void observe(long sequence) {
            if (Long.compareUnsigned(sequence, ack) < 0 || Long.compareUnsigned(sequence, sent) > 0)
                throw new IllegalArgumentException("ack regression/future");
            ack = sequence;
        }
        public long acknowledged() { return ack; }
    }
    public record Input(long inputSeq, long hostTick, long eventSeq, int held, int pressed, int released) {}
    private static final class Parser {
        final String text; int pos;
        Parser(String text) { this.text = text; }
        void space() { while (pos < text.length() && " \t\r\n".indexOf(text.charAt(pos)) >= 0) pos++; }
        void expect(char ch) { space(); if (pos == text.length() || text.charAt(pos++) != ch) throw new IllegalArgumentException("control syntax"); }
        String string(int max) {
            expect('"'); int begin = pos;
            while (pos < text.length() && text.charAt(pos) != '"') {
                if (text.charAt(pos) < 32 || text.charAt(pos) == '\\' || pos - begin >= max)
                    throw new IllegalArgumentException("control string");
                pos++;
            }
            if (pos == text.length()) throw new IllegalArgumentException("control string");
            return text.substring(begin, pos++);
        }
    }
    public static Map<String, String> parse(byte[] bytes) {
        if (bytes.length > 16384) throw new IllegalArgumentException("control limit");
        for (byte b : bytes) if (b < 0 || b == 127) throw new IllegalArgumentException("control encoding");
        Parser p = new Parser(new String(bytes, StandardCharsets.US_ASCII));
        Map<String, String> fields = new LinkedHashMap<>(); p.expect('{'); p.space();
        if (p.pos < p.text.length() && p.text.charAt(p.pos) != '}') {
            while (true) {
                String key = p.string(64); p.expect(':'); String value = p.string(2048);
                if (fields.putIfAbsent(key, value) != null || fields.size() > 32) throw new IllegalArgumentException("duplicate/field limit");
                p.space(); if (p.pos < p.text.length() && p.text.charAt(p.pos) == ',') { p.pos++; continue; }
                break;
            }
        }
        p.expect('}'); p.space(); if (p.pos != p.text.length()) throw new IllegalArgumentException("control trailing data");
        return fields;
    }
    public static byte[] encode(String... pairs) {
        if (pairs.length % 2 != 0) throw new IllegalArgumentException("pairs");
        StringBuilder out = new StringBuilder("{");
        for (int i = 0; i < pairs.length; i += 2) {
            if (i > 0) out.append(',');
            for (int k = 0; k < 2; k++) {
                if (k > 0) out.append(':'); out.append('"');
                String s = pairs[i + k];
                for (int n = 0; n < s.length(); n++) {
                    char ch = s.charAt(n); if (ch < 32 || ch > 126 || ch == '"' || ch == '\\') throw new IllegalArgumentException("control string");
                    out.append(ch);
                }
                out.append('"');
            }
        }
        byte[] bytes = out.append('}').toString().getBytes(StandardCharsets.US_ASCII); parse(bytes); return bytes;
    }
    public static long u64(String value) {
        if (value.isEmpty() || value.length() > 20 || (value.length() > 1 && value.charAt(0) == '0'))
            throw new IllegalArgumentException("canonical u64");
        for (int i = 0; i < value.length(); i++) if (value.charAt(i) < '0' || value.charAt(i) > '9')
            throw new IllegalArgumentException("canonical u64");
        return Long.parseUnsignedLong(value);
    }
    public static void fields(Map<String, String> fields, String... keys) {
        if (fields.size() != keys.length || !fields.keySet().containsAll(Arrays.asList(keys)))
            throw new IllegalArgumentException("schema fields");
    }
    private static void hex(String value) {
        if (!value.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("hex256");
    }
    public static byte[] hello(String role, String nonce, String build, long pid, long startTime) {
        return hello(role, nonce, build, pid, startTime, 1);
    }
    public static byte[] hello(String role, String nonce, String build, long pid, long startTime, long capabilities) {
        if (capabilities != 1 && capabilities != 3) throw new IllegalArgumentException("capabilities");
        return encode("schema", capabilities == 3 ? "world-1" : "control-1", "role", role, "nonce", nonce,
            "layout", capabilities == 3 ? WORLD_LAYOUT : LAYOUT, "build", build,
            "pid", Long.toUnsignedString(pid), "startTime", Long.toUnsignedString(startTime),
            "javaMajor", role.equals("mc") ? "25" : "0", "capabilities", Long.toUnsignedString(capabilities));
    }
    public static Peer verifyHello(Wire.Envelope m, UUID session, int type, String role, String nonce, String build) {
        return verifyHello(m, session, type, role, nonce, build, 1);
    }
    public static Peer verifyHello(Wire.Envelope m, UUID session, int type, String role, String nonce, String build, long capabilities) {
        if (capabilities != 1 && capabilities != 3) throw new IllegalArgumentException("capabilities");
        if (!m.session().equals(session) || m.type() != type || m.worldEpoch() != 0 || m.modeEpoch() != 0 ||
            m.sequence() != 1 || m.ackSequence() != (type == 2 ? 1 : 0) || (type != 1 && type != 2) ||
            !role.equals(type == 1 ? "mc" : "dc")) throw new IllegalArgumentException("hello envelope");
        var f = parse(m.body()); fields(f, "schema", "role", "nonce", "layout", "build", "pid", "startTime", "javaMajor", "capabilities");
        hex(nonce); hex(build); hex(f.get("nonce")); hex(f.get("build"));
        if (!MessageDigest.isEqual(HexFormat.of().parseHex(nonce), HexFormat.of().parseHex(f.get("nonce"))) ||
            !f.get("schema").equals(capabilities == 3 ? "world-1" : "control-1") || !f.get("role").equals(role) ||
            !f.get("layout").equals(capabilities == 3 ? WORLD_LAYOUT : LAYOUT) ||
            !f.get("build").equals(build) || !f.get("javaMajor").equals(role.equals("mc") ? "25" : "0") || u64(f.get("capabilities")) != capabilities)
            throw new IllegalArgumentException("hello binding/auth/capability");
        long pid = u64(f.get("pid")), start = u64(f.get("startTime"));
        if (pid == 0 || Long.compareUnsigned(pid, 0xffffffffL) > 0 || start == 0) throw new IllegalArgumentException("process claim");
        return new Peer(session, role, build, pid, start, capabilities);
    }
    public static byte[] encodeInput(Input m) {
        return encode("inputSeq", Long.toUnsignedString(m.inputSeq), "hostTick", Long.toUnsignedString(m.hostTick),
            "eventSeq", Long.toUnsignedString(m.eventSeq), "held", Integer.toString(m.held),
            "pressed", Integer.toString(m.pressed), "released", Integer.toString(m.released));
    }
    public static Input parseInput(byte[] bytes) {
        var f = parse(bytes); fields(f, "inputSeq", "hostTick", "eventSeq", "held", "pressed", "released");
        long held = u64(f.get("held")), pressed = u64(f.get("pressed")), released = u64(f.get("released"));
        if (Long.compareUnsigned(held | pressed | released, 127) > 0 || (pressed & released) != 0 ||
            (pressed & held) != pressed || (released & held) != 0) throw new IllegalArgumentException("button masks");
        return new Input(u64(f.get("inputSeq")), u64(f.get("hostTick")), u64(f.get("eventSeq")), (int)held, (int)pressed, (int)released);
    }
}
