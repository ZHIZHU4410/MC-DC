package dev.mcdn.minecraft;

import dev.mcdn.protocol.*;
import java.util.UUID;

/** Uses real MC Input/Vec2/ClientInput classes without launching Minecraft. */
public final class NativeInputBench {
    private static void check(boolean value) { if (!value) throw new AssertionError("native type assertion"); }
    public static void main(String[] args) {
        UUID id = UUID.fromString("00112233-4455-6677-8899-aabbccddeeff");
        var hello = new Wire.Envelope(2, id, 0, 0, 1, 1, Control.hello("dc", "a".repeat(64), "b".repeat(64), 123, 456));
        var peer = new Control.Handshake().accept(hello, id, 2, "dc", "a".repeat(64), "b".repeat(64));
        var inbox = new InputInbox(peer, 1, 1); var adapter = new BridgeClientInput(inbox);
        check(inbox.receive(new Wire.Envelope(13, id, 1, 1, 2, 1,
            Control.encodeInput(new Control.Input(1, 1, 1, 21, 21, 0))), System.nanoTime()));
        adapter.tick();
        check(adapter.keyPresses.forward() && adapter.keyPresses.left() && adapter.keyPresses.jump());
        check(!adapter.keyPresses.backward() && !adapter.keyPresses.right() && !adapter.keyPresses.shift() && !adapter.keyPresses.sprint());
        check(Math.abs(adapter.getMoveVector().x - 0.70710677f) < 0.00001f && Math.abs(adapter.getMoveVector().y - 0.70710677f) < 0.00001f);
        check(inbox.consumedAck() == 2);
        check(inbox.receive(new Wire.Envelope(13, id, 1, 1, 3, 1,
            Control.encodeInput(new Control.Input(2, 2, 2, 66, 66, 21))), System.nanoTime()));
        adapter.tick(); check(adapter.keyPresses.backward() && adapter.keyPresses.sprint() && !adapter.keyPresses.forward());
        check(adapter.getMoveVector().x == 0 && adapter.getMoveVector().y == -1);
        check(inbox.receive(new Wire.Envelope(13, id, 1, 1, 4, 1,
            Control.encodeInput(new Control.Input(3, 3, 3, 40, 40, 66))), System.nanoTime()));
        adapter.tick(); check(adapter.keyPresses.right() && adapter.keyPresses.shift() && !adapter.keyPresses.left());
        check(adapter.getMoveVector().x == -1 && adapter.getMoveVector().y == 0);
        inbox.revoke("focus-lost"); adapter.tick();
        check(adapter.keyPresses.equals(net.minecraft.world.entity.player.Input.EMPTY));
        check(adapter.getMoveVector().equals(net.minecraft.world.phys.Vec2.ZERO));
        var stale = new InputInbox(peer, 1, 2); var staleAdapter = new BridgeClientInput(stale);
        check(stale.receive(new Wire.Envelope(13, id, 1, 2, 3, 1,
            Control.encodeInput(new Control.Input(1, 1, 1, 64, 64, 0))), System.nanoTime() - InputInbox.LEASE_NANOS));
        staleAdapter.tick(); check(staleAdapter.keyPresses.equals(net.minecraft.world.entity.player.Input.EMPTY));
        check(stale.consumedAck() == 1 && stale.fault().equals("stale-queued-input"));
        var uiInbox=new InputInbox(peer,1,3);var allowMovement=new java.util.concurrent.atomic.AtomicBoolean(false);
        var gated=new BridgeClientInput(uiInbox,h->allowMovement.get()?h:0);
        check(uiInbox.receive(new Wire.Envelope(13,id,1,3,2,1,Control.encodeInput(new Control.Input(1,1,1,17,17,0))),System.nanoTime()));
        gated.tick();check(gated.keyPresses.equals(net.minecraft.world.entity.player.Input.EMPTY)&&uiInbox.consumedInput()==1&&uiInbox.fault()==null);
        allowMovement.set(true);gated.tick();check(gated.keyPresses.forward()&&gated.keyPresses.jump());
        uiInbox.revoke("inventory-release");gated.tick();check(gated.keyPresses.equals(net.minecraft.world.entity.player.Input.EMPTY));
        System.out.println("MC_NATIVE_TYPES_PASS real 26.3 Input/ClientInput/Vec2: keys, normalized movement, revoke, stale lease");
    }
}
