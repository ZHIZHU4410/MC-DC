package dev.mcdn.fabric.mixin;

import dev.mcdn.fabric.WorldLayers;
import net.minecraft.world.level.CollisionGetter;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.shapes.*;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(CollisionGetter.class)
public interface CollisionMixin {
    @Inject(method="getBlockCollisionsFromContext",at=@At("HEAD"),cancellable=true,require=1)
    default void mcdn$shapes(CollisionContext context,AABB box,CallbackInfoReturnable<Iterable<VoxelShape>> cir) {
        var layer=WorldLayers.lookup(this); if(layer!=null)cir.setReturnValue(layer.shapes());
    }
}
