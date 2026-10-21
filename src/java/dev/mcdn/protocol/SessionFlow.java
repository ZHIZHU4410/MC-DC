package dev.mcdn.protocol;

import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

/** One socket reader registers; workers may complete; ONLY the game consumer advances the prefix ACK. */
public final class SessionFlow {
    public static final class Receipt {
        private final long sequence;
        private volatile boolean done;
        private Receipt(long sequence) { this.sequence = sequence; }
        public long sequence() { return sequence; }
    }
    private final UUID session;
    private final ConcurrentLinkedQueue<Receipt> pending = new ConcurrentLinkedQueue<>();
    private final AtomicInteger count = new AtomicInteger();
    private long received = 1, remoteAck = 1; // reader owned
    private volatile long sent = 1, consumed = 1;
    public SessionFlow(Control.Peer peer) { session = peer.session(); }
    public Receipt accept(Wire.Envelope m) {
        if (!m.session().equals(session) || Long.compareUnsigned(m.sequence(), received) <= 0 ||
            Long.compareUnsigned(m.ackSequence(), remoteAck) < 0 || Long.compareUnsigned(m.ackSequence(), sent) > 0)
            throw new IllegalArgumentException("session sequence/ack");
        if (count.incrementAndGet() > 128) { count.decrementAndGet(); throw new IllegalArgumentException("unconsumed queue overflow"); }
        Receipt receipt = new Receipt(m.sequence()); pending.add(receipt);
        received = m.sequence(); remoteAck = m.ackSequence(); return receipt;
    }
    public static void complete(Receipt receipt) { receipt.done = true; }
    public void flushConsumed() {
        Receipt first;
        while ((first = pending.peek()) != null && first.done) { consumed = first.sequence; pending.remove(); count.decrementAndGet(); }
    }
    public long consumed() { return consumed; }
    public long sent() { return sent; }
    /** Sole socket writer, immediately before writing this message. */
    public void sent(long sequence) {
        if (Long.compareUnsigned(sequence, sent) <= 0) throw new IllegalArgumentException("send sequence"); sent = sequence;
    }
}
