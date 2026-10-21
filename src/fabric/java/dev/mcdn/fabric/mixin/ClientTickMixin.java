package dev.mcdn.fabric.mixin;

import dev.mcdn.fabric.FabricProbe;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public abstract class ClientTickMixin {
    @Inject(method="tick",at=@At("TAIL"),require=1)
    private void mcdn$observe(CallbackInfo ci){FabricProbe.clientTick((Minecraft)(Object)this);}
}
