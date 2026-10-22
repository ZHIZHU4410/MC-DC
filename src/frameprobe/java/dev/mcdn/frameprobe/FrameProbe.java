package dev.mcdn.frameprobe;

import com.google.gson.*;
import dev.mcdn.ipc.NativeMailbox;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.systems.RenderSystem;
import net.fabricmc.api.ClientModInitializer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.CameraType;
import net.minecraft.client.Screenshot;
import net.minecraft.client.renderer.GameRenderer;
import org.joml.Matrix4f;
import org.slf4j.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** Bounded diagnostic of the actual MC render target. World-color PNGs, never MCDF player layers. */
public final class FrameProbe implements ClientModInitializer {
    private static final Logger LOG=LoggerFactory.getLogger("MCDN-FRAME");
    private static final AtomicReference<Job> ready=new AtomicReference<>();
    record Frozen(long frameId,String dimension,long nativeGameTime,int playerTick,
        double footX,double footY,double footZ,double cameraX,double cameraY,double cameraZ,
        float yaw,float pitch,float partialTick,float[] viewRotation,float[] projection,
        int sourceWidth,int sourceHeight,int downscale,String cameraType,long requestedNanos,long captureQpc,long streamEpoch,String screenType,String worldVisuals) {}
    private static java.util.function.Supplier<String> sceneLabel=()->"native-diagnostic";
    public static void sceneLabel(java.util.function.Supplier<String> label){sceneLabel=Objects.requireNonNull(label);}
    private record Job(Frozen context,NativeImage image,long completedNanos,long readyQpc) {}
    private static Path game,output;
    private static volatile boolean configured;
    private static boolean inFlight,failed,hookObserved;
    private static long next,id;
    private static int requests;
    private static double captureMinY=-1_000_000;
    private static CameraType captureCameraType;
    private static LiveColorSession live;
    private static Object lastLevel;
    private static long streamEpoch,liveStarted;
    private static final long LIVE_CAPTURE_LIMIT_NANOS=600_000_000_000L;
    @Override public void onInitializeClient() {
        String manifest=System.getProperty("mcdn.lab.manifest");if(manifest==null)return;
        try {
            var config=JsonParser.parseString(Files.readString(Path.of(manifest))).getAsJsonObject();
            game=Path.of(config.get("gameDir").getAsString()).toRealPath();
            if(!Files.isRegularFile(game.resolve("MCDN_ISOLATED_LAB")))throw new IllegalArgumentException("lab marker missing");
            if(config.has("captureMinY"))captureMinY=config.get("captureMinY").getAsDouble();
            if(!Double.isFinite(captureMinY))throw new IllegalArgumentException("capture gate must be finite");
            if(config.has("captureCameraType"))captureCameraType=CameraType.valueOf(config.get("captureCameraType").getAsString());
            // Separate, bounded first GPU diagnostic; no changes to the v0.5 geometry protocol or observations.
            output=Path.of(config.get("outputDir").getAsString()).toAbsolutePath().normalize().resolve("world-color").resolve(UUID.randomUUID().toString());
            Files.createDirectories(output);
            live=LiveColorSession.read(game,output.getParent().getParent().getParent());configured=true;
            Thread worker=new Thread(FrameProbe::writeLoop,"MCDN-frame-files");worker.setDaemon(true);worker.start();
            LOG.info("MCDN_FRAME_PROBE_INITIALIZED source={} output={}; limit={}; no input takeover",FrameProbe.class.getProtectionDomain().getCodeSource().getLocation(),output,live==null?"12 recorded frames":"600s live capture");
        }catch(Exception ex){LOG.error("MCDN frame probe disabled: {}",ex.toString());}
    }
    public static void afterRender(GameRenderer renderer) {
        if(!hookObserved){hookObserved=true;LOG.info("MCDN_FRAME_HOOK_OBSERVED thread={}; bounded diagnostic only",Thread.currentThread().getName());}
        if(!configured||failed||inFlight||(live==null&&requests>=12)||System.nanoTime()<next)return;
        if(live!=null&&liveStarted!=0&&System.nanoTime()-liveStarted>LIVE_CAPTURE_LIMIT_NANOS){configured=false;LOG.info("MCDN_LIVE_COLOR_PRODUCER_STOPPED duration bound");return;}
        try {
            RenderSystem.assertOnRenderThread();Minecraft mc=Minecraft.getInstance();
            if(mc.level==null||mc.player==null||mc.isPaused()||mc.getSingleplayerServer()==null||
               !mc.gameDirectory.toPath().toAbsolutePath().normalize().equals(game))return;
            if(mc.player.getY()<captureMinY||(captureCameraType!=null&&!(live!=null&&live.viewControl)&&mc.options.getCameraType()!=captureCameraType))return;
            // MC26.3 actually writes/uses shouldRenderLevel. readyForLevelRendering is an unused,
            // never-written field in this exact game build and stays false even in a live world.
            var state=renderer.gameRenderState();if(!state.shouldRenderLevel)return;
            var levelState=state.levelRenderState;var camera=levelState.cameraRenderState;
            if(!camera.initialized||!levelState.playerRenderState.hasPlayer)return;
            var target=renderer.mainRenderTarget();var texture=target.getColorTexture();
            if(texture==null)return;
            if(texture.getFormat()!=com.mojang.renderpearl.api.GpuFormat.RGBA8_UNORM) {
                failed=true;LOG.error("MCDN frame capture disabled: unsupported native format {}",texture.getFormat());return;
            }
            // At most 32MiB native staging for this diagnostic, and one in-flight GPU request.
            if(target.width<1||target.height<1||(long)target.width*target.height>3840L*2160)return;
            // Read the bounded native surface once; arbitrary-size CPU fitting happens on the file worker.
            // E.g. 2560x1494 has no integral divisor that would fit the old <=1024 rule.
            int factor=1;
            var level=mc.level;var player=mc.player;var server=mc.getSingleplayerServer();
            if(lastLevel!=level){lastLevel=level;streamEpoch++;}
            String cameraType=mc.options.getCameraType().name();float partial=camera.cameraEntityPartialTicks;
            // Interpolated native foot position at this extraction's partial tick; never resampled in the callback.
            var foot=player.getPosition(partial);var pos=camera.pos;
            float[] view=new Matrix4f(camera.viewRotationMatrix).get(new float[16]),projection=new Matrix4f(camera.projectionMatrix).get(new float[16]);
            // Initial native render extraction can precede a valid interpolated camera/pose.
            // Skip that transient sample; never serialize Infinity or poison all later captures.
            if(!Double.isFinite(foot.x)||!Double.isFinite(foot.y)||!Double.isFinite(foot.z)||!Double.isFinite(pos.x)||!Double.isFinite(pos.y)||!Double.isFinite(pos.z)||!Float.isFinite(partial)||!Float.isFinite(camera.yRot)||!Float.isFinite(camera.xRot))return;
            for(float value:view)if(!Float.isFinite(value))return;
            for(float value:projection)if(!Float.isFinite(value))return;
            Frozen frozen=new Frozen(++id,level.dimension().toString(),levelState.gameTime,player.tickCount,foot.x,foot.y,foot.z,pos.x,pos.y,pos.z,
                camera.yRot,camera.xRot,partial,view,projection,target.width,target.height,factor,cameraType,System.nanoTime(),live==null?0:NativeMailbox.qpc(),streamEpoch,mc.gui.screen()==null?"none":mc.gui.screen() instanceof net.minecraft.client.gui.screens.inventory.InventoryScreen?"inventory":"other",sceneLabel.get());
            inFlight=true;requests++;if(liveStarted==0)liveStarted=System.nanoTime();next=System.nanoTime()+(live==null?2_000_000_000L:200_000_000L);
            Screenshot.takeScreenshot(target,factor,image->{
                try {
                    RenderSystem.assertOnRenderThread();
                    if(!configured||failed||mc.level!=level||mc.player!=player||mc.getSingleplayerServer()!=server||
                       !mc.options.getCameraType().name().equals(cameraType)||
                       !sceneLabel.get().equals(frozen.worldVisuals)||
                       target!=renderer.mainRenderTarget()||target.width!=frozen.sourceWidth||target.height!=frozen.sourceHeight||
                       System.nanoTime()-frozen.requestedNanos>5_000_000_000L) {image.close();return;}
                    Job replaced=ready.getAndSet(new Job(frozen,image,System.nanoTime(),live==null?0:NativeMailbox.qpc()));if(replaced!=null)replaced.image.close();
                }catch(Exception ex){image.close();failed=true;LOG.error("MCDN frame readback refused: {}",ex.toString());}
                finally{inFlight=false;}
            });
        }catch(Exception ex){failed=true;LOG.error("MCDN frame capture disabled: {}",ex.toString());}
    }
    private static void liveLoop() {
        try(LiveColorSession session=live){
            session.open();LOG.info("MCDN_LIVE_COLOR_OPEN session={}; native GPU producer only",session.session);
            while(configured&&!session.stopped()){
                Job job=ready.getAndSet(null);
                if(job==null){Thread.sleep(10);continue;}
                double scale=Math.min(1.0,(double)session.maxEdge/Math.max(job.image.getWidth(),job.image.getHeight()));
                int w=Math.max(1,(int)Math.round(job.image.getWidth()*scale)),h=Math.max(1,(int)Math.round(job.image.getHeight()*scale));
                try(NativeImage source=job.image;NativeImage image=new NativeImage(source.format(),w,h,false)){
                    source.resizeSubRectTo(0,0,source.getWidth(),source.getHeight(),image);
                    session.publish(job.context,image,job.readyQpc);
                }
            }
            LOG.info("MCDN_LIVE_COLOR_PRODUCER_STOPPED session={}",session.session);
        }catch(Exception ex){LOG.error("MCDN live color disabled: {}",ex.toString());}
        finally{configured=false;Job remaining=ready.getAndSet(null);if(remaining!=null)remaining.image.close();}
    }
    private static void writeLoop() {
        if(live!=null){liveLoop();return;}
        while(configured) {
            Job job=ready.getAndSet(null);
            if(job==null){try{Thread.sleep(50);}catch(InterruptedException ex){Thread.currentThread().interrupt();return;}continue;}
            FrameSize size=FrameSize.fit(job.image.getWidth(),job.image.getHeight());
            try(NativeImage source=job.image;NativeImage image=new NativeImage(source.format(),size.width(),size.height(),false)) {
                source.resizeSubRectTo(0,0,source.getWidth(),source.getHeight(),image);
                Frozen f=job.context;String name="frame-"+f.frameId+".png";Path temporary=output.resolve(name+".tmp"),finalPath=output.resolve(name);
                image.writeToFile(temporary);Files.move(temporary,finalPath,StandardCopyOption.ATOMIC_MOVE);
                var meta=new JsonObject();meta.addProperty("kind","native-mc-world-color-probe");meta.addProperty("frameId",Long.toUnsignedString(f.frameId));
                meta.addProperty("file",name);meta.addProperty("sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(finalPath))));
                meta.addProperty("source","MC26.3 GameRenderer.mainRenderTarget / Screenshot async GPU callback");
                meta.addProperty("captureSchema","world-color-probe-2");
                meta.addProperty("sourceWidth",f.sourceWidth);meta.addProperty("sourceHeight",f.sourceHeight);meta.addProperty("gpuDownscale",f.downscale);
                meta.addProperty("outputResize","NativeImage.resizeSubRectTo CPU linear after GPU callback");
                meta.addProperty("width",image.getWidth());meta.addProperty("height",image.getHeight());
                meta.addProperty("fullScene",true);meta.addProperty("includesHud",true);meta.addProperty("playerLayer",false);meta.addProperty("eligibleForControl",false);
                meta.addProperty("nativeDimension",f.dimension);meta.addProperty("bridgeContextPaired",false);
                meta.addProperty("worldVisuals",f.worldVisuals);
                meta.addProperty("note","native MC full-scene diagnostic; geometry provenance requires separate paired evidence; not a MODE/MCDF ready frame");
                meta.addProperty("nativeGameTime",Long.toUnsignedString(f.nativeGameTime));meta.addProperty("nativePlayerTick",f.playerTick);
                meta.addProperty("footX",f.footX);meta.addProperty("footY",f.footY);meta.addProperty("footZ",f.footZ);
                meta.addProperty("cameraX",f.cameraX);meta.addProperty("cameraY",f.cameraY);meta.addProperty("cameraZ",f.cameraZ);
                meta.addProperty("cameraYaw",f.yaw);meta.addProperty("cameraPitch",f.pitch);meta.addProperty("partialTick",f.partialTick);meta.addProperty("cameraType",f.cameraType);
                meta.add("viewRotationColumnMajor",new Gson().toJsonTree(f.viewRotation));meta.add("projectionColumnMajor",new Gson().toJsonTree(f.projection));
                meta.addProperty("requestedNanoTime",Long.toString(f.requestedNanos));meta.addProperty("completedNanoTime",Long.toString(job.completedNanos));
                meta.addProperty("clock","same-JVM nanoTime diagnostic only; not cross-process QPC latency");
                String encoded=new GsonBuilder().setPrettyPrinting().create().toJson(meta);
                Files.writeString(output.resolve("frame-"+f.frameId+".json"),encoded);
                Files.writeString(output.resolve("latest.json.tmp"),encoded);Files.move(output.resolve("latest.json.tmp"),output.resolve("latest.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
                LOG.info("MCDN_NATIVE_WORLD_COLOR_WRITTEN frame={} nativeTick={} image={}x{}; no bridge/player-layer/control claim",f.frameId,f.nativeGameTime,image.getWidth(),image.getHeight());
            }catch(Exception ex){configured=false;LOG.error("MCDN frame export disabled: {}",ex.toString());}
        }
        Job remaining=ready.getAndSet(null);if(remaining!=null)remaining.image.close();
    }
}
