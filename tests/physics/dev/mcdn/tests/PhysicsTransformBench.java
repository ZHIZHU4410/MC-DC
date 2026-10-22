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
            String[][] hooks={{"net.minecraft.client.Minecraft","mcdn$physicsClient"},{"net.minecraft.server.MinecraftServer","mcdn$physicsServer"},{"net.minecraft.world.level.CollisionGetter","mcdn$physics"},{"net.minecraft.world.entity.Display","mcdn$transform"},{"net.minecraft.world.entity.Display$BlockDisplay","mcdn$block"},
                {"net.minecraft.client.renderer.GameRenderer","mcdn$dcVisualExtract"},{"net.minecraft.client.renderer.SkyRenderer","mcdn$dcVisualSky"},{"net.minecraft.client.renderer.CloudRenderer","mcdn$dcVisualCloud"},{"net.minecraft.client.renderer.fog.FogRenderer","mcdn$dcVisualFog"}};
            for(var pair:hooks){Class<?> type=Class.forName(pair[0],false,loader);if(Arrays.stream(type.getDeclaredMethods()).noneMatch(m->m.getName().contains(pair[1])))throw new IllegalStateException("hook not merged: "+pair[0]);}
            Class<?> server=Class.forName("net.minecraft.server.MinecraftServer",false,loader);
            if(Arrays.stream(server.getDeclaredMethods()).noneMatch(m->m.getName().contains("mcdn$physicsStop")))throw new IllegalStateException("pre-save lab restoration hook missing");
            Class<?> players=Class.forName("net.minecraft.server.players.PlayerList",false,loader);
            if(Arrays.stream(players.getDeclaredMethods()).noneMatch(m->m.getName().contains("mcdn$physicsRemove")))throw new IllegalStateException("pre-player-save lab restoration hook missing");
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
                if(plan.has("nativeBlocks")&&plan.get("nativeBlocks").getAsBoolean()){
                    var install=probe.getDeclaredMethod("install",Class.forName("net.minecraft.world.level.Level",false,loader));install.setAccessible(true);install.invoke(null,(Object)null);
                    var layers=probe.getDeclaredField("layers");layers.setAccessible(true);
                    if(!((java.util.List<?>)((java.util.concurrent.atomic.AtomicReference<?>)layers.get(null)).get()).isEmpty())throw new IllegalStateException("native block scene installed a diagnostic collision override");
                    System.out.println("DC_NATIVE_BLOCK_NO_OVERRIDE_PASS exact integer cell grid; native player motion still pending");
                }
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
            visualStateCheck(loader);
            System.out.println("PHYSICS_TRANSFORM_PASS actual Knot/Mixin client/server/collision/native Display accessors; no game main or motion");
        }catch(Throwable ex){ex.printStackTrace(System.err);System.exit(2);}
    }
    @SuppressWarnings("unchecked")
    private static void visualStateCheck(ClassLoader loader)throws Exception {
        Class<?> visual=Class.forName("dev.mcdn.physics.DcVisuals",true,loader),stateType=Class.forName("net.minecraft.client.renderer.state.GameRenderState",true,loader);
        Object state=stateType.getConstructor().newInstance(),level=stateType.getField("levelRenderState").get(state),gui=stateType.getField("guiRenderState").get(state);
        Object player=level.getClass().getField("playerRenderState").get(level),hands=player.getClass().getField("firstPersonHandsAndItems").get(player);
        var entities=(java.util.List<Object>)level.getClass().getField("entityRenderStates").get(level);
        Object nativeEntity=Class.forName("net.minecraft.client.renderer.entity.state.EntityRenderState",true,loader).getConstructor().newInstance();entities.add(nativeEntity);
        stateType.getField("shouldRenderLevel").setBoolean(state,true);
        var active=visual.getDeclaredField("active");active.setAccessible(true);
        var color=visual.getDeclaredField("fogColor");color.setAccessible(true);color.setInt(null,0x123456);
        var extract=visual.getMethod("extracted",stateType);
        extract.invoke(null,state);if(entities.size()!=1)throw new IllegalStateException("inactive visual mode changed native entities");
        active.setBoolean(null,true);
        try{
            extract.invoke(null,state);
            if(!entities.isEmpty()||stateType.getField("guiRenderState").get(state)!=gui||player.getClass().getField("firstPersonHandsAndItems").get(player)!=hands)
                throw new IllegalStateException("native world/hand/GUI separation");
            Class<?> fogType=Class.forName("net.minecraft.client.renderer.fog.FogData",true,loader);
            Object fog=fogType.getConstructor().newInstance();visual.getMethod("fog",fogType).invoke(null,fog);
            if(fogType.getField("environmentalEnd").getFloat(fog)!=48)throw new IllegalStateException("native source fog distance");
            Object rgb=fogType.getField("color").get(fog);float red=(Float)rgb.getClass().getMethod("x").invoke(rgb);
            if(Math.abs(red-0x12/255f)>1e-6)throw new IllegalStateException("DC fog RGB order");
        }finally{var release=visual.getDeclaredMethod("release");release.setAccessible(true);release.invoke(null);}
        Object light=stateType.getField("lightmapRenderState").get(state);light.getClass().getField("needsUpdate").setBoolean(light,false);
        entities.add(nativeEntity);extract.invoke(null,state);if(entities.size()!=1||!light.getClass().getField("needsUpdate").getBoolean(light))throw new IllegalStateException("released mode still suppresses native world or leaves stale DC lighting");
        long cloudHooks=Arrays.stream(Class.forName("net.minecraft.client.renderer.CloudRenderer",false,loader).getDeclaredMethods()).filter(m->m.getName().contains("mcdn$dcVisualCloud")).count();
        if(cloudHooks!=2)throw new IllegalStateException("both native cloud passes must be gated");
        System.out.println("DC_VISUAL_STATE_PASS actual extracted native types; world entities isolated; hand/GUI references preserved; fog RGB; release; both cloud passes transformed; no GPU evidence");
    }
}
