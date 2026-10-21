package dev.mcdn.frameprobe.mixin;
import dev.mcdn.frameprobe.FrameProbe;
import net.minecraft.client.renderer.GameRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(GameRenderer.class)
public abstract class FrameRenderMixin {
    @Inject(method="render",at=@At("TAIL"),require=1)
    private void mcdn$captureColor(CallbackInfo ci){FrameProbe.afterRender((GameRenderer)(Object)this);}
}
