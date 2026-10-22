package dev.mcdn.minecraft;

import dev.mcdn.protocol.InputInbox;
import dev.mcdn.protocol.ModeGate;
import dev.mcdn.protocol.World;
import net.minecraft.client.player.ClientInput;
import net.minecraft.client.player.LocalPlayer;

/** Game-thread save/restore of the actual input object. No automatic loader or Hero hook. */
public final class BridgeInputBinding implements ModeGate.Binding {
    public interface Slot { ClientInput get(); void set(ClientInput input); }
    public static Slot slot(LocalPlayer player) {
        return new Slot() {
            public ClientInput get() { return player.input; }
            public void set(ClientInput input) { player.input = input; }
        };
    }
    private final Thread owner = Thread.currentThread();
    private final Slot slot;
    private final InputInbox inbox;
    private final BridgeClientInput bridge;
    private ClientInput original;
    private boolean attempted, installed;
    public BridgeInputBinding(Slot slot, InputInbox inbox) {
        this(slot,inbox,java.util.function.IntUnaryOperator.identity());
    }
    public BridgeInputBinding(Slot slot,InputInbox inbox,java.util.function.IntUnaryOperator nativeGate){
        this.slot = java.util.Objects.requireNonNull(slot); this.inbox = java.util.Objects.requireNonNull(inbox);
        bridge = new BridgeClientInput(inbox,nativeGate);
    }
    private void thread() { if (Thread.currentThread() != owner) throw new IllegalStateException("binding game thread only"); }
    @Override public boolean matches(World.Stamp stamp, long mode) {
        return inbox.matches(stamp.session(), stamp.epoch(), mode) && inbox.fault() == null;
    }
    @Override public boolean enter() {
        thread(); if (attempted) return installed;
        attempted = true; original = java.util.Objects.requireNonNull(slot.get());
        // Preserve original even if an adapter throws after partially setting the slot.
        slot.set(bridge); installed = true; return true;
    }
    @Override public boolean release() {
        thread(); inbox.revoke("mode-release"); bridge.tick();
        if (original == null) return true;
        ClientInput current = slot.get();
        if (current == original) { installed = false; return true; }
        if (current != bridge) return false; // Another owner changed the slot: do not clobber it.
        slot.set(original); installed = false; return true;
    }
    @Override public String fault() { return inbox.fault(); }
}
