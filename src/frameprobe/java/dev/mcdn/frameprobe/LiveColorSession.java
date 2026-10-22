package dev.mcdn.frameprobe;

import com.google.gson.*;
import com.mojang.blaze3d.platform.NativeImage;
import dev.mcdn.ipc.NativeMailbox;
import dev.mcdn.protocol.WorldColorFrame;
import java.nio.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.CRC32;

/** Startup-only manifest I/O, then a worker-owned typed native mailbox. */
final class LiveColorSession implements AutoCloseable {
    final Path directory;
    final UUID session;
    final long expires;
    final boolean viewControl;
    final int maxEdge;
    private final Path map;
    private NativeMailbox mailbox;
    private long published;
    static LiveColorSession read(Path game,Path lab)throws Exception {
        Path pointer=game.resolve("mcdn-world-color.json");if(!Files.exists(pointer))return null;
        if(Files.size(pointer)>4096)throw new IllegalArgumentException("live pointer size");
        var p=JsonParser.parseString(Files.readString(pointer)).getAsJsonObject();Path path=Path.of(p.get("manifest").getAsString()).toRealPath();
        if(!path.startsWith(lab.resolve("live-color").toRealPath())||Files.size(path)>16384)throw new IllegalArgumentException("live manifest path/size");
        byte[] bytes=Files.readAllBytes(path);
        if(!hash(bytes).equals(p.get("sha256").getAsString()))throw new IllegalArgumentException("live manifest hash");
        return new LiveColorSession(JsonParser.parseString(new String(bytes,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject(),game,path.getParent());
    }
    private LiveColorSession(JsonObject config,Path game,Path root)throws Exception {
        if(!config.get("kind").getAsString().equals("mcdn-live-world-color-diagnostic-1")||!Path.of(config.get("gameDir").getAsString()).toRealPath().equals(game)||config.get("eligibleForControl").getAsBoolean())throw new IllegalArgumentException("live diagnostic scope");
        directory=root;session=UUID.fromString(config.get("session").getAsString());expires=config.get("expiresUnixMs").getAsLong();
        viewControl=config.has("inputLab")&&config.get("inputLab").getAsBoolean()&&config.has("viewControl")&&config.get("viewControl").getAsBoolean();
        maxEdge=config.has("captureMaxEdge")?config.get("captureMaxEdge").getAsInt():512;
        if(maxEdge<256||maxEdge>1024)throw new IllegalArgumentException("bounded native capture size");
        if(expires<=System.currentTimeMillis()||expires-System.currentTimeMillis()>900000)throw new IllegalArgumentException("live session expiry");
        map=Path.of(config.get("map").getAsString()).toRealPath();Path dll=Path.of(config.get("dll").getAsString()).toRealPath();
        if(!map.getParent().equals(directory)||!dll.getParent().equals(directory))throw new IllegalArgumentException("private session files required");
        NativeMailbox.load(dll,config.get("dllSha256").getAsString());
    }
    void open(){mailbox=new NativeMailbox(map,session,384+1024*1024*4,true);}
    boolean stopped(){return System.currentTimeMillis()>=expires||Files.exists(directory.resolve("stop-producer"));}
    void publish(FrameProbe.Frozen f,NativeImage image,long readyQpc)throws Exception {
        byte[] raw=new byte[image.getWidth()*image.getHeight()*4];image.getPixelBytes().duplicate().get(raw);
        byte[] packet=new byte[384+raw.length];var b=ByteBuffer.wrap(packet).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(0,0x4357434d).putShort(4,(short)0).putShort(6,(short)1).putInt(8,384).putInt(12,raw.length);
        ByteBuffer.wrap(packet).order(ByteOrder.BIG_ENDIAN).putLong(16,session.getMostSignificantBits()).putLong(24,session.getLeastSignificantBits());
        b.putLong(32,f.streamEpoch()).putLong(56,f.frameId()).putLong(64,f.nativeGameTime()).putLong(72,f.captureQpc());
        b.putInt(80,image.getWidth()).putInt(84,image.getHeight()).putInt(88,image.getWidth()*4).putInt(92,1).putInt(96,7);
        int camera=switch(f.cameraType()){case "FIRST_PERSON"->0;case "THIRD_PERSON_BACK"->1;case "THIRD_PERSON_FRONT"->2;default->throw new IllegalArgumentException("camera type");};
        b.putInt(100,camera).putInt(104,f.sourceWidth()).putInt(108,f.sourceHeight());
        double[] pose={f.footX(),f.footY(),f.footZ(),f.cameraX(),f.cameraY(),f.cameraZ()};for(int i=0;i<6;i++)b.putDouble(112+i*8,pose[i]);
        b.putFloat(160,f.yaw()).putFloat(164,f.pitch()).putFloat(168,f.partialTick());
        for(int i=0;i<16;i++){b.putFloat(176+i*4,f.viewRotation()[i]);b.putFloat(240+i*4,f.projection()[i]);}
        b.putLong(304,readyQpc).putLong(312,NativeMailbox.frequency());var crc=new CRC32();crc.update(raw);b.putInt(320,(int)crc.getValue());System.arraycopy(raw,0,packet,384,raw.length);
        if(!mailbox.publishWorldColor(WorldColorFrame.decode(packet)))return;
        var meta=new JsonObject();meta.addProperty("kind","live-native-mc-world-color-published");meta.addProperty("session",session.toString());meta.addProperty("frameId",Long.toUnsignedString(f.frameId()));meta.addProperty("streamEpoch",Long.toUnsignedString(f.streamEpoch()));
        meta.addProperty("nativeTick",Long.toUnsignedString(f.nativeGameTime()));meta.addProperty("width",image.getWidth());meta.addProperty("height",image.getHeight());meta.addProperty("rawSha256",hash(raw));meta.addProperty("packetSha256",hash(packet));meta.addProperty("captureQpc",f.captureQpc());meta.addProperty("readyQpc",readyQpc);meta.addProperty("eligibleForControl",false);
        meta.addProperty("playerTick",f.playerTick());meta.addProperty("yaw",f.yaw());meta.addProperty("pitch",f.pitch());meta.addProperty("cameraType",f.cameraType());meta.addProperty("footX",f.footX());meta.addProperty("footY",f.footY());meta.addProperty("footZ",f.footZ());
        meta.addProperty("screenType",f.screenType());
        meta.addProperty("worldVisuals",f.worldVisuals());
        String encoded=new Gson().toJson(meta);Files.writeString(directory.resolve("producer.jsonl"),encoded+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND);
        Files.writeString(directory.resolve("producer-latest.json.tmp"),encoded);
        try{Files.move(directory.resolve("producer-latest.json.tmp"),directory.resolve("producer-latest.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
        catch(AccessDeniedException busy){
            // Windows readers can temporarily deny replacement. The append-only journal above
            // is authoritative; an optional latest snapshot must not stop the native producer.
        }
        if(++published==1)image.writeToFile(directory.resolve("first-native-frame.png"));
    }
    static String hash(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    @Override public void close(){if(mailbox!=null)mailbox.close();}
}
