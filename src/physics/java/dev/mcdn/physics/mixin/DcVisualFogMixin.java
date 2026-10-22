package dev.mcdn.physics.mixin;
import dev.mcdn.physics.DcVisuals;
import net.minecraft.client.renderer.fog.*;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(FogRenderer.class)
public abstract class DcVisualFogMixin {
    @Inject(method="setupFog",at=@At("RETURN"),require=1)
    private void mcdn$dcVisualFog(CallbackInfoReturnable<FogData> ci){DcVisuals.fog(ci.getReturnValue());}
}
