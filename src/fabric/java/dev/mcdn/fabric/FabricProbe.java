package dev.mcdn.fabric;

import net.fabricmc.api.ClientModInitializer;
import net.minecraft.client.Minecraft;
import net.minecraft.world.level.storage.LevelResource;
import dev.mcdn.protocol.World;
import dev.mcdn.minecraft.BridgeGeometry;
import com.google.gson.*;
import org.slf4j.*;
import org.spongepowered.asm.mixin.MixinEnvironment;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.*;

/** Isolated lab diagnostic only. Never installs input or acknowledges carrier/frame readiness. */
public final class FabricProbe implements ClientModInitializer {
    private static final Logger LOG=LoggerFactory.getLogger("MCDN");
    private record Candidate(World world,JsonObject metadata) {}
    private static final AtomicReference<Candidate> pending=new AtomicReference<>();
    private static final AtomicReference<JsonObject> observation=new AtomicReference<>();
    private static final AtomicReference<String> serverApplied=new AtomicReference<>();
    private record ServerInstall(Candidate candidate,Object clientIdentity,long generation) {}
    private static final AtomicReference<ServerInstall> installed=new AtomicReference<>();
    private static final AtomicLong generation=new AtomicLong(),serverQueries=new AtomicLong();
    private static final AtomicBoolean queryRequested=new AtomicBoolean();
    private static Path labGame,sourceRoot,output;
    private static boolean configured;
    private static String appliedDigest;
    private static long ticks;
    private static boolean tickObserved;
    @Override public void onInitializeClient() {
        LOG.info("MCDN Fabric probe 0.5.0 initialized; input takeover disabled");
        boolean collisionHook=Arrays.stream(net.minecraft.world.level.CollisionGetter.class.getDeclaredMethods()).anyMatch(m->m.getName().contains("mcdn$shapes"));
        boolean tickHook=Arrays.stream(Minecraft.class.getDeclaredMethods()).anyMatch(m->m.getName().contains("mcdn$observe"));
        LOG.info("MCDN_LOAD_CHECK collisionMixin={} tickMixin={} source={}",collisionHook,tickHook,getClass().getProtectionDomain().getCodeSource().getLocation());
        String manifest=System.getProperty("mcdn.lab.manifest"); if(manifest==null)return;
        try {
            var config=JsonParser.parseString(Files.readString(Path.of(manifest))).getAsJsonObject();
            labGame=Path.of(config.get("gameDir").getAsString()).toRealPath();
            sourceRoot=Path.of(config.get("dcSourceRoot").getAsString()).toRealPath();
            output=Path.of(config.get("outputDir").getAsString()).toAbsolutePath().normalize(); Files.createDirectories(output);
            if(!Files.isRegularFile(labGame.resolve("MCDN_ISOLATED_LAB")))throw new IllegalArgumentException("missing isolated lab marker");
            if(!MixinEnvironment.Feature.INJECTORS_IN_INTERFACE_MIXINS.isEnabled())throw new IllegalStateException("interface collision injectors unavailable");
            configured=true; Thread worker=new Thread(FabricProbe::watch,"MCDN-probe-files");worker.setDaemon(true);worker.start();
        }catch(Exception ex){LOG.error("MCDN probe disabled: {}",ex.toString());}
    }
    private static void watch() {
        String last=null;
        while(configured) {
            try {
                Path latest=null;
                try(var folders=Files.list(sourceRoot)) {
                    for(var p:folders.filter(Files::isDirectory).toList()) {
                        if(!p.getFileName().toString().matches("[a-f0-9]{32}"))continue;
                        Path meta=p.resolve("latest.json");
                        if(Files.isRegularFile(meta)&&(latest==null||Files.getLastModifiedTime(meta).compareTo(Files.getLastModifiedTime(latest))>0))latest=meta;
                    }
                }
                if(latest!=null) {
                    JsonObject meta=JsonParser.parseString(Files.readString(latest)).getAsJsonObject();String digest=meta.get("digest").getAsString();
                    if(!digest.equals(last)) {
                        String name=meta.get("file").getAsString();
                        if(!name.matches("world-[0-9]+-[0-9]+\\.mcdw"))throw new IllegalArgumentException("world filename");
                        Path blob=latest.getParent().resolve(name);long size=Files.size(blob);
                        if(size>World.HEADER_BYTES+World.MAX_SHAPES*World.SHAPE_BYTES)throw new IllegalArgumentException("world size");
                        World world=World.decode(Files.readAllBytes(blob));
                        if(!world.stamp().digest().equals(digest)||!world.stamp().session().toString().equals(meta.get("session").getAsString())||
                            world.stamp().epoch()!=Long.parseUnsignedLong(meta.get("worldEpoch").getAsString())||
                            world.stamp().revision()!=Long.parseUnsignedLong(meta.get("revision").getAsString()))throw new IllegalArgumentException("world metadata mismatch");
                        pending.set(new Candidate(world,meta));last=digest;
                    }
                }
                JsonObject sample=observation.getAndSet(null);
                if(sample!=null){Path tmp=output.resolve("mc-probe.json.tmp");Files.writeString(tmp,new GsonBuilder().setPrettyPrinting().create().toJson(sample));
                    Files.move(tmp,output.resolve("mc-probe.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
                Thread.sleep(200);
            }catch(InterruptedException ex){Thread.currentThread().interrupt();return;}
            catch(Exception ex){LOG.warn("MCDN probe worker refused data: {}",ex.toString());try{Thread.sleep(500);}catch(InterruptedException interrupted){return;}}
        }
    }
    public static void clientTick(Minecraft mc) {
        if(!tickObserved){tickObserved=true;LOG.info("MCDN_CLIENT_TICK_OBSERVED; thread={}; no takeover",Thread.currentThread().getName());}
        if(!configured)return;
        try {
            var server=mc.getSingleplayerServer();
            if(server==null||mc.level==null||mc.player==null||!mc.gameDirectory.toPath().toAbsolutePath().normalize().equals(labGame)) {
                WorldLayers.clear();generation.incrementAndGet();appliedDigest=null;return;
            }
            Candidate candidate=pending.getAndSet(null);
            if(candidate!=null) {
                var clientLevel=mc.level;var dimension=clientLevel.dimension();long request=generation.incrementAndGet();serverApplied.set(null);
                server.execute(()->{try{
                    Path save=server.getWorldPath(LevelResource.ROOT).toRealPath();
                    if(!save.startsWith(labGame.resolve("saves")))throw new IllegalStateException("server save outside lab");
                    var serverLevel=server.overworld();
                    if(request!=generation.get()||!dimension.equals(serverLevel.dimension()))return;
                    WorldLayers.install(serverLevel,new BridgeGeometry(candidate.world));serverApplied.set(candidate.world.stamp().digest());
                    installed.set(new ServerInstall(candidate,clientLevel,request));
                }catch(Exception ex){WorldLayers.clear();LOG.error("MCDN server shape install failed: {}",ex.toString());}});
            }
            var result=installed.getAndSet(null);
            if(result!=null&&result.generation==generation.get()&&result.clientIdentity==mc.level) {
                WorldLayers.install(mc.level,new BridgeGeometry(result.candidate.world));appliedDigest=result.candidate.world.stamp().digest();
                LOG.info("MCDN lab collision subset registered: {} unsupportedCells={}; takeover remains disabled",appliedDigest,result.candidate.metadata.get("unsupportedCells"));
            }
            if(++ticks%10==0) {
                if(queryRequested.compareAndSet(false,true))server.execute(()->{
                    try{serverQueries.set(WorldLayers.queries(server.overworld()));}finally{queryRequested.set(false);}});
                JsonObject s=new JsonObject();s.addProperty("kind","isolated-native-world-probe");s.addProperty("gameTicks",ticks);
                s.addProperty("digest",appliedDigest);s.addProperty("serverDigest",serverApplied.get());s.addProperty("clientQueryCount",WorldLayers.queries(mc.level));
                s.addProperty("serverQueryCount",serverQueries.get());
                s.addProperty("playerX",mc.player.getX());s.addProperty("playerY",mc.player.getY());s.addProperty("playerZ",mc.player.getZ());
                s.addProperty("onGround",mc.player.onGround());s.addProperty("paused",mc.isPaused());s.addProperty("eligibleForControl",false);
                s.addProperty("physicsIsolationComplete",false);s.addProperty("note","solid collision subset only; no input/frame/Hero handoff");observation.set(s);
            }
        }catch(Exception ex){WorldLayers.clear();LOG.error("MCDN lab tick disabled collision layer: {}",ex.toString());}
    }
}
