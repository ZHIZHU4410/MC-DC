package dev.mcdn.physics.mixin;
import dev.mcdn.physics.DcVisuals;
import net.minecraft.client.renderer.SkyRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(SkyRenderer.class)
public abstract class DcVisualSkyMixin {
    @Inject(method="render",at=@At("HEAD"),cancellable=true,require=1)
    private void mcdn$dcVisualSky(CallbackInfo ci){if(DcVisuals.active())ci.cancel();}
}
