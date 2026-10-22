package dev.mcdn.physics;

import com.google.gson.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.fog.FogData;
import net.minecraft.client.renderer.state.GameRenderState;
import net.minecraft.resources.Identifier;
import org.joml.Vector4f;
import org.joml.Vector3f;

/** Private source-art theme on the native collision scene. No simulation or global option overrides. */
public final class DcVisuals {
    private static boolean configured,verified,lightingOwned;
    private static volatile boolean active;
    private static String packId,packDigest;
    private static int fogColor,ambientColor;
    private static long extractedFrames,removedEntities;
    private static JsonObject configuration;
    private DcVisuals() {}

    static void configure(Path manifest,String expected,String scene,Path game)throws Exception {
        if(Files.size(manifest)>32768)throw new IllegalArgumentException("visual configuration size");
        byte[] data=Files.readAllBytes(manifest);
        if(!hash(data).equals(expected))throw new IllegalArgumentException("visual configuration digest");
        var cfg=JsonParser.parseString(new String(data,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        if(!cfg.get("kind").getAsString().equals("owned-dc-visual-scene-1")||
            !cfg.get("sceneDigest").getAsString().equals(scene)||
            !cfg.get("atlasName").getAsString().equals("prison")||cfg.get("productionModeGranted").getAsBoolean())
            throw new IllegalArgumentException("DC visual source/geometry binding");
        String name=cfg.get("packFile").getAsString();
        if(!name.equals("mcdn-dc-prison.zip"))throw new IllegalArgumentException("owned visual pack filename");
        Path pack=game.resolve("resourcepacks").resolve(name).toRealPath();
        if(!pack.getParent().equals(game.resolve("resourcepacks").toRealPath())||Files.size(pack)>4_194_304)
            throw new IllegalArgumentException("private visual pack path/size");
        packDigest=cfg.get("packSha256").getAsString();
        if(!hash(Files.readAllBytes(pack)).equals(packDigest))throw new IllegalArgumentException("private visual pack changed");
        packId=cfg.get("packId").getAsString();
        if(!packId.equals("file/"+name))throw new IllegalArgumentException("visual pack identity");
        fogColor=cfg.get("fogColor").getAsInt();
        ambientColor=cfg.get("ambientColor").getAsInt();
        if(fogColor<0||fogColor>0xffffff||ambientColor<0||ambientColor>0xffffff)throw new IllegalArgumentException("DC lighting RGB");
        configuration=cfg;configured=true;
    }

    /** Once per scene, before any native world mutation. No per-frame file reads. */
    static void verifyResources(Minecraft mc) {
        if(!configured||verified)return;
        var selected=new ArrayList<>(mc.getResourcePackRepository().getSelectedIds());
        if(selected.isEmpty()||!selected.getLast().equals(packId))throw new IllegalStateException("DC material pack is not the highest selected pack");
        for(var entry:configuration.getAsJsonObject("resources").entrySet()){
            String name=entry.getKey();if(!name.startsWith("assets/"))continue;
            String[] path=name.substring(7).split("/",2);
            var resource=mc.getResourceManager().getResource(Identifier.fromNamespaceAndPath(path[0],path[1])).orElseThrow();
            if(!resource.sourcePackId().equals(packId))throw new IllegalStateException("DC material resource overridden: "+name);
        }
        verified=true;
    }
    static void activate(){if(configured&&!verified)throw new IllegalStateException("DC visual resources unverified");active=configured;}
    static void release(){active=false;}
    public static boolean active(){return active;}
    public static String description(){return active?"dc-prison-source-materials":"native-diagnostic";}
    static JsonObject evidence(){
        var value=new JsonObject();value.addProperty("kind","dc-visual-layer-state");value.addProperty("configured",configured);
        value.addProperty("active",active);value.addProperty("resourcesVerified",verified);value.addProperty("packSha256",packDigest);
        value.addProperty("extractedFrames",extractedFrames);value.addProperty("removedNativeEntities",removedEntities);
        value.addProperty("thirdPersonDcAvatarImplemented",false);return value;
    }

    /** Operate on the extracted world state. First-person hand and GUI state are preserved. */
    public static void extracted(GameRenderState state){
        if(!active&&lightingOwned){state.lightmapRenderState.needsUpdate=true;lightingOwned=false;}
        if(!active||!state.shouldRenderLevel)return;
        var level=state.levelRenderState;
        removedEntities+=level.entityRenderStates.size();level.entityRenderStates.clear();
        level.blockEntityRenderStates.clear();level.particlesRenderState.reset();level.weatherRenderState.reset();
        level.cloudColor=0;level.shouldShowEntityOutlines=false;
        var light=state.lightmapRenderState;light.needsUpdate=true;lightingOwned=true;
        light.skyFactor=0;light.blockFactor=0;light.brightness=0;light.darknessEffectScale=0;
        light.nightVisionEffectIntensity=0;light.bossOverlayWorldDarkening=0;
        light.ambientColor=new Vector3f(((ambientColor>>16)&255)/255f,((ambientColor>>8)&255)/255f,(ambientColor&255)/255f);
        extractedFrames++;
    }
    public static void fog(FogData fog){
        if(!active)return;
        fog.color=new Vector4f(((fogColor>>16)&255)/255f,((fogColor>>8)&255)/255f,(fogColor&255)/255f,1);
        fog.environmentalStart=24;fog.environmentalEnd=48;fog.renderDistanceStart=24;fog.renderDistanceEnd=48;
        fog.skyEnd=48;fog.cloudEnd=48;
    }
    private static String hash(byte[] data)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));}
}
