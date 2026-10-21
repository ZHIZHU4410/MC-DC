package dev.mcdn.protocol;

import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public final class WorldModeBench {
    static void check(boolean pass) { if (!pass) throw new AssertionError("world/mode assertion"); }
    static void reject(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("expected world/mode rejection");
    }
    static final class Binding implements ModeGate.Binding {
        final World.Stamp stamp;
        Binding(World.Stamp stamp) { this.stamp = stamp; }
        public boolean matches(World.Stamp s, long mode) { return stamp.equals(s) && mode == 1; }
        int enters, releases; boolean allowRestore = true; String fault;
        public boolean enter() { enters++; return true; }
        public boolean release() { releases++; return allowRestore; }
        public String fault() { return fault; }
    }
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]); int count = 0;
        try (var paths = Files.list(root)) {
            for (var path : paths.filter(p -> p.toString().endsWith(".world")).sorted().toList()) {
                byte[] bytes = Files.readAllBytes(path); boolean accepted = true;
                try { check(Arrays.equals(World.decode(bytes).encode(), bytes)); }
                catch (IllegalArgumentException ex) { accepted = false; }
                check(accepted != path.getFileName().toString().startsWith("bad-")); count++;
            }
        }
        World world = World.decode(Files.readAllBytes(root.resolve("exported.world")));
        byte[] bytes = world.encode(); var transfer = new World.Transfer(world.stamp(), bytes.length);
        for (int off = 0, i = 0; off < bytes.length; i++) {
            int n = Math.min(37, bytes.length - off); transfer.chunk(i, Arrays.copyOfRange(bytes, off, off+n)); off += n;
        }
        check(transfer.finish().stamp().equals(world.stamp())); reject(transfer::finish);
        var incomplete = new World.Transfer(world.stamp(), bytes.length); incomplete.chunk(0, Arrays.copyOf(bytes, 12)); reject(incomplete::finish);
        var duplicate = new World.Transfer(world.stamp(), bytes.length); duplicate.chunk(0, Arrays.copyOf(bytes, 12));
        reject(() -> duplicate.chunk(0, Arrays.copyOf(bytes, 12))); reject(duplicate::finish);
        var oversized = new World.Transfer(world.stamp(), bytes.length); reject(() -> oversized.chunk(0, new byte[1025]));
        var wrongStamp = new World.Stamp(world.stamp().session(), world.stamp().epoch(), 99, world.stamp().digest());
        var wrong = new World.Transfer(wrongStamp, bytes.length); wrong.chunk(0, bytes); reject(wrong::finish);
        var gate = new ModeGate(world.stamp().session()); var binding = new Binding(world.stamp());
        Frame frame = Frame.decode(Files.readAllBytes(root.resolve("ready.frame")));
        gate.stage(world); check(gate.prepare(1, 1, 100, 1000));
        check(!gate.commit(world.stamp(), 1, 1, frame.frameId(), 101, binding));
        check(gate.applied("client", world.stamp())); check(gate.carrierPrepared(1));
        check(gate.offerFrame(frame, 101)); check(gate.state() == ModeGate.State.PREPARING);
        check(!gate.commit(world.stamp(), 1, 1, frame.frameId(), 101, binding)); check(binding.enters == 0);
        check(gate.applied("server", world.stamp())); check(gate.state() == ModeGate.State.PREPARING);
        check(!gate.spaceChecked("client", world.stamp(), 1, frame.frameId()+1, frame.nativeTick(), true));
        gate.spaceChecked("client", world.stamp(), 1, frame.frameId(), frame.nativeTick(), true);
        check(!gate.commit(world.stamp(), 1, 1, frame.frameId(), 101, binding));
        gate.spaceChecked("server", world.stamp(), 1, frame.frameId(), frame.nativeTick(), true);
        check(gate.state() == ModeGate.State.READY);
        check(!gate.commit(wrongStamp, 1, 1, frame.frameId(), 101, binding));
        check(!gate.commit(world.stamp(), 1, 2, frame.frameId(), 101, binding));
        check(!gate.commit(world.stamp(), 1, 1, frame.frameId()+1, 101, binding));
        check(gate.commit(world.stamp(), 1, 1, frame.frameId(), 101, binding));
        check(gate.commit(world.stamp(), 1, 1, frame.frameId(), 101, binding)); check(binding.enters == 1);
        binding.fault = "input-lease-expired"; gate.tick(102); check(gate.state() == ModeGate.State.HERO && binding.releases == 1);
        check(!gate.prepare(1, 1, 103, 1000)); check(gate.prepare(2, 1, 103, 1000));
        check(!gate.offerFrame(frame, 104)); gate.tick(1103); check(gate.state() == ModeGate.State.HERO);
        check(gate.prepare(3, 1, 1200, 1000)); gate.revoke("disconnect"); check(gate.state() == ModeGate.State.HERO);
        reject(() -> gate.stage(world));
        // Failed restore keeps a recoverable state; future modes cannot bypass it.
        var retry = new ModeGate(world.stamp().session()); var broken = new Binding(world.stamp()); broken.allowRestore = false;
        retry.stage(world); retry.prepare(1, 1, 100, 1000); retry.applied("client", world.stamp()); retry.applied("server", world.stamp());
        retry.carrierPrepared(1); retry.offerFrame(frame, 101);
        retry.spaceChecked("client", world.stamp(), 1, frame.frameId(), frame.nativeTick(), true);
        retry.spaceChecked("server", world.stamp(), 1, frame.frameId(), frame.nativeTick(), true);
        check(retry.commit(world.stamp(), 1, 1, frame.frameId(), 101, broken));
        retry.revoke("disconnect"); check(retry.state() == ModeGate.State.RECOVERING); check(!retry.prepare(2, 1, 102, 1000));
        broken.allowRestore = true; retry.revoke("retry"); check(retry.state() == ModeGate.State.HERO);
        var changed = new ModeGate(world.stamp().session()); var switched = new Binding(world.stamp());
        changed.stage(world); changed.prepare(1, 1, 100, 1000); changed.applied("client", world.stamp()); changed.applied("server", world.stamp());
        changed.carrierPrepared(1); check(!changed.offerFrame(frame, 1100)); check(!changed.offerFrame(frame, 99)); changed.offerFrame(frame, 101);
        changed.spaceChecked("client", world.stamp(), 1, frame.frameId(), frame.nativeTick(), true);
        changed.spaceChecked("server", world.stamp(), 1, frame.frameId(), frame.nativeTick(), true);
        check(changed.commit(world.stamp(), 1, 1, frame.frameId(), 101, switched));
        World next = World.decode(Files.readAllBytes(root.resolve("good-next.world"))); changed.stage(next);
        check(switched.releases == 1 && changed.state() == ModeGate.State.HERO); check(changed.prepare(2, 1, 102, 1000));
        check(!changed.offerFrame(frame, 103)); check(!changed.commit(world.stamp(), 1, 1, frame.frameId(), 103, switched));
        var blocked = new ModeGate(world.stamp().session()); blocked.stage(world); blocked.prepare(1, 1, 100, 1000);
        blocked.offerFrame(frame, 101); check(!blocked.spaceChecked("server", world.stamp(), 1, frame.frameId(), frame.nativeTick(), false));
        check(blocked.state() == ModeGate.State.HERO && blocked.reason().equals("blocked-spawn"));
        var failure = new AtomicReference<Throwable>();
        Thread foreign = new Thread(() -> { try { gate.state(); failure.set(new AssertionError("foreign thread accepted")); } catch (IllegalStateException expected) {} });
        foreign.start(); foreign.join(); check(failure.get() == null);
        System.out.println("WORLD_JAVA_PASS " + count + "; chunks/hash/duplicate/truncation/bounds PASS");
        System.out.println("MODE_GATE_PASS dual geometry/frame/carrier gates; exact commit; idempotency; timeout; stale mode; lease fault; restore retry; thread ownership");
    }
}
