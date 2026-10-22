package dev.mcdn.physics.mixin;
import dev.mcdn.physics.DcVisuals;
import net.minecraft.client.renderer.GameRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(GameRenderer.class)
public abstract class DcVisualExtractMixin {
    @Inject(method="extract",at=@At("TAIL"),require=1)
    private void mcdn$dcVisualExtract(CallbackInfo ci){DcVisuals.extracted(((GameRenderer)(Object)this).gameRenderState());}
}
