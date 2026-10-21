package dev.mcdn.physics.mixin;
import dev.mcdn.physics.PhysicsProbe;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(Minecraft.class)
public abstract class PhysicsClientMixin {
    @Inject(method="tick",at=@At("TAIL"),require=1)
    private void mcdn$physicsClient(CallbackInfo ci){PhysicsProbe.clientTick((Minecraft)(Object)this);}
}
