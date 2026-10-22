package dev.mcdn.physics;

import com.google.gson.*;
import com.mojang.math.Transformation;
import dev.mcdn.minecraft.*;
import dev.mcdn.physics.mixin.*;
import dev.mcdn.protocol.*;
import net.fabricmc.api.ClientModInitializer;
import net.minecraft.client.*;
import net.minecraft.client.player.ClientInput;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.*;
import net.minecraft.world.Difficulty;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.shapes.*;
import org.joml.Vector3f;
import org.joml.Quaternionf;
import org.slf4j.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.*;

/** Opt-in single-game component integration test. Never installs a production/DC MODE. */
public final class PhysicsProbe implements ClientModInitializer {
    private static final Logger LOG=LoggerFactory.getLogger("MCDN-PHYSICS");
    private record Layer(Level level,UUID player,BridgeGeometry geometry,AtomicLong queries){}
    private static final AtomicReference<List<Layer>> layers=new AtomicReference<>(List.of());
    private static final ConcurrentLinkedQueue<JsonObject> events=new ConcurrentLinkedQueue<>();
    private static final AtomicInteger queued=new AtomicInteger();
    private static final AtomicBoolean begin=new AtomicBoolean(),restore=new AtomicBoolean();
    private static volatile boolean configured,savePathVerified,worldPrepared,serverReady,serverRestored,finished,failed;
    private static volatile int phase=-1;
    private static World fixture;
    private static DcScene dcScene;
    private static LabControlGuest control;
    private static Path game,output;
    private static UUID playerId;
    private static boolean worldPreparationRequested,setupRequested,clientInstalled,readyReported,released;
    private static int warm,originWarm,restoredTicks,setupWait,restoreAttempts,warmWait;
    private static boolean enteredTestArea;
    private static long inputSeq,envelopeSeq=1,eventSeq;
    private static int lastHeld;
    private static InputInbox inbox;
    private static BridgeInputBinding binding;
    private static ClientInput original;
    private static CameraType camera;
    private static net.minecraft.client.gui.screens.inventory.InventoryScreen ownedInventory;
    private static String leaseFault;
    // Server-owned state; the file worker never reads game objects.
    private static ServerPlayer serverPlayer;
    private static Vec3 returnPosition;
    private static float returnYaw,returnPitch;
    private static GameType returnMode;
    private static final List<Display.BlockDisplay> displays=new ArrayList<>();
    private static final List<BlockPos> nativeBlocks=new ArrayList<>();
    private static boolean shutdownReturn;

