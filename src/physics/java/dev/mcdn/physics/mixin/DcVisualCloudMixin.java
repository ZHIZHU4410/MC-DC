package dev.mcdn.physics.mixin;
import dev.mcdn.physics.DcVisuals;
import net.minecraft.client.renderer.CloudRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(CloudRenderer.class)
public abstract class DcVisualCloudMixin {
    @Inject(method="render(Lnet/minecraft/client/CloudStatus;Lcom/mojang/renderpearl/api/commands/RenderPass;)V",at=@At("HEAD"),cancellable=true,require=1)
    private void mcdn$dcVisualCloud(CallbackInfo ci){if(DcVisuals.active())ci.cancel();}
    @Inject(method="renderOit",at=@At("HEAD"),cancellable=true,require=1)
    private void mcdn$dcVisualCloudOit(CallbackInfo ci){if(DcVisuals.active())ci.cancel();}
}
