package dev.mcdn.protocol;

import java.nio.file.*;
import java.net.*;
import java.io.*;
import java.util.*;
import java.nio.charset.StandardCharsets;

public final class Bench {
    static void check(boolean ok) { if (!ok) throw new AssertionError("assertion failed"); }
    static void reject(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException ex) { return; }
        throw new AssertionError("expected rejection");
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("connect")) { connect(Integer.parseInt(args[1])); return; }
        Path root = Path.of(args[1]); int vectors = 0;
        try (var paths = Files.list(root)) {
            for (Path path : paths.sorted().toList()) {
                String name = path.getFileName().toString();
                if (!name.endsWith(".wire") && !name.endsWith(".frame")) continue;
                byte[] bytes = Files.readAllBytes(path);
                if (name.endsWith(".wire")) {
                    if (name.startsWith("bad-")) {
                        reject(() -> Wire.decode(bytes));
                        reject(() -> { var d = new Wire.StreamDecoder(); d.feed(bytes, 0, bytes.length, m -> {}); d.complete(); });
                    } else {
                        var m = Wire.decode(bytes);
                        check(Arrays.equals(Wire.encode(m), bytes));
                        check(m.session().toString().equals("00112233-4455-6677-8899-aabbccddeeff"));
                        check(m.worldEpoch() == -1L && m.modeEpoch() == Long.MIN_VALUE);
                        for (int split = 0; split <= Math.min(bytes.length, 65); split++) {
                            int[] count = {0}; var d = new Wire.StreamDecoder();
                            java.util.function.Consumer<Wire.Envelope> got = item -> {
                                check(Arrays.equals(Wire.encode(item), bytes)); count[0]++;
                            };
                            d.feed(bytes, 0, split, got); d.feed(bytes, split, bytes.length - split, got);
                            d.complete(); check(count[0] == 1);
                        }
                        byte[] joined = new byte[bytes.length * 2];
                        System.arraycopy(bytes, 0, joined, 0, bytes.length); System.arraycopy(bytes, 0, joined, bytes.length, bytes.length);
                        int[] count = {0}; var d = new Wire.StreamDecoder();
                        d.feed(joined, 0, joined.length, item -> count[0]++); d.complete(); check(count[0] == 2);
                    }
                } else if (name.startsWith("bad-")) reject(() -> Frame.decode(bytes));
                else {
                    var f = Frame.decode(bytes); check(Arrays.equals(f.encode(), bytes));
                    check(f.footX() == 12.5 && f.footY() == -3.25 && f.footZ() == 0.125 && f.frameId() == -1L);
                    check(f.nativeTick() == Long.MIN_VALUE + 1 && f.consumedInputSeq() == 9007199254740993L);
                    check(f.matches(f.session(), f.worldEpoch(), f.modeEpoch(), f.worldRevision(), f.cameraEpoch()));
                    check(!f.matches(f.session(), f.worldEpoch()-1, f.modeEpoch(), f.worldRevision(), f.cameraEpoch()));
                    check(!f.matches(f.session(), f.worldEpoch(), f.modeEpoch()+1, f.worldRevision(), f.cameraEpoch()));
                    check(!f.matches(f.session(), f.worldEpoch(), f.modeEpoch(), f.worldRevision()+1, f.cameraEpoch()));
                    check(!f.matches(f.session(), f.worldEpoch(), f.modeEpoch(), f.worldRevision(), f.cameraEpoch()+1));
                    byte[] copy = f.encode(); copy[112] ^= 1; check(f.footX() == 12.5);
                }
                vectors++;
            }
        }
        var sample = Wire.decode(Files.readAllBytes(root.resolve("good-small.wire")));
        var gate = new Wire.ReceiveGate(sample.session(), sample.worldEpoch(), sample.modeEpoch()); gate.accept(sample);
        reject(() -> gate.accept(sample));
        reject(() -> gate.accept(new Wire.Envelope(1, UUID.randomUUID(), -1L, Long.MIN_VALUE, -1L, 0L, new byte[0])));
        reject(() -> gate.accept(new Wire.Envelope(1, sample.session(), 1L, Long.MIN_VALUE, -1L, 0L, new byte[0])));
        reject(() -> gate.accept(new Wire.Envelope(1, sample.session(), -1L, 1L, -1L, 0L, new byte[0])));
        gate.accept(new Wire.Envelope(1, sample.session(), -1L, Long.MIN_VALUE, -1L, 0L, new byte[0]));
        reject(() -> gate.accept(sample));
        var poisoned = new Wire.StreamDecoder(); reject(() -> poisoned.feed(new byte[64], 0, 64, m -> {}));
        byte[] good = Wire.encode(sample); reject(() -> poisoned.feed(good, 0, good.length, m -> {}));
        System.out.println("VECTORS_PASS " + vectors + "; fragmentation/coalescing/replay/epochs/poison PASS");
    }
    static void connect(int port) throws Exception {
        UUID id = UUID.fromString("00112233-4455-6677-8899-aabbccddeeff");
        var originals = new ArrayList<byte[]>(); var burst = new ByteArrayOutputStream();
        for (int i = 0; i < 256; i++) {
            byte[] body = ("{\"diagnostic\":\"传输样本\",\"counter\":\"" + i + "\"}").getBytes(StandardCharsets.UTF_8);
            byte[] packet = Wire.encode(new Wire.Envelope(3, id, -1L, Long.MIN_VALUE, Long.MIN_VALUE + i, 0L, body));
            originals.add(packet); burst.write(packet);
        }
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), port), 5000);
            socket.setSoTimeout(15000); socket.setTcpNoDelay(true);
            byte[] all = burst.toByteArray(); OutputStream out = socket.getOutputStream();
            // Includes byte-wise headers, split bodies and several messages in one write.
            int offset = 0; int[] sizes = {1, 2, 61, 3, 511, 7, 4096}; int index = 0;
            while (offset < all.length) {
                int n = Math.min(sizes[index++ % sizes.length], all.length - offset);
                out.write(all, offset, n); offset += n;
            }
            socket.shutdownOutput();
            var d = new Wire.StreamDecoder(); var gate = new Wire.ReceiveGate(id, -1L, Long.MIN_VALUE);
            int[] count = {0}; byte[] buffer = new byte[113]; int n;
            while ((n = socket.getInputStream().read(buffer)) != -1) {
                d.feed(buffer, 0, n, m -> {
                    gate.accept(m); check(count[0] < 256);
                    check(Arrays.equals(Wire.encode(m), originals.get(count[0]++)));
                });
            }
            d.complete(); check(count[0] == 256);
        }
        System.out.println("TCP_PASS 256 byte-exact Java -> C# -> Java");
    }
}
