package dev.mcdn.tests;

import java.util.Arrays;
import net.fabricmc.api.EnvType;
import net.fabricmc.loader.impl.launch.knot.Knot;

/** Initialize the real loader and transform classes; never call game main, a client constructor or a world. */
public final class FabricTransformBench {
    private static boolean handler(ClassLoader loader,String name,String marker) throws Exception {
        return Arrays.stream(Class.forName(name,false,loader).getDeclaredMethods()).anyMatch(m->m.getName().contains(marker));
    }
    public static void main(String[] args) throws Exception {
        ClassLoader loader=new Knot(EnvType.CLIENT).init(new String[]{"--gameDir",args[0],"--version","MCDN-transform-only"});
        Class<?> probe=Class.forName("dev.mcdn.fabric.FabricProbe",true,loader);
        Object instance=probe.getDeclaredConstructor().newInstance();
        probe.getMethod("onInitializeClient").invoke(instance);
        boolean lab=System.getProperty("mcdn.lab.manifest")!=null;
        if(lab) {
            var configured=probe.getDeclaredField("configured");configured.setAccessible(true);
            if(!configured.getBoolean(null))throw new AssertionError("isolated lab configuration was refused");
        }
        Class.forName("dev.mcdn.fabric.WorldLayers",false,loader);
        boolean collision=handler(loader,"net.minecraft.world.level.CollisionGetter","mcdn$shapes");
        boolean tick=handler(loader,"net.minecraft.client.Minecraft","mcdn$observe");
        if(instance==null||!collision||!tick)throw new AssertionError("probe or transformed hooks missing: collision="+collision+" tick="+tick);
        System.out.println("FABRIC_TRANSFORM_PASS real Knot/Mixin; probe initializer executed; collision/tick handlers merged; labConfigured="+lab+"; game main not invoked");
    }
}
