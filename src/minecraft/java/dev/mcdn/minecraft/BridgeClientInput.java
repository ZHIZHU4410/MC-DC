package dev.mcdn.minecraft;

import dev.mcdn.protocol.InputInbox;
import net.minecraft.client.player.ClientInput;
import net.minecraft.world.entity.player.Input;
import net.minecraft.world.phys.Vec2;

/**
 * Compile-checked against the user's MC 26.3 JAR. No loader entrypoint or automatic install.
 * A future mode adapter must save/restore LocalPlayer.input and enforce world/frame readiness.
 */
public final class BridgeClientInput extends ClientInput {
    private final InputInbox inbox;
    private final java.util.function.IntUnaryOperator nativeGate;
    public BridgeClientInput(InputInbox inbox) { this(inbox,java.util.function.IntUnaryOperator.identity()); }
    public BridgeClientInput(InputInbox inbox,java.util.function.IntUnaryOperator nativeGate) { this.inbox = java.util.Objects.requireNonNull(inbox);this.nativeGate=java.util.Objects.requireNonNull(nativeGate); }
    @Override public void tick() { inbox.tick(System.nanoTime(),held->{int filtered=nativeGate.applyAsInt(held);if((filtered&~127)!=0)throw new IllegalStateException("native input gate returned invalid mask");install(filtered);}); }
    private void install(int held) {
        keyPresses = new Input((held & 1) != 0, (held & 2) != 0, (held & 4) != 0, (held & 8) != 0,
            (held & 16) != 0, (held & 32) != 0, (held & 64) != 0);
        float forward = (keyPresses.forward() ? 1 : 0) - (keyPresses.backward() ? 1 : 0);
        float left = (keyPresses.left() ? 1 : 0) - (keyPresses.right() ? 1 : 0);
        moveVector = new Vec2(left, forward).normalized();
    }
}
