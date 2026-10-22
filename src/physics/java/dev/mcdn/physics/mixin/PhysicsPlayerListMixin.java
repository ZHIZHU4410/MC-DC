package dev.mcdn.physics.mixin;
import dev.mcdn.physics.PhysicsProbe;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(PlayerList.class)
public abstract class PhysicsPlayerListMixin {
    @Inject(method="remove",at=@At("HEAD"),require=1)
    private void mcdn$physicsRemove(ServerPlayer player,CallbackInfo ci){PhysicsProbe.beforePlayerRemove(player);}
}
