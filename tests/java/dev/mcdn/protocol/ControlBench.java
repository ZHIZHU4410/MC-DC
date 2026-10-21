package dev.mcdn.protocol;

import java.nio.file.*;
import java.net.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public final class ControlBench {
    static final UUID ID = UUID.fromString("00112233-4455-6677-8899-aabbccddeeff");
    static void check(boolean value) { if (!value) throw new AssertionError("control assertion failed"); }
    static void reject(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException ex) { return; }
        throw new AssertionError("expected rejection");
    }
    static Control.Peer host() {
        byte[] body = Control.hello("dc", "a".repeat(64), "c".repeat(64), 123, 456);
        return new Control.Handshake().accept(new Wire.Envelope(2, ID, 0, 0, 1, 1, body), ID, 2, "dc", "a".repeat(64), "c".repeat(64));
    }
    static Wire.Envelope input(long env, long seq, long event, int held, int pressed, int released) {
        return new Wire.Envelope(13, ID, 1, 1, env, 1, Control.encodeInput(new Control.Input(seq, seq, event, held, pressed, released)));
    }
    static InputInbox inbox() { return new InputInbox(host(), 1, 1); }
    static void tests() throws Exception {
        byte[] helloBody = Control.hello("mc", "a".repeat(64), "b".repeat(64), 123, 456);
        var hello = new Wire.Envelope(1, ID, 0, 0, 1, 0, helloBody);
        for (var bad : List.of(new Wire.Envelope(1, UUID.randomUUID(), 0, 0, 1, 0, helloBody),
            new Wire.Envelope(1, ID, 1, 0, 1, 0, helloBody), new Wire.Envelope(1, ID, 0, 1, 1, 0, helloBody),
            new Wire.Envelope(1, ID, 0, 0, 2, 0, helloBody), new Wire.Envelope(1, ID, 0, 0, 1, 1, helloBody),
            new Wire.Envelope(2, ID, 0, 0, 1, 0, helloBody))) {
            var h = new Control.Handshake();
            reject(() -> h.accept(bad, ID, 1, "mc", "a".repeat(64), "b".repeat(64)));
            reject(() -> h.accept(hello, ID, 1, "mc", "a".repeat(64), "b".repeat(64)));
        }
        int[] nativeHeld = {0}; var box = inbox();
        check(box.receive(input(2, 1, 1, 16, 16, 0), 0));
        check(box.receive(input(3, 2, 2, 0, 0, 16), 1));
        check(box.consumedAck() == 1);
        box.tick(50_000_000, value -> nativeHeld[0] = value); check(nativeHeld[0] == 16 && box.consumedAck() == 2);
        box.tick(100_000_000, value -> nativeHeld[0] = value); check(nativeHeld[0] == 0 && box.consumedAck() == 3);
        box.tick(250_000_001, value -> nativeHeld[0] = value); check(nativeHeld[0] == 0 && box.fault().equals("input-lease-expired"));
        check(!box.receive(input(4, 3, 3, 16, 16, 0), 250_000_002));

        var stale = inbox(); stale.receive(input(2, 1, 1, 16, 16, 0), 0);
        stale.tick(InputInbox.LEASE_NANOS, value -> nativeHeld[0] = value);
        check(stale.consumedAck() == 1 && nativeHeld[0] == 0 && stale.fault().equals("stale-queued-input"));
        var clock = inbox(); clock.receive(input(2, 1, 1, 16, 16, 0), 10);
        clock.tick(9, value -> nativeHeld[0] = value); check(nativeHeld[0] == 0 && clock.fault() != null);
        var overflow = inbox();
        for (int i = 1; i <= 128; i++) check(overflow.receive(input(i+1, i, 1, 1, i == 1 ? 1 : 0, 0), 0));
        check(!overflow.receive(input(130, 129, 1, 1, 0, 0), 0));
        overflow.tick(0, value -> nativeHeld[0] = value); check(nativeHeld[0] == 0 && overflow.consumedAck() == 1);
        var stable = inbox();
        for (int i = 1; i <= 128; i++) check(stable.receive(input(i+1, i, 1, 1, i == 1 ? 1 : 0, 0), 0));
        stable.tick(1, value -> nativeHeld[0] = value);
        check(stable.consumedAck() == 129 && nativeHeld[0] == 1 && stable.fault() == null);
        var wrong = inbox(); check(!wrong.receive(new Wire.Envelope(13, ID, 2, 1, 2, 1, input(2, 1, 1, 1, 1, 0).body()), 0));
        wrong.tick(0, value -> nativeHeld[0] = value); check(nativeHeld[0] == 0 && wrong.fault() != null);
        var replay = inbox(); check(replay.receive(input(2, 1, 1, 1, 1, 0), 0));
        check(!replay.receive(input(2, 1, 1, 1, 1, 0), 0)); check(replay.consumedAck() == 1);
        var missing = inbox(); check(!missing.receive(input(2, 1, 0, 16, 0, 0), 0));
        var gap = inbox(); check(!gap.receive(input(2, 2, 1, 16, 16, 0), 0));
        var futureAck = inbox(); var first = input(2, 1, 1, 16, 16, 0);
        check(!futureAck.receive(new Wire.Envelope(13, ID, 1, 1, 2, 2, first.body()), 0));
        var staleAck = inbox(); check(!staleAck.receive(new Wire.Envelope(13, ID, 1, 1, 2, 0, first.body()), 0));
        var sessionPeer = host(); var order = new InputInbox.SessionOrder(sessionPeer);
        var original = new InputInbox(sessionPeer, 1, 1, order); check(original.receive(input(2, 1, 1, 1, 1, 0), 0));
        original.revoke("world-change");
        var newMode = new InputInbox(sessionPeer, 1, 2, order);
        check(!newMode.receive(new Wire.Envelope(13, ID, 1, 2, 2, 1, first.body()), 0));
        var throwing = inbox(); throwing.receive(input(2, 1, 1, 16, 16, 0), 0);
        try { throwing.tick(0, held -> { if (held != 0) throw new IllegalStateException("native failure"); }); }
        catch (IllegalStateException expected) { check(throwing.held() == 0 && throwing.consumedAck() == 1); }
        check(throwing.fault().equals("native-input-failed"));
        var eof = inbox(); eof.receive(input(2, 1, 1, 1, 1, 0), 0); eof.tick(0, x -> {});
        eof.revoke("disconnect"); eof.tick(1, value -> nativeHeld[0] = value); check(nativeHeld[0] == 0 && eof.consumedAck() == 2);

        // Real SPSC threads exercise ring wrap and visibility, not shared-memory/JNI semantics.
        var threaded = inbox(); var failure = new AtomicReference<Throwable>();
        Thread consumer = new Thread(() -> {
            try {
                while (threaded.consumedInput() < 10_000 && threaded.fault() == null) threaded.tick(0, x -> {});
            } catch (Throwable ex) { failure.set(ex); }
        });
        consumer.setDaemon(true); consumer.start();
        for (int i = 1; i <= 10_000; i++) {
            // Keep at most one pending to test publication deterministically without inducing overflow.
            long deadline = System.nanoTime() + 5_000_000_000L;
            while (threaded.consumedAck() != i) {
                if (System.nanoTime() > deadline || failure.get() != null || threaded.fault() != null) throw new AssertionError("SPSC timeout");
                Thread.onSpinWait();
            }
            check(threaded.receive(input(i+1, i, i, i%2, i%2, i%2 == 0 ? 1 : 0), 0));
        }
        consumer.join(5000); if (consumer.isAlive()) { threaded.revoke("test-timeout"); consumer.join(1000); }
        check(!consumer.isAlive() && failure.get() == null && threaded.fault() == null && threaded.consumedAck() == 10001);
        var ack = new Control.AckWindow(); ack.sent(1); reject(() -> ack.observe(2)); ack.observe(1); reject(() -> ack.observe(0));
        System.out.println("INPUT_INBOX_PASS taps/consumed-ack/lease/stale/overflow/epochs/replay/edges/native-failure/EOF; SPSC 10000 PASS");
    }
    static Wire.Envelope read(InputStream in) throws IOException {
        byte[] h = in.readNBytes(64); if (h.length != 64) throw new EOFException();
        int size = Wire.validateHeader(h); byte[] b = in.readNBytes(size); if (b.length != size) throw new EOFException();
        byte[] packet = Arrays.copyOf(h, 64 + size); System.arraycopy(b, 0, packet, 64, size); return Wire.decode(packet);
    }
    static void connect(int port) throws Exception {
        UUID session = UUID.fromString(System.getenv("MCDN_BENCH_SESSION")); String nonce = System.getenv("MCDN_BENCH_NONCE");
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", port), 5000); socket.setSoTimeout(10000);
            InputStream in = socket.getInputStream(); OutputStream out = socket.getOutputStream();
            out.write(Wire.encode(new Wire.Envelope(1, session, 0, 0, 1, 0, Control.hello("mc", nonce, "b".repeat(64), 123, 456))));
            var peer = new Control.Handshake().accept(read(in), session, 2, "dc", nonce, "c".repeat(64));
            var order = new InputInbox.SessionOrder(peer);
            var box = new InputInbox(peer, 1, 1, order); int[] held = {0};
            check(box.receive(read(in), 0) && box.consumedAck() == 1); box.tick(1, x -> held[0] = x);
            check(held[0] == 16 && box.consumedAck() == 2);
            out.write(Wire.encode(new Wire.Envelope(3, session, 1, 1, 2, box.consumedAck(), Control.encode("held", "16", "fault", "none"))));
            box.outboundSent(2);
            check(box.receive(read(in), 2) && box.consumedAck() == 2); box.tick(3, x -> held[0] = x);
            check(held[0] == 0 && box.consumedAck() == 3);
            out.write(Wire.encode(new Wire.Envelope(3, session, 1, 1, 3, box.consumedAck(), Control.encode("held", "0", "fault", box.fault()))));
            box.outboundSent(3);
            var next = new InputInbox(peer, 1, 2, order);
            check(next.receive(read(in), 4)); next.tick(5, x -> held[0] = x); check(held[0] == 1);
            out.write(Wire.encode(new Wire.Envelope(3, session, 1, 2, 4, next.consumedAck(), Control.encode("held", "1", "fault", "none"))));
            check(in.read() == -1); next.revoke("disconnect"); next.tick(6, x -> held[0] = x);
            check(held[0] == 0 && next.consumedAck() == 4);
        }
        System.out.println("CONTROL_TCP_GUEST_PASS authenticated; native sink consumed ack; release; new mode; EOF cleared input");
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("selftest")) { tests(); return; }
        if (args[0].equals("connect")) { connect(Integer.parseInt(args[1])); return; }
        // Manifest is emitted by Python; a simple line list avoids adding a test JSON dependency.
        Path root = Path.of(args[1]); int count = 0;
        for (String line : Files.readAllLines(root.resolve("manifest.tsv"))) {
            String[] parts = line.split("\t"); boolean valid = parts[0].equals("good"), accepted = true;
            byte[] bytes = Files.readAllBytes(root.resolve(parts[2]));
            try {
                if (parts[1].equals("hello")) {
                    var m = new Wire.Envelope(1, ID, 0, 0, 1, 0, bytes); var handshake = new Control.Handshake();
                    handshake.accept(m, ID, 1, "mc", "a".repeat(64), "b".repeat(64));
                    reject(() -> handshake.accept(m, ID, 1, "mc", "a".repeat(64), "b".repeat(64)));
                } else Control.parseInput(bytes);
            } catch (IllegalArgumentException ex) { accepted = false; }
            check(accepted == valid); count++;
        }
        System.out.println("CONTROL_VECTORS_PASS " + count + "; one-shot-handshake PASS");
    }
}