    @Override public void onInitializeClient(){
        String config=System.getProperty("mcdn.physics.manifest");if(config==null)return;
        try{
            var cfg=JsonParser.parseString(Files.readString(Path.of(config))).getAsJsonObject();
            game=Path.of(cfg.get("gameDir").getAsString()).toRealPath();
            if(!game.getFileName().toString().equals("MC-DC-Physics-26.3")||!Files.isRegularFile(game.resolve("MCDN_PHYSICS_LAB")))throw new IllegalArgumentException("dedicated physics lab required");
            Path blob=Path.of(cfg.get("fixture").getAsString());if(Files.size(blob)>World.HEADER_BYTES+World.MAX_SHAPES*World.SHAPE_BYTES)throw new IllegalArgumentException("fixture size");
            fixture=World.decode(Files.readAllBytes(blob));
            if(!fixture.stamp().digest().equals(cfg.get("fixtureSha256").getAsString()))throw new IllegalArgumentException("pinned fixture required");
            if(cfg.has("dcScene"))dcScene=new DcScene(JsonParser.parseString(Files.readString(Path.of(cfg.get("dcScene").getAsString()))).getAsJsonObject(),fixture);
            else if(fixture.boxes().size()>16)throw new IllegalArgumentException("large scene requires explicit DC provenance");
            if(cfg.has("dcVisuals")){
                if(dcScene==null||!dcScene.nativeBlocks)throw new IllegalArgumentException("DC visuals require native DC geometry");
                DcVisuals.configure(Path.of(cfg.get("dcVisuals").getAsString()),cfg.get("dcVisualsSha256").getAsString(),fixture.stamp().digest(),game);
                dev.mcdn.frameprobe.FrameProbe.sceneLabel(DcVisuals::description);
            }
            if(cfg.has("inputManifest")){
                if(dcScene==null)throw new IllegalArgumentException("input lab requires pinned DC scene");
                control=new LabControlGuest(Path.of(cfg.get("inputManifest").getAsString()),cfg.get("inputManifestSha256").getAsString(),fixture);
            }
            Path parent=Path.of(cfg.get("output").getAsString()).toAbsolutePath().normalize();Files.createDirectories(parent);
            output=parent.resolve(UUID.randomUUID().toString());Files.createDirectory(output);configured=true;
            Thread worker=new Thread(PhysicsProbe::files,"MCDN-physics-files");worker.setDaemon(true);worker.start();
            LOG.info("MCDN_PHYSICS_INITIALIZED source={} fixture={}; inputSource={}; no production MODE",getClass().getProtectionDomain().getCodeSource().getLocation(),fixture.stamp().digest(),control==null?"local-script":"dc-foreground-input-lab");
        }catch(Exception ex){LOG.error("MCDN physics refused: {}",ex.toString());}
    }
    private static void files(){
        try{
            Files.writeString(output.getParent().resolve("current-run.json"),new Gson().toJson(Map.of("directory",output.toString(),"fixtureSha256",fixture.stamp().digest())));
            while(!finished||!events.isEmpty()){
                Path save=game.resolve("saves/MCDN-Physics");
                if(!savePathVerified&&Files.isDirectory(save)){
                    if(!save.toRealPath().equals(save))throw new IllegalStateException("dedicated save must remain inside the canonical lab");
                    savePathVerified=true;
                }
                if(Files.exists(output.resolve("begin")))begin.set(true);
                JsonObject event;while((event=events.poll())!=null){queued.decrementAndGet();String text=new Gson().toJson(event);
                    Files.writeString(output.resolve("events.jsonl"),text+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND);
                    if(event.get("kind").getAsString().equals("ready"))Files.writeString(output.resolve("ready.json"),text);
                }
                Thread.sleep(10);
            }
            Files.writeString(output.resolve("complete.json"),new Gson().toJson(Map.of("kind","native-physics-test-ended","failed",failed,"serverRestored",serverRestored,"leaseFault",Objects.toString(leaseFault,""),"source",control==null?"local-script":"dc-foreground-input-lab","productionModeGranted",false)));
        }catch(Exception ex){failed=true;LOG.error("MCDN physics file worker failed: {}",ex.toString());}
    }
    private static void emit(JsonObject event){
        event.addProperty("productionModeGranted",false);event.addProperty("fixtureSha256",fixture.stamp().digest());
        event.addProperty("geometrySource",dcScene==null?"synthetic-fixture":"archived-dc-solid-subset");
        event.addProperty("inputSource",control==null?"local-script":"dc-foreground-input-lab");
        event.addProperty("geometryImplementation",dcScene!=null&&dcScene.nativeBlocks?"native-blocks":"query-shapes");
        if(dcScene!=null)event.addProperty("dcSourceDigest",dcScene.sourceDigest);
        if(queued.incrementAndGet()>2048){queued.decrementAndGet();failed=true;return;}events.add(event);
    }
    private static void install(Level level){
        if(dcScene!=null&&dcScene.nativeBlocks)return; // Vanilla block state/shape queries own all collisions.
        var value=new Layer(level,playerId,new BridgeGeometry(fixture),new AtomicLong());value.geometry.applied();
        layers.updateAndGet(old->{var list=new ArrayList<Layer>();for(var e:old)if(e.level!=level)list.add(e);list.add(value);return List.copyOf(list);});
    }
    private static void remove(Level level){layers.updateAndGet(old->old.stream().filter(e->e.level!=level).toList());}
    public static Iterable<VoxelShape> collision(Object world,CollisionContext context,AABB bounds){
        if(!(context instanceof EntityCollisionContext entity)||entity.getEntity()==null)return null;
        for(var layer:layers.get())if(layer.level==world&&layer.player.equals(entity.getEntity().getUUID())){layer.queries.incrementAndGet();return layer.geometry.intersecting(bounds);}
        return null;
    }
    private static long queries(Level level){for(var e:layers.get())if(e.level==level)return e.queries.get();return 0;}
    private static void prepareWorld(MinecraftServer server){
        try{
            if(!savePathVerified||!server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().equals(game.resolve("saves/MCDN-Physics"))||server.getPlayerCount()!=1)throw new IllegalStateException("only the dedicated one-player fixture save allowed");
            server.setDifficulty(Difficulty.PEACEFUL,true);
            if(server.getWorldData().getDifficulty()!=Difficulty.PEACEFUL)throw new IllegalStateException("peaceful fixture required");
            var event=new JsonObject();event.addProperty("kind","world-prepared");event.addProperty("difficulty","peaceful");emit(event);worldPrepared=true;
            LOG.info("MCDN_PHYSICS_WORLD_PREPARED peaceful; awaiting a living native player");
        }catch(Exception ex){failed=true;serverRestored=true;LOG.error("MCDN physics world preparation failed: {}",ex.toString());}
    }
    private static void setupServer(MinecraftServer server){
        try{
            Path save=server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
            if(!savePathVerified||!save.equals(game.resolve("saves/MCDN-Physics"))||server.getPlayerCount()!=1)throw new IllegalStateException("only the dedicated one-player fixture save allowed");
            var player=server.getPlayerList().getPlayer(playerId);
            if(player==null||player.level()!=server.overworld()||!player.isAlive()||!player.onGround())throw new IllegalStateException("living grounded overworld player required");
            serverPlayer=player;returnPosition=player.position();returnYaw=player.getYRot();returnPitch=player.getXRot();returnMode=player.gameMode();
            var origin=sample("server-before",player);origin.addProperty("kind","origin");origin.addProperty("gameMode",returnMode.getName());emit(origin);
            if(!player.level().getBlockState(new BlockPos(0,199,0)).isAir()||!player.level().getFluidState(new BlockPos(0,200,0)).isEmpty())throw new IllegalStateException("fixture must occupy original air");
            if(dcScene!=null){
                // Only our tagged diagnostic displays in the backed-up dedicated lab scene.
                var stale=new ArrayList<Entity>();
                for(var entity:server.overworld().getAllEntities())if(entity instanceof Display.BlockDisplay&&entity.entityTags().contains("mcdn-physics-fixture")&&entity.getY()>=170&&entity.getY()<=230&&Math.abs(entity.getX())<64&&Math.abs(entity.getZ())<16)stale.add(entity);
                for(var entity:stale)entity.discard();
                var cleaned=new JsonObject();cleaned.addProperty("kind","previous-displays-cleaned");cleaned.addProperty("removed",stale.size());emit(cleaned);
            }
            install(player.level());
            // Reject original terrain/fluid contamination before installing a native scene.
            if(dcScene!=null)for(var b:fixture.boxes())for(int x=(int)Math.floor(b.minX());x<Math.ceil(b.maxX());x++)
                for(int y=(int)Math.floor(b.minY());y<Math.ceil(b.maxY());y++)for(int z=(int)Math.floor(b.minZ());z<Math.ceil(b.maxZ());z++){
                    var pos=new BlockPos(x,y,z);
                    if(!player.level().getBlockState(pos).isAir()||!player.level().getFluidState(pos).isEmpty())throw new IllegalStateException("DC scene overlaps native blocks/fluids");
                }
            if(dcScene!=null&&dcScene.nativeBlocks){
                var targets=new LinkedHashSet<BlockPos>();
                for(var b:fixture.boxes())for(int x=(int)b.minX();x<(int)b.maxX();x++)for(int y=(int)b.minY();y<(int)b.maxY();y++)for(int z=(int)b.minZ();z<(int)b.maxZ();z++)targets.add(new BlockPos(x,y,z));
                if(targets.size()!=dcScene.nativeBlockCount)throw new IllegalStateException("native block count/overlap mismatch");
                // Preflight every target before touching any block. This dedicated region must be air.
                for(var pos:targets)if(!server.overworld().getBlockState(pos).isAir()||!server.overworld().getFluidState(pos).isEmpty()||server.overworld().getBlockEntity(pos)!=null)throw new IllegalStateException("native region is not pristine air");
                nativeBlocks.addAll(targets); // Rollback ledger exists before the first native mutation.
                for(var pos:nativeBlocks)if(!server.overworld().setBlock(pos,Blocks.STONE.defaultBlockState(),3))throw new IllegalStateException("native block materialization failed");
                var event=new JsonObject();event.addProperty("kind","native-blocks-installed");event.addProperty("blocks",nativeBlocks.size());event.addProperty("collisionOverride",false);emit(event);
            }
            for(var box:dcScene!=null&&dcScene.nativeBlocks?List.<World.Box>of():dcScene==null?fixture.boxes():DcScene.displayRuns(fixture)){
                var display=new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY,player.level());
                ((BlockDisplayAccess)(Object)display).mcdn$block((box.id()==2?Blocks.GOLD_BLOCK:box.id()==3?Blocks.GLASS:Blocks.STONE).defaultBlockState());
                ((DisplayAccess)(Object)display).mcdn$transform(new Transformation(new Vector3f(),new Quaternionf(),new Vector3f((float)(box.maxX()-box.minX()),(float)(box.maxY()-box.minY()),(float)(box.maxZ()-box.minZ())),new Quaternionf()));
                ((DisplayAccess)(Object)display).mcdn$width((float)Math.max(16,2*Math.max(box.maxX()-box.minX(),box.maxZ()-box.minZ())));((DisplayAccess)(Object)display).mcdn$height((float)Math.max(8,box.maxY()-box.minY()));
                display.setPos(box.minX(),box.minY(),box.minZ());display.addTag("mcdn-physics-fixture");
                if(!server.overworld().addFreshEntity(display))throw new IllegalStateException("native display spawn failed");displays.add(display);
            }
            player.setGameMode(GameType.SURVIVAL);player.setDeltaMovement(Vec3.ZERO);
            if(!player.teleportTo(server.overworld(),dcScene==null?.5:dcScene.x,200.5,dcScene==null?.5:dcScene.z,Set.of(),-90,0,false))throw new IllegalStateException("native setup teleport failed");
            serverReady=true;LOG.info("MCDN_PHYSICS_SERVER_READY actual native player, displays={}, fixture={}",displays.size(),fixture.stamp().digest());
        }catch(Exception ex){failed=true;if(serverPlayer==null)serverRestored=true;restore.set(true);LOG.error("MCDN physics setup failed: {}",ex.toString());}
    }
    private static void start(Minecraft mc){
        if(control!=null){
            inbox=Objects.requireNonNull(control.inbox());original=mc.player.input;binding=new BridgeInputBinding(BridgeInputBinding.slot(mc.player),inbox,held->mc.gui.screen()==null?held:0);
            if(camera==null)camera=mc.options.getCameraType();mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
            if(!binding.enter())throw new IllegalStateException("native external input install failed");phase=0;
            LOG.info("MCDN_NATIVE_INPUT_LAB_INSTALLED actual DC foreground input channel; production MODE not granted");return;
        }
        UUID session=fixture.stamp().session();String hex="0123456789abcdef".repeat(4);
        // Schema-only local fixture peer, explicitly not a remote DC identity or authenticated network session.
        var hello=new Wire.Envelope(2,session,0,0,1,1,Control.hello("dc",hex,hex,ProcessHandle.current().pid(),1));
        var peer=new Control.Handshake().accept(hello,session,2,"dc",hex,hex);
        inbox=new InputInbox(peer,1,1);original=mc.player.input;binding=new BridgeInputBinding(BridgeInputBinding.slot(mc.player),inbox);
        camera=mc.options.getCameraType();mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
        if(!binding.enter())throw new IllegalStateException("native input fixture install failed");
        phase=0;LOG.info("MCDN_PHYSICS_SCRIPT_STARTED local input only; originalInput={}",original.getClass().getName());
    }
    private static int held(int tick){
        if(dcScene!=null)return DcScene.held(tick);
        if(tick>=20&&tick<60||tick>=166&&tick<170)return 1;
        if(tick==70||tick==130)return 16;
        if(tick>=110&&tick<118)return 2;
        return 0;
    }
    private static void release(Minecraft mc){
        if(ownedInventory!=null){if(mc.gui.screen()==ownedInventory)mc.gui.setScreen(null);ownedInventory=null;}
        if(binding!=null&&!released){if(!binding.release())throw new IllegalStateException("original input restore pending");released=true;}
        if(camera!=null)mc.options.setCameraType(camera);
    }
    private static JsonObject sample(String side,net.minecraft.world.entity.player.Player player){
        var j=new JsonObject();j.addProperty("kind","sample");j.addProperty("side",side);j.addProperty("phase",phase);j.addProperty("nativeTick",player.tickCount);
        j.addProperty("x",player.getX());j.addProperty("y",player.getY());j.addProperty("z",player.getZ());var v=player.getDeltaMovement();
        j.addProperty("vx",v.x);j.addProperty("vy",v.y);j.addProperty("vz",v.z);j.addProperty("grounded",player.onGround());j.addProperty("horizontalCollision",player.horizontalCollision);j.addProperty("verticalCollision",player.verticalCollision);
        j.addProperty("noPhysics",player.noPhysics);j.addProperty("flying",player.getAbilities().flying);j.addProperty("health",player.getHealth());j.addProperty("queries",queries(player.level()));
        var body=player.getBoundingBox();j.addProperty("bodyMinX",body.minX);j.addProperty("bodyMaxX",body.maxX);j.addProperty("bodyMinY",body.minY);j.addProperty("bodyMaxY",body.maxY);j.addProperty("bodyMinZ",body.minZ);j.addProperty("bodyMaxZ",body.maxZ);
        j.addProperty("originalBlockBelow",player.level().getBlockState(BlockPos.containing(player.getX(),199,player.getZ())).isAir()?"air":"non-air");return j;
    }
    public static void clientTick(Minecraft mc){
        if(!configured||finished)return;
        try{
            var server=mc.getSingleplayerServer();
            if(mc.level==null||mc.player==null||server==null){DcVisuals.release();if(setupRequested){release(mc);failed=true;finished=true;restore.set(true);}return;}
            if(!mc.gameDirectory.toPath().toAbsolutePath().normalize().equals(game))return;
            if(failed){DcVisuals.release();release(mc);restore.set(true);if(serverRestored)finished=true;return;}
            if(!worldPreparationRequested){if(!savePathVerified)return;worldPreparationRequested=true;playerId=mc.player.getUUID();server.execute(()->prepareWorld(server));return;}
            if(!setupRequested){
                if(!worldPrepared||!mc.player.isAlive()||mc.player.tickCount<20||!mc.player.onGround()){originWarm=0;return;}
                if(++originWarm<10)return;
                DcVisuals.verifyResources(mc);setupRequested=true;server.execute(()->setupServer(server));return;
            }
            if(!serverReady)return;
            if(!clientInstalled){install(mc.level);clientInstalled=true;DcVisuals.activate();emit(DcVisuals.evidence());}
            if(serverRestored){DcVisuals.release();remove(mc.level);if(++restoredTicks>=10){var end=sample("client-restored",mc.player);end.addProperty("kind","restored");end.addProperty("inputIdentityRestored",original==mc.player.input);end.addProperty("cameraRestored",camera==mc.options.getCameraType());emit(end);emit(DcVisuals.evidence());if(control!=null)publishControl("restored",mc);finished=true;}return;}
            // The server may send the return teleport before completing a large block rollback.
            // While relinquishing ownership, being outside the test area is expected, not a fault.
            if(released&&restore.get()){if(control!=null)publishControl("releasing",mc);return;}
            if(!enteredTestArea&&phase<0&&mc.player.getY()<195&&++setupWait<100)return;
            if(mc.player.getY()>=195)enteredTestArea=true;
            if(mc.player.getY()<195||mc.player.noPhysics||mc.player.getAbilities().flying||mc.isPaused()){release(mc);failed=true;restore.set(true);return;}
            if(phase<0){
                if(++warmWait%20==0){var waiting=sample("client",mc.player);waiting.addProperty("kind","warmup");emit(waiting);}
                if(warmWait>200&&!readyReported)throw new IllegalStateException("native ground readiness timed out");
                if(mc.player.onGround()&&Math.abs(mc.player.getY()-200)<.01)warm++;else warm=0;
                if(warm>=10&&!readyReported){var event=sample("client",mc.player);event.addProperty("kind","ready");emit(event);readyReported=true;}
                if(control!=null&&readyReported){
                    if(camera==null){camera=mc.options.getCameraType();original=mc.player.input;mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);}
                    publishControl("ready",mc);
                    if(control.failure()!=null)throw new IllegalStateException(control.failure());
                    if(control.inbox()!=null&&control.inbox().fault()!=null){leaseFault=control.inbox().fault();release(mc);restore.set(true);return;}
                    if(control.requested())start(mc);else return;
                }else if(readyReported&&begin.get())start(mc);else return;
            }
            if(control!=null&&control.viewControl&&!released){
                for(int count=0;count<128;count++){var view=control.consumedView();if(view==null)break;
                    if(view.inventory()){
                        if(mc.gui.screen()==null){ownedInventory=new net.minecraft.client.gui.screens.inventory.InventoryScreen(mc.player);mc.gui.setScreen(ownedInventory);}
                        else if(mc.gui.screen()==ownedInventory){mc.gui.setScreen(null);ownedInventory=null;}
                        else throw new IllegalStateException("unowned native GUI");
                    }
                    if(mc.gui.screen()==null){mc.player.turn(view.x(),view.y());if(view.cycle())mc.options.setCameraType(mc.options.getCameraType().cycle());}
                    var event=new JsonObject();event.addProperty("kind","view-consumed");event.addProperty("inputSeq",view.inputSeq());event.addProperty("mouseX",view.x());event.addProperty("mouseY",view.y());event.addProperty("cameraCycle",view.cycle());event.addProperty("inventoryCycle",view.inventory());event.addProperty("screen",screenType(mc));event.addProperty("yaw",mc.player.getYRot());event.addProperty("pitch",mc.player.getXRot());event.addProperty("camera",mc.options.getCameraType().name());event.addProperty("nativeTick",mc.player.tickCount);emit(event);
                }
            }
            var record=sample("client",mc.player);record.addProperty("held",inbox.held());record.addProperty("consumedInput",inbox.consumedInput());record.addProperty("consumedAck",inbox.consumedAck());record.addProperty("inputIdentityRestored",original==mc.player.input);record.addProperty("fault",inbox.fault());
            record.addProperty("screen",screenType(mc));record.addProperty("nativeForward",mc.player.input.keyPresses.forward());record.addProperty("nativeJump",mc.player.input.keyPresses.jump());record.addProperty("nativeMoveX",mc.player.input.getMoveVector().x);record.addProperty("nativeMoveY",mc.player.input.getMoveVector().y);
            emit(record);
            if(inbox.fault()!=null&&!released){leaseFault=inbox.fault();release(mc);}
            if(control!=null){
                publishControl(released?"releasing":"active",mc);
                if(released)restore.set(true);
                if(++phase>=1200){inbox.revoke("bounded-input-lab-end");release(mc);restore.set(true);}
                return;
            }
            if(phase<170){
                if(released)throw new IllegalStateException("early input fault: "+inbox.fault());
                int mask=held(phase),pressed=mask&~lastHeld,up=lastHeld&~mask;if((pressed|up)!=0)eventSeq++;
                var input=new Control.Input(++inputSeq,phase+1,eventSeq,mask,pressed,up);
                if(!inbox.receive(new Wire.Envelope(13,fixture.stamp().session(),1,1,++envelopeSeq,1,Control.encodeInput(input)),System.nanoTime()))throw new IllegalStateException("script input refused");lastHeld=mask;
            }
            if(++phase>=200){release(mc);restore.set(true);}
        }catch(Exception ex){failed=true;restore.set(true);try{release(mc);}catch(Exception restoreError){LOG.error("MCDN physics input restore failed: {}",restoreError.toString());}LOG.error("MCDN physics client failed: {}",ex.toString());}
    }
    private static String screenType(Minecraft mc){return mc.gui.screen()==null?"none":mc.gui.screen()==ownedInventory?"inventory":"other";}
    private static void publishControl(String stage,Minecraft mc){control.publish(stage,mc.player.tickCount,mc.player.getX(),mc.player.getY(),mc.player.getZ(),original==mc.player.input,mc.player.getYRot(),mc.player.getXRot(),mc.options.getCameraType().name(),screenType(mc));}
    public static void beforeServerStop(MinecraftServer server){
        if(!configured||serverPlayer==null||serverRestored)return;
        beginShutdownRestore(server,"server-stop");
    }
    public static void beforePlayerRemove(ServerPlayer player){
        if(!configured||player!=serverPlayer||serverRestored)return;
        beginShutdownRestore(player.level().getServer(),"player-remove-before-save");
    }
    private static void beginShutdownRestore(MinecraftServer server,String trigger){
        var event=new JsonObject();event.addProperty("kind","shutdown-restore");event.addProperty("trigger",trigger);event.addProperty("phase",phase);event.addProperty("nativeTick",serverPlayer.tickCount);emit(event);
        // Invoked on the native server shutdown path before vanilla saves the dedicated world.
        // This also covers closing the lab while waiting for an F7 entry that was refused.
        if(inbox!=null)inbox.revoke("native-server-stopping");
        shutdownReturn=true;restore.set(true);serverTick(server);
        if(!serverRestored)LOG.error("MCDN_NATIVE_WORLD_RESTORE_INCOMPLETE_BEFORE_SAVE; retained lab backup required");
    }
    public static void serverTick(MinecraftServer server){
        if(!configured||serverPlayer==null)return;
        if(restore.get()&&!serverRestored){
            try{
                for(var d:displays)d.discard();displays.clear();remove(serverPlayer.level());serverPlayer.setGameMode(returnMode);serverPlayer.setDeltaMovement(Vec3.ZERO);
                int cleared=nativeBlocks.size();
                for(var pos:nativeBlocks)server.overworld().setBlock(pos,Blocks.AIR.defaultBlockState(),3);
                for(var pos:nativeBlocks)if(!server.overworld().getBlockState(pos).isAir()||server.overworld().getBlockEntity(pos)!=null)throw new IllegalStateException("native block rollback pending");
                nativeBlocks.clear();
                if(dcScene!=null&&dcScene.nativeBlocks){var event=new JsonObject();event.addProperty("kind","native-blocks-restored");event.addProperty("blocks",cleared);event.addProperty("remaining",nativeBlocks.size());emit(event);}
                if(shutdownReturn)serverPlayer.absSnapTo(returnPosition.x,returnPosition.y,returnPosition.z,returnYaw,returnPitch);
                else if(!serverPlayer.teleportTo(server.overworld(),returnPosition.x,returnPosition.y,returnPosition.z,Set.of(),returnYaw,returnPitch,false))throw new IllegalStateException("return teleport failed");
                var end=sample("server-restored",serverPlayer);end.addProperty("kind","restored");end.addProperty("gameMode",serverPlayer.gameMode().getName());end.addProperty("remainingFixtureDisplays",displays.size());emit(end);
                serverRestored=true;LOG.info("MCDN_PHYSICS_SERVER_RESTORED original pose/mode; fixture displays removed");
            }catch(Exception ex){failed=true;if(++restoreAttempts>=3)finished=true;LOG.error("MCDN physics server restore failed attempt {}: {}",restoreAttempts,ex.toString());}return;
        }
        if(serverReady&&!serverRestored&&(phase>=0||serverPlayer.tickCount%20==0)){var record=sample("server",serverPlayer);if(phase<0)record.addProperty("kind","warmup");emit(record);}
    }
}
