package dev.mcdn.physics.mixin;
import net.minecraft.world.entity.Display;
import com.mojang.math.Transformation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;
@Mixin(Display.class)
public interface DisplayAccess {
    @Invoker("setTransformation") void mcdn$transform(Transformation value);
    @Invoker("setWidth") void mcdn$width(float value);
    @Invoker("setHeight") void mcdn$height(float value);
}
