package dev.mcdn.minecraft;

import dev.mcdn.protocol.*;
import net.minecraft.core.Direction;
import net.minecraft.client.player.ClientInput;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.shapes.Shapes;
import java.nio.file.*;
import java.util.concurrent.atomic.AtomicReference;

/** Real native shape solver and input objects; no game Level, Entity or loader is started. */
public final class NativeWorldBench {
    private record Trial(World.Stamp stamp, double wall, double floor, double back, double front, double ceiling, boolean free, boolean blocked) {}
    static void check(boolean ok) { if (!ok) throw new AssertionError("native world assertion"); }
    static void near(double actual, double expected) { check(Math.abs(actual - expected) < 0.000001); }
    static Trial solve(World world) {
        var layer = new BridgeGeometry(world); var shapes = layer.shapes();
        var standing = new AABB(0.25, 0, -0.3, 0.85, 1.8, 0.3);
        var falling = new AABB(0.25, 1, -0.3, 0.85, 2.8, 0.3);
        return new Trial(layer.applied(), Shapes.collide(Direction.Axis.X, standing, shapes, 3),
            Shapes.collide(Direction.Axis.Y, falling, shapes, -3), Shapes.collide(Direction.Axis.Z, standing, shapes, 3),
            Shapes.collide(Direction.Axis.Z, standing, shapes, -3), Shapes.collide(Direction.Axis.Y, standing, shapes, 5),
            layer.isFree(standing), layer.isFree(new AABB(2.3, 0, -0.3, 2.9, 1.8, 0.3)));
    }
    static final class Slot implements BridgeInputBinding.Slot {
        ClientInput value = new ClientInput(); final ClientInput original = value; boolean failRestore, failEnter;
        public ClientInput get() { return value; }
        public void set(ClientInput input) {
            if (failRestore && input == original) throw new IllegalStateException("fixture restore failure");
            value = input;
            if (failEnter && input != original) throw new IllegalStateException("fixture partial enter failure");
        }
    }
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]); var world = World.decode(Files.readAllBytes(root.resolve("exported.world")));
        var client = new AtomicReference<Trial>(); var server = new AtomicReference<Trial>(); var error = new AtomicReference<Throwable>();
        Thread clientThread = new Thread(() -> { try { client.set(solve(world)); } catch (Throwable ex) { error.set(ex); } });
        Thread serverThread = new Thread(() -> { try { server.set(solve(world)); } catch (Throwable ex) { error.set(ex); } });
        clientThread.start(); serverThread.start(); clientThread.join(); serverThread.join();
        if (error.get() != null) throw new AssertionError(error.get());
        check(client.get().equals(server.get())); var result = client.get();
        near(result.wall, 1.4); near(result.floor, -1); near(result.back, 0.95); near(result.front, -0.95); near(result.ceiling, 1.95);
        check(result.free && !result.blocked);
        var peer = new Control.Handshake().accept(new Wire.Envelope(2, world.stamp().session(), 0, 0, 1, 1,
            Control.hello("dc", "a".repeat(64), "b".repeat(64), 123, 456)), world.stamp().session(), 2, "dc", "a".repeat(64), "b".repeat(64));
        var frame = Frame.decode(Files.readAllBytes(root.resolve("ready.frame")));
        near(frame.footX(), 0.55); near(frame.footY(), 0); near(frame.footZ(), 0);
        var inbox = new InputInbox(peer, world.stamp().epoch(), 1); var slot = new Slot(); var binding = new BridgeInputBinding(slot, inbox);
        var gate = new ModeGate(world.stamp().session());
        gate.stage(world); gate.prepare(1, 1, 100, 1000);
        gate.applied("client", result.stamp); gate.applied("server", server.get().stamp); gate.carrierPrepared(1); gate.offerFrame(frame, 101);
        gate.spaceChecked("client", result.stamp, 1, frame.frameId(), frame.nativeTick(), result.free);
        gate.spaceChecked("server", result.stamp, 1, frame.frameId(), frame.nativeTick(), server.get().free);
        check(gate.commit(world.stamp(), 1, 1, frame.frameId(), 101, binding)); check(slot.value instanceof BridgeClientInput);
        check(inbox.receive(new Wire.Envelope(13, world.stamp().session(), world.stamp().epoch(), 1, 2, 1,
            Control.encodeInput(new Control.Input(1, 1, 1, 1, 1, 0))), System.nanoTime()));
        slot.value.tick(); check(slot.value.keyPresses.forward());
        ClientInput savedBridge = slot.value;
        slot.failRestore = true; gate.revoke("disconnect");
        check(gate.state() == ModeGate.State.RECOVERING); check(savedBridge.keyPresses.equals(net.minecraft.world.entity.player.Input.EMPTY));
        slot.failRestore = false; gate.revoke("retry"); check(gate.state() == ModeGate.State.HERO && slot.value == slot.original);
        // A setter that throws after installation still restores the same original object.
        var brokenInbox = new InputInbox(peer, world.stamp().epoch(), 1); var partial = new Slot(); partial.failEnter = true;
        var retryGate = new ModeGate(world.stamp().session()); retryGate.stage(world); retryGate.prepare(1, 1, 100, 1000);
        retryGate.applied("client", result.stamp); retryGate.applied("server", result.stamp); retryGate.carrierPrepared(1); retryGate.offerFrame(frame, 101);
        retryGate.spaceChecked("client", result.stamp, 1, frame.frameId(), frame.nativeTick(), true);
        retryGate.spaceChecked("server", result.stamp, 1, frame.frameId(), frame.nativeTick(), true);
        check(!retryGate.commit(world.stamp(), 1, 1, frame.frameId(), 101, new BridgeInputBinding(partial, brokenInbox)));
        check(partial.value == partial.original && retryGate.state() == ModeGate.State.HERO);
        System.out.println("MC_WORLD_NATIVE_PASS two fixture threads: fractional wall=1.4 floor=-1 depth=+/-0.95 ceiling=1.95");
        System.out.println("MC_MODE_NATIVE_PASS gated real ClientInput binding; input applied; disconnect clears; failed restore retries; original object restored");
    }
}
