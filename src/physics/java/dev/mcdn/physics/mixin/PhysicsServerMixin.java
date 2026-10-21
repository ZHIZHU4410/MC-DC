package dev.mcdn.physics.mixin;
import dev.mcdn.physics.PhysicsProbe;
import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(MinecraftServer.class)
public abstract class PhysicsServerMixin {
    @Inject(method="tickServer",at=@At("TAIL"),require=1)
    private void mcdn$physicsServer(CallbackInfo ci){PhysicsProbe.serverTick((MinecraftServer)(Object)this);}
}
