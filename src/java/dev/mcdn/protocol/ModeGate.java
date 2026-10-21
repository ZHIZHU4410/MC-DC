package dev.mcdn.protocol;

import java.util.Objects;

/** Game-thread-owned guest handoff gate. Network dispatch/host Hero restoration are separate. */
public final class ModeGate {
    public enum State { HERO, PREPARING, READY, ACTIVE, RECOVERING }
    public interface Binding {
        boolean matches(World.Stamp stamp, long mode);
        boolean enter();
        boolean release();
        default String fault() { return null; }
    }
    private final Thread owner = Thread.currentThread();
    private final java.util.UUID session;
    private World world;
    private boolean clientApplied, serverApplied, carrierReady, clientSpace, serverSpace;
    private long mode, camera, frequency, started;
    private Frame frame;
    private Binding binding;
    private State state = State.HERO;
    private String reason;
    public ModeGate(java.util.UUID session) { this.session = Objects.requireNonNull(session); }
    private void thread() { if (Thread.currentThread() != owner) throw new IllegalStateException("mode game thread only"); }
    public State state() { thread(); return state; }
    public String reason() { thread(); return reason; }
    public void stage(World next) {
        thread(); Objects.requireNonNull(next);
        var stamp = next.stamp();
        if (!stamp.session().equals(session) || (world != null &&
            (Long.compareUnsigned(stamp.epoch(), world.stamp().epoch()) < 0 ||
             (stamp.epoch() == world.stamp().epoch() && Long.compareUnsigned(stamp.revision(), world.stamp().revision()) <= 0))))
            throw new IllegalArgumentException("world rollback/session");
        revoke("world-change");
        if (state == State.RECOVERING) throw new IllegalStateException("input restore pending");
        world = next; clientApplied = false; serverApplied = false;
    }
    public boolean applied(String side, World.Stamp stamp) {
        thread();
        if (world == null || !world.stamp().equals(stamp) || (!side.equals("client") && !side.equals("server"))) {
            clientApplied = false; serverApplied = false; revoke("geometry-mismatch"); return false;
        }
        if (side.equals("client")) clientApplied = true; else serverApplied = true;
        ready(); return true;
    }
    public boolean prepare(long nextMode, long cameraEpoch, long nowQpc, long qpcFrequency) {
        thread();
        if (world == null || Long.compareUnsigned(nextMode, mode) <= 0 || cameraEpoch == 0 || nowQpc < 0 || qpcFrequency <= 0)
            return false;
        revoke("mode-change"); if (state == State.RECOVERING) return false;
        mode = nextMode; camera = cameraEpoch; frequency = qpcFrequency; started = nowQpc;
        frame = null; carrierReady = false; clientSpace = false; serverSpace = false; reason = null; state = State.PREPARING; return true;
    }
    public boolean carrierPrepared(long preparedMode) {
        thread(); if (preparedMode != mode || (state != State.PREPARING && state != State.READY)) return false;
        carrierReady = true; ready(); return true;
    }
    public boolean offerFrame(Frame next, long nowQpc) {
        thread();
        if ((state != State.PREPARING && state != State.READY) || !validFrame(next, nowQpc) ||
            (frame != null && Long.compareUnsigned(next.frameId(), frame.frameId()) <= 0)) return false;
        frame = next; clientSpace = false; serverSpace = false; state = State.PREPARING; ready(); return true;
    }
    public boolean spaceChecked(String side, World.Stamp stamp, long checkedMode, long frameId, long nativeTick, boolean free) {
        thread();
        if ((state != State.PREPARING && state != State.READY) || world == null || frame == null ||
            !world.stamp().equals(stamp) || mode != checkedMode || frame.frameId() != frameId || frame.nativeTick() != nativeTick ||
            (!side.equals("client") && !side.equals("server"))) return false;
        if (!free) { revoke("blocked-spawn"); return false; }
        if (side.equals("client")) clientSpace = true; else serverSpace = true;
        ready(); return true;
    }
    private boolean validFrame(Frame f, long now) {
        return f != null && world != null && f.matches(session, world.stamp().epoch(), mode, world.stamp().revision(), camera) &&
            f.frameId() != 0 && f.nativeTick() != 0 && f.qpcFrequency() == frequency && f.readyQpc() >= 0 &&
            now >= f.readyQpc() && now - f.readyQpc() < frequency;
    }
    private void ready() {
        if (state == State.PREPARING && clientApplied && serverApplied && carrierReady && frame != null && clientSpace && serverSpace) state = State.READY;
    }
    public boolean commit(World.Stamp stamp, long committedMode, long committedCamera, long frameId, long nowQpc, Binding next) {
        thread(); Objects.requireNonNull(next);
        if (state == State.ACTIVE) return binding.fault() == null && world.stamp().equals(stamp) && mode == committedMode && camera == committedCamera &&
            frame.frameId() == frameId && binding == next;
        if (state != State.READY || !world.stamp().equals(stamp) || committedMode != mode || committedCamera != camera ||
            frame.frameId() != frameId || !next.matches(stamp, mode) || !validFrame(frame, nowQpc) || nowQpc < started || nowQpc - started >= frequency)
            return false;
        binding = next;
        try { if (next.enter()) { state = State.ACTIVE; return true; } }
        catch (RuntimeException ex) { reason = "binding-enter-failed"; }
        revoke("binding-enter-failed"); return false;
    }
    public void tick(long nowQpc) {
        thread();
        if ((state == State.PREPARING || state == State.READY) && (nowQpc < started || nowQpc - started >= frequency)) revoke("prepare-timeout");
        if (state == State.ACTIVE && binding.fault() != null) revoke(binding.fault());
    }
    public void revoke(String why) {
        thread(); reason = Objects.requireNonNull(why); frame = null; carrierReady = false; clientSpace = false; serverSpace = false;
        if (binding != null) {
            state = State.RECOVERING;
            try { if (!binding.release()) return; }
            catch (RuntimeException ex) { return; }
            binding = null;
        }
        state = State.HERO;
    }
}
