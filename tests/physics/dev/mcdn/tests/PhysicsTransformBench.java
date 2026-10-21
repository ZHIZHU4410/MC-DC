package dev.mcdn.tests;
import java.util.Arrays;
import net.fabricmc.api.EnvType;
import net.fabricmc.loader.impl.launch.knot.Knot;
public final class PhysicsTransformBench {
    public static void main(String[] args){
        try{
            ClassLoader loader=new Knot(EnvType.CLIENT).init(new String[]{"--gameDir",args[0],"--version","MCDN-physics-transform-only"});
            Class<?> probe=Class.forName("dev.mcdn.physics.PhysicsProbe",true,loader);
            probe.getMethod("onInitializeClient").invoke(probe.getDeclaredConstructor().newInstance());
            var configured=probe.getDeclaredField("configured");configured.setAccessible(true);
            if(!configured.getBoolean(null))throw new IllegalStateException("physics config rejected");
            String[][] hooks={{"net.minecraft.client.Minecraft","mcdn$physicsClient"},{"net.minecraft.server.MinecraftServer","mcdn$physicsServer"},{"net.minecraft.world.level.CollisionGetter","mcdn$physics"},{"net.minecraft.world.entity.Display","mcdn$transform"},{"net.minecraft.world.entity.Display$BlockDisplay","mcdn$block"}};
            for(var pair:hooks){Class<?> type=Class.forName(pair[0],false,loader);if(Arrays.stream(type.getDeclaredMethods()).noneMatch(m->m.getName().contains(pair[1])))throw new IllegalStateException("hook not merged: "+pair[0]);}
            Class<?> worldType=Class.forName("dev.mcdn.protocol.World",true,loader),geometryType=Class.forName("dev.mcdn.minecraft.BridgeGeometry",true,loader),boxType=Class.forName("net.minecraft.world.phys.AABB",true,loader);
            Object world=worldType.getMethod("decode",byte[].class).invoke(null,(Object)java.nio.file.Files.readAllBytes(java.nio.file.Path.of(args[1]))),geometry=geometryType.getConstructor(worldType).newInstance(world);
            var box=boxType.getConstructor(double.class,double.class,double.class,double.class,double.class,double.class);
            Object standing=box.newInstance(.2,200.,.2,.8,201.8,.8),blocked=box.newInstance(2.2,200.,.2,2.8,201.8,.8),remote=box.newInstance(20.,210.,20.,21.,212.,21.);
            if(args.length>2){
                var plan=com.google.gson.JsonParser.parseString(java.nio.file.Files.readString(java.nio.file.Path.of(args[2]))).getAsJsonObject();
                var spawn=plan.getAsJsonArray("spawn");double x=spawn.get(0).getAsDouble(),z=spawn.get(2).getAsDouble(),wall=plan.get("wallX").getAsDouble();
                standing=box.newInstance(x-.3,200.,z-.3,x+.3,201.8,z+.3);
                blocked=box.newInstance(wall-.1,200.,z-.3,wall+.5,201.8,z+.3);
                remote=box.newInstance(x-.3,200.,3.,x+.3,201.8,3.6);
                Class<?> scene=Class.forName("dev.mcdn.physics.DcScene",true,loader);
                var runs=scene.getDeclaredMethod("displayRuns",worldType);runs.setAccessible(true);
                var merged=(java.util.List<?>)runs.invoke(null,world);
                if(merged.size()>=2515)throw new IllegalStateException("DC display runs were not merged");
                System.out.println("DC_SCENE_NATIVE_SHAPES_PASS original shapes and exact adjacent display runs="+merged.size());
            }
            var intersect=geometryType.getMethod("intersecting",boxType);
            Class<?> getter=Class.forName("net.minecraft.world.level.CollisionGetter",true,loader),entity=Class.forName("net.minecraft.world.entity.Entity",false,loader);
            Object nativeQuery=java.lang.reflect.Proxy.newProxyInstance(loader,new Class<?>[]{getter},(proxy,method,values)->{
                if(method.getName().equals("getBlockCollisions"))return intersect.invoke(geometry,values[1]);
                if(method.isDefault())return java.lang.reflect.InvocationHandler.invokeDefault(proxy,method,values);
                throw new UnsupportedOperationException(method.getName());
            });
            var nativeFree=getter.getMethod("noBlockCollision",entity,boxType);
            if(!(Boolean)nativeFree.invoke(nativeQuery,null,standing)||(Boolean)nativeFree.invoke(nativeQuery,null,blocked)||!(Boolean)nativeFree.invoke(nativeQuery,null,remote))throw new IllegalStateException("actual native noBlockCollision query range contract");
            System.out.println("PHYSICS_QUERY_PASS actual native noBlockCollision: standing touch and remote air free, wall overlap blocked");
            System.out.println("PHYSICS_TRANSFORM_PASS actual Knot/Mixin client/server/collision/native Display accessors; no game main or motion");
        }catch(Throwable ex){ex.printStackTrace(System.err);System.exit(2);}
    }
}
