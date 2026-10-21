package dev.mcdn.tests;
import java.util.Arrays;
import net.fabricmc.api.EnvType;
import net.fabricmc.loader.impl.launch.knot.Knot;

/** Load and transform installed game types, without game main, client construction or GPU calls. */
public final class FrameTransformBench {
    public static void main(String[] args) {
        try {
            ClassLoader loader=new Knot(EnvType.CLIENT).init(new String[]{"--gameDir",args[0],"--version","MCDN-frame-transform-only"});
            Class<?> type=Class.forName("dev.mcdn.frameprobe.FrameProbe",true,loader);
            type.getMethod("onInitializeClient").invoke(type.getDeclaredConstructor().newInstance());
            var configured=type.getDeclaredField("configured");configured.setAccessible(true);
            if(!configured.getBoolean(null))throw new IllegalStateException("marked lab config not accepted");
            Class<?> renderer=Class.forName("net.minecraft.client.renderer.GameRenderer",false,loader);
            if(Arrays.stream(renderer.getDeclaredMethods()).noneMatch(m->m.getName().contains("mcdn$captureColor")))throw new IllegalStateException("render hook not merged");
            Class.forName("dev.mcdn.frameprobe.FrameProbe$Frozen",false,loader);
            System.out.println("FRAME_TRANSFORM_PASS actual Knot/Mixin initializer + GameRenderer hook; no game main/client/GPU");
        }catch(Throwable ex){System.err.println("FRAME_TRANSFORM_FAIL "+ex);ex.printStackTrace(System.err);System.exit(2);}
    }
}
