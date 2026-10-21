package dev.mcdn.protocol;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** world-1: socket-byte handling and bounded game-thread dispatch. Never blocks a game thread. */
public final class GuestSession {
    public interface Ports {
        long qpc(); long frequency();
        void installWorld(World world); // schedule client/server installs; report via applied() on game thread
        ModeGate.Binding binding(InputInbox inbox);
    }
    private record Action(WorldCommands.Command command, SessionFlow.Receipt receipt, World completed, long receivedNanos) {}
    private record PendingInput(SessionFlow.Receipt receipt, long sequence) {}
    private final Thread owner = Thread.currentThread();
    private final Control.Peer peer;
    private final Ports ports;
    private final SessionFlow flow;
    private final ModeGate gate;
    private final BoundedQueue<Action> incoming = new BoundedQueue<>(128);
    private final BoundedQueue<Wire.Envelope> outgoing = new BoundedQueue<>(128);
    private final AtomicReference<String> fault = new AtomicReference<>();
    private final ArrayDeque<PendingInput> inputReceipts = new ArrayDeque<>(); // game-thread only
    private volatile boolean urgentRevoke;
    private volatile long revokeThrough;
    private World.Transfer transfer; private World.Stamp transferring; // socket reader only
    private World world; private long mode, camera, nextOutput = 1;
    private InputInbox inbox; private ModeGate.Binding binding; private Frame frame;
    private boolean readySent;
    public GuestSession(Control.Peer peer, Ports ports) {
        if (!peer.role().equals("dc") || peer.capabilities() != 3) throw new IllegalArgumentException("world capability not negotiated");
        this.peer = peer; this.ports = ports; flow = new SessionFlow(peer); gate = new ModeGate(peer.session());
    }
    private void thread() { if (Thread.currentThread() != owner) throw new IllegalStateException("guest game thread only"); }
    public ModeGate.State state() { thread(); return gate.state(); }
    public String fault() { return fault.get(); }
    public long consumedAck() { return flow.consumed(); }
    public void disconnect() { fault.compareAndSet(null, "disconnect"); urgentRevoke = true; }
    public void failed(String reason) { fault.compareAndSet(null, reason); urgentRevoke = true; }
    /** Reader thread. Only parses immutable values/bytes; no game or ModeGate access. */
    public boolean receive(Wire.Envelope message, long receivedNanos) {
        if (fault.get() != null) return false;
        try {
            var command = WorldCommands.parse(message); var receipt = flow.accept(message); World complete = null;
            var f = command.fields();
            if (message.type() == 4) {
                revokeThrough = message.sequence(); urgentRevoke = true; transferring = WorldCommands.stamp(message, f);
                transfer = new World.Transfer(transferring, (int)Control.u64(f.get("totalBytes")));
            } else if (message.type() == 5) {
                if (transfer == null || message.worldEpoch() != transferring.epoch() || Control.u64(f.get("revision")) != transferring.revision())
                    throw new IllegalArgumentException("chunk baseline");
                transfer.chunk((int)Control.u64(f.get("index")), command.chunk()); SessionFlow.complete(receipt); return true;
            } else if (message.type() == 6) {
                if (transfer == null || !transferring.equals(WorldCommands.stamp(message, f))) throw new IllegalArgumentException("world end baseline");
                complete = transfer.finish(); transfer = null;
            } else if (message.type() == 12) { revokeThrough = message.sequence(); urgentRevoke = true; }
            if (!incoming.offer(new Action(command, receipt, complete, receivedNanos))) throw new IllegalArgumentException("game queue overflow");
            return true;
        } catch (RuntimeException ex) { failed("invalid-world-stream"); return false; }
    }
    /** Socket writer must call sent() immediately before writing each pollOutgoing() result. */
    public Wire.Envelope pollOutgoing() { return outgoing.poll(); }
    public void sent(long sequence) { flow.sent(sequence); }
    private void reply(int type, long epoch, long modeEpoch, byte[] body) {
        if (nextOutput == -1L) { failed("send-sequence-exhausted"); return; }
        flow.flushConsumed();
        if (!outgoing.offer(new Wire.Envelope(type, peer.session(), epoch, modeEpoch, ++nextOutput, flow.consumed(), body))) failed("outgoing-overflow");
    }
    private void cancelInput(String why) {
        if (inbox != null) inbox.revoke(why);
        gate.revoke(why); // actual binding clears keys before attempting original input restore
        for (var pending : inputReceipts) SessionFlow.complete(pending.receipt());
        inputReceipts.clear(); inbox = null; binding = null; frame = null; readySent = false;
    }
    /** Start of client game tick. A native ClientInput.tick consumes inputs later in the normal chain. */
    public void beginTick() {
        thread();
        if (fault.get() != null) { cancelInput(fault.get()); flow.flushConsumed(); return; }
        if (urgentRevoke) { urgentRevoke = false; cancelInput("control-revoke"); }
        try {
            for (int budget = 0; budget < 128; budget++) {
                Action action = incoming.poll(); if (action == null) break;
                var command = action.command(); var m = command.envelope(); var f = command.fields(); boolean consume = true;
                if (Long.compareUnsigned(m.sequence(), revokeThrough) < 0) { SessionFlow.complete(action.receipt()); continue; }
                switch (m.type()) {
                    case 4 -> cancelInput("world-begin");
                    case 6 -> {
                        cancelInput("world-install");
                        if (world == null || !world.stamp().equals(action.completed().stamp())) gate.stage(action.completed());
                        world = action.completed(); SessionFlow.complete(action.receipt()); ports.installWorld(world);
                    }
                    case 9 -> {
                        if (world == null || !world.stamp().equals(WorldCommands.stamp(m, f))) throw new IllegalArgumentException("prepare world");
                        cancelInput("mode-prepare"); mode = m.modeEpoch(); camera = Control.u64(f.get("cameraEpoch"));
                        if (!gate.prepare(mode, camera, ports.qpc(), ports.frequency())) throw new IllegalArgumentException("prepare mode");
                        if (f.get("carrierPrepared").equals("1")) gate.carrierPrepared(mode);
                    }
                    case 11 -> {
                        if (world == null || frame == null || frame.nativeTick() != Control.u64(f.get("nativeTick"))) throw new IllegalArgumentException("commit proof");
                        if (inbox == null) { inbox = new InputInbox(peer, m.worldEpoch(), m.modeEpoch()); binding = ports.binding(inbox); }
                        if (!gate.commit(WorldCommands.stamp(m, f), m.modeEpoch(), Control.u64(f.get("cameraEpoch")), Control.u64(f.get("frameId")), ports.qpc(), binding))
                            throw new IllegalArgumentException("commit denied");
                    }
                    case 12 -> cancelInput(f.get("reason"));
                    case 13 -> {
                        if (gate.state() != ModeGate.State.ACTIVE || inbox == null) throw new IllegalArgumentException("input before commit");
                        // Connection-wide order/ACK already validated by flow. Inbox retains its input/edge checks.
                        var local = new Wire.Envelope(13, m.session(), m.worldEpoch(), m.modeEpoch(), m.sequence(), 1, m.body());
                        if (!inbox.receive(local, action.receivedNanos())) throw new IllegalArgumentException("input rejected");
                        inputReceipts.addLast(new PendingInput(action.receipt(), m.sequence())); consume = false;
                    }
                    default -> throw new IllegalArgumentException("dispatch type");
                }
                if (consume) SessionFlow.complete(action.receipt());
            }
            flow.flushConsumed(); gate.tick(ports.qpc());
        } catch (RuntimeException ex) { failed("game-dispatch-failed"); cancelInput(fault.get()); }
    }
    /** End of native client tick, after ClientInput.tick has actually run. */
    public void endTick() {
        thread();
        if (inbox != null) {
            while (!inputReceipts.isEmpty() && Long.compareUnsigned(inputReceipts.peekFirst().sequence(), inbox.consumedAck()) <= 0)
                SessionFlow.complete(inputReceipts.removeFirst().receipt());
            if (inbox.fault() != null) { cancelInput(inbox.fault()); }
        }
        gate.tick(ports.qpc()); flow.flushConsumed();
    }
    public void applied(String side, World.Stamp stamp, long nativeTick) {
        thread(); if (!gate.applied(side, stamp) || nativeTick == 0) { failed("geometry-receipt-mismatch"); return; }
        reply(8, stamp.epoch(), 0, Control.encode("revision", Long.toUnsignedString(stamp.revision()), "digest", stamp.digest(), "side", side, "tick", Long.toUnsignedString(nativeTick)));
    }
    public boolean offerFrame(Frame next) { thread(); boolean ok = gate.offerFrame(next, ports.qpc()); if (ok) { frame = next; readySent = false; } return ok; }
    public boolean spaceChecked(String side, World.Stamp stamp, long frameId, long nativeTick, boolean free) {
        thread(); boolean ok = gate.spaceChecked(side, stamp, mode, frameId, nativeTick, free);
        if (gate.state() == ModeGate.State.READY && !readySent) {
            readySent = true;
            reply(10, stamp.epoch(), mode, Control.encode("revision", Long.toUnsignedString(stamp.revision()), "digest", stamp.digest(),
                "cameraEpoch", Long.toUnsignedString(camera), "frameId", Long.toUnsignedString(frameId), "nativeTick", Long.toUnsignedString(nativeTick)));
        }
        return ok;
    }
    /** Diagnostics only; lets a transport send current prefix ACK without doing work on a game thread. */
    public void heartbeat(long epoch, long modeEpoch) {
        thread(); reply(3, epoch, modeEpoch, Control.encode("state", gate.state().name()));
    }
}
