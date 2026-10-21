package dev.mcdn.protocol;

import java.util.Objects;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.IntConsumer;

/**
 * One socket producer, one native-input consumer. No locks, waits, I/O or game objects.
 * Construct a fresh inbox per committed mode, after external world/frame/carrier readiness.
 * Receipt never advances consumedAck. Consumer clock is local monotonic nanoseconds.
 */
public final class InputInbox {
    public static final int CAPACITY = 128;
    public static final long LEASE_NANOS = 250_000_000L;
    private record Pending(Control.Input input, long envelopeSeq, long receivedNanos) {}
    private final Pending[] slots = new Pending[CAPACITY + 1];
    private volatile int head, tail; // acquire/release within the JVM only, not shared-memory IPC
    /** Connection-wide ordering survives mode changes. Socket worker owns this object. */
    public static final class SessionOrder {
        private final java.util.UUID session;
        private long received = 1; // verified host HELLO_ACK
        private volatile long consumedAck = 1; // handshake was consumed before any mode existed
        private final Control.AckWindow outbound = new Control.AckWindow();
        public SessionOrder(Control.Peer peer) {
            if (!peer.role().equals("dc")) throw new IllegalArgumentException("input peer");
            session = peer.session(); outbound.sent(1); outbound.observe(1); // MC HELLO consumed by host
        }
        private void accept(Wire.Envelope m) {
            if (!m.session().equals(session) || Long.compareUnsigned(m.sequence(), received) <= 0)
                throw new IllegalArgumentException("connection sequence");
            outbound.observe(m.ackSequence()); received = m.sequence();
        }
    }
    private final SessionOrder order;
    private final long world, mode;
    private final AtomicReference<String> fault = new AtomicReference<>();
    private long lastInput, lastEvent, lastHostTick;
    private int receivedHeld;
    private volatile long releaseSequence;
    private long consumedInput, consumedAt;
    private int appliedHeld;
    private boolean hasConsumed;

    public InputInbox(Control.Peer peer, long world, long mode) {
        this(peer, world, mode, new SessionOrder(peer));
    }
    public InputInbox(Control.Peer peer, long world, long mode, SessionOrder order) {
        if (!peer.role().equals("dc") || world == 0 || mode == 0) throw new IllegalArgumentException("input context");
        if (!peer.session().equals(order.session)) throw new IllegalArgumentException("input session order");
        this.world = world; this.mode = mode; this.order = order;
    }
    public String fault() { return fault.get(); }
    public boolean matches(java.util.UUID session, long world, long mode) {
        return order.session.equals(session) && this.world == world && this.mode == mode;
    }
    public long consumedAck() { return order.consumedAck; }
    public long consumedInput() { return consumedInput; }
    public int held() { return appliedHeld; }
    public void revoke(String reason) { fault.compareAndSet(null, Objects.requireNonNull(reason)); }
    public void outboundSent(long sequence) { order.outbound.sent(sequence); } // same socket-worker owner

    /** Socket worker. Parsing/identity/overflow errors latch a fault; no further message may revive it. */
    public boolean receive(Wire.Envelope m, long receivedNanos) {
        if (fault.get() != null) return false;
        try {
            if ((m.type() != 13 && m.type() != 12) || m.sequence() == 1) throw new IllegalArgumentException("input type/sequence");
            if (m.worldEpoch() != world || m.modeEpoch() != mode) throw new IllegalArgumentException("input epoch");
            order.accept(m);
            if (m.type() == 12) {
                var fields = Control.parse(m.body()); Control.fields(fields, "reason");
                if (!java.util.Set.of("release", "paused", "focus-lost", "world-change", "shutdown").contains(fields.get("reason")))
                    throw new IllegalArgumentException("release reason");
                releaseSequence = m.sequence(); revoke(fields.get("reason")); return true;
            }
            Control.Input input = Control.parseInput(m.body());
            if (lastInput == -1L || input.inputSeq() != lastInput + 1 || Long.compareUnsigned(input.hostTick(), lastHostTick) < 0)
                throw new IllegalArgumentException("input sequence/tick");
            int pressed = input.held() & ~receivedHeld, released = receivedHeld & ~input.held();
            boolean edge = (pressed | released) != 0;
            if ((edge && lastEvent == -1L) || input.eventSeq() != lastEvent + (edge ? 1 : 0) ||
                input.pressed() != pressed || input.released() != released)
                throw new IllegalArgumentException("input edges");
            int next = (tail + 1) % slots.length;
            if (next == head) { revoke("queue-overflow"); return false; }
            slots[tail] = new Pending(input, m.sequence(), receivedNanos);
            lastInput = input.inputSeq(); lastEvent = input.eventSeq(); lastHostTick = input.hostTick(); receivedHeld = input.held();
            tail = next;
            return true;
        } catch (IllegalArgumentException ex) { revoke("invalid-input"); return false; }
    }

    /**
     * Native client-input thread, once per tick. At most one edge-bearing snapshot preserves taps;
     * redundant held snapshots can drain in the same bounded tick, avoiding host-FPS backlog.
     * Callback installs native input only. Physics/server commit are reported separately.
     */
    public void tick(long nowNanos, IntConsumer installNativeHeld) {
        Objects.requireNonNull(installNativeHeld);
        if (fault.get() != null) { release(installNativeHeld); return; }
        boolean edgeConsumed = false, consumed = false;
        for (int budget = 0; budget < CAPACITY && head != tail; budget++) {
            Pending pending = slots[head];
            boolean edge = (pending.input.pressed() | pending.input.released()) != 0;
            if (edge && edgeConsumed) break;
            long age = nowNanos - pending.receivedNanos;
            if (age < 0 || age >= LEASE_NANOS) { revoke("stale-queued-input"); release(installNativeHeld); return; }
            try { installNativeHeld.accept(pending.input.held()); }
            catch (RuntimeException ex) { revoke("native-input-failed"); release(installNativeHeld); throw ex; }
            if (fault.get() != null) { release(installNativeHeld); return; }
            appliedHeld = pending.input.held(); consumedAt = pending.receivedNanos; hasConsumed = true;
            consumedInput = pending.input.inputSeq(); order.consumedAck = pending.envelopeSeq;
            slots[head] = null; head = (head + 1) % slots.length;
            edgeConsumed |= edge; consumed = true;
        }
        if (!consumed) {
            if (hasConsumed && (nowNanos - consumedAt < 0 || nowNanos - consumedAt >= LEASE_NANOS)) {
                revoke("input-lease-expired"); release(installNativeHeld);
            } else {
                try { installNativeHeld.accept(appliedHeld); }
                catch (RuntimeException ex) { revoke("native-input-failed"); release(installNativeHeld); throw ex; }
                if (fault.get() != null) release(installNativeHeld);
            }
        }
    }
    private void release(IntConsumer sink) {
        appliedHeld = 0;
        // Consumer owns head and can drop the entire pending ring after terminal revocation.
        while (head != tail) { slots[head] = null; head = (head + 1) % slots.length; }
        sink.accept(0);
        if (Long.compareUnsigned(releaseSequence, order.consumedAck) > 0) order.consumedAck = releaseSequence;
    }
}
