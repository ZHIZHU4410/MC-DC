package dev.mcdn.physics;

import com.google.gson.*;
import dev.mcdn.protocol.*;
import java.net.*;
import java.nio.file.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

/** Opt-in local native-input experiment. Does not implement or grant production MODE. */
final class LabControlGuest {
    private record State(byte[] body,long ack,boolean terminal){}
    private final AtomicReference<State> state=new AtomicReference<>();
    private final UUID session;
    private final long worldEpoch;
    private final String nonce,mcBuild,dcBuild,digest;
    private final int port;
    private final Path endpoint;
    private final long expires;
    private volatile InputInbox inbox;
    private volatile boolean firstInput;
    private volatile String failure;
    final boolean viewControl;
    final boolean inventoryControl;
    private long lastViewInput;
    record View(long inputSeq,int x,int y,boolean cycle,boolean inventory){}
    private final ConcurrentLinkedQueue<View> views=new ConcurrentLinkedQueue<>();
    private final AtomicInteger viewCount=new AtomicInteger();
    LabControlGuest(Path manifest,String expected,World world)throws Exception{
        if(Files.size(manifest)>16384)throw new IllegalArgumentException("input lab manifest size");
        byte[] raw=Files.readAllBytes(manifest);
        if(!HexFormat.of().formatHex(World.sha256(raw)).equals(expected))throw new IllegalArgumentException("input lab manifest digest");
        var cfg=JsonParser.parseString(new String(raw,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        if(!cfg.get("inputLab").getAsBoolean()||cfg.get("eligibleForControl").getAsBoolean()||!cfg.get("geometryDigest").getAsString().equals(world.stamp().digest()))throw new IllegalArgumentException("isolated input lab geometry/scope");
        session=UUID.fromString(cfg.get("session").getAsString());worldEpoch=world.stamp().epoch();digest=world.stamp().digest();
        viewControl=cfg.has("viewControl")&&cfg.get("viewControl").getAsBoolean();
        inventoryControl=cfg.has("inventoryControl")&&cfg.get("inventoryControl").getAsBoolean();
        if(inventoryControl&&!viewControl)throw new IllegalArgumentException("native inventory requires view controls");
        nonce=cfg.get("controlNonce").getAsString();mcBuild=cfg.get("mcBuild").getAsString();dcBuild=cfg.get("dcBuild").getAsString();port=cfg.get("controlPort").getAsInt();expires=cfg.get("expiresUnixMs").getAsLong();
        endpoint=manifest.getParent().resolve("control-endpoint.json");
        if((port!=0&&port<1024)||port>65535||expires<=System.currentTimeMillis()||expires-System.currentTimeMillis()>900000)throw new IllegalArgumentException("input lab endpoint/expiry");
        Path own=Path.of(LabControlGuest.class.getProtectionDomain().getCodeSource().getLocation().toURI());
        if(!HexFormat.of().formatHex(World.sha256(Files.readAllBytes(own))).equals(mcBuild))throw new IllegalArgumentException("actual native input build mismatch");
        Thread worker=new Thread(this::run,"MCDN-native-input-lab");worker.setDaemon(true);worker.start();
    }
    InputInbox inbox(){return inbox;}
    boolean requested(){return firstInput;}
    String failure(){return failure;}
    void publish(String stage,int tick,double x,double y,double z,boolean inputRestored,float yaw,float pitch,String camera,String screen){
        var value=inbox;long consumed=value==null?0:value.consumedInput(),ack=value==null?1:value.consumedAck();
        byte[] body=Control.encode("schema","native-input-lab-1","state",stage,"geometry",digest,"tick",Integer.toString(tick),"x",Double.toString(x),"y",Double.toString(y),"z",Double.toString(z),"inputSeq",Long.toUnsignedString(consumed),"inputRestored",Boolean.toString(inputRestored));
        if(viewControl){var fields=new TreeMap<>(Control.parse(body));fields.put("yaw",Float.toString(yaw));fields.put("pitch",Float.toString(pitch));fields.put("camera",camera);if(inventoryControl)fields.put("screen",screen);body=Control.encode(fields.entrySet().stream().flatMap(e->java.util.stream.Stream.of(e.getKey(),e.getValue())).toArray(String[]::new));}
        state.set(new State(body,ack,stage.equals("restored")));
    }
    View consumedView(){
        var value=inbox;if(value==null||value.fault()!=null){views.clear();return null;}
        var next=views.peek();if(next==null||Long.compareUnsigned(next.inputSeq(),value.consumedInput())>0)return null;
        next=views.poll();viewCount.decrementAndGet();return next;
    }
    private boolean receive(Wire.Envelope message){
        if(!viewControl||message.type()!=13)return inbox.receive(message,System.nanoTime());
        var fields=new TreeMap<>(Control.parse(message.body()));
        if(inventoryControl)Control.fields(fields,"inputSeq","hostTick","eventSeq","held","pressed","released","viewSchema","mouseX","mouseY","cameraCycle","inventoryCycle");
        else Control.fields(fields,"inputSeq","hostTick","eventSeq","held","pressed","released","viewSchema","mouseX","mouseY","cameraCycle");
        if(!fields.remove("viewSchema").equals(inventoryControl?"native-ui-lab-1":"native-view-lab-1"))throw new IllegalArgumentException("view schema");
        int x=Integer.parseInt(fields.remove("mouseX")),y=Integer.parseInt(fields.remove("mouseY"));String cycle=fields.remove("cameraCycle");
        String inventory=inventoryControl?fields.remove("inventoryCycle"):"false";
        if(x < -4096||x > 4096||y < -4096||y > 4096||!Set.of("true","false").contains(cycle)||!Set.of("true","false").contains(inventory))throw new IllegalArgumentException("view bounds");
        long input=Long.parseUnsignedLong(fields.get("inputSeq"));
        if(lastViewInput==-1L||input!=lastViewInput+1)throw new IllegalArgumentException("view input order");
        byte[] original=Control.encode(fields.entrySet().stream().flatMap(e->java.util.stream.Stream.of(e.getKey(),e.getValue())).toArray(String[]::new));
        // Publish view BEFORE its matching native input can become consumable.
        if(viewCount.incrementAndGet()>128)throw new IllegalArgumentException("view overflow");
        views.add(new View(input,x,y,Boolean.parseBoolean(cycle),Boolean.parseBoolean(inventory)));
        boolean accepted=inbox.receive(new Wire.Envelope(message.type(),message.session(),message.worldEpoch(),message.modeEpoch(),message.sequence(),message.ackSequence(),original),System.nanoTime());if(accepted)lastViewInput=input;return accepted;
    }
    private Socket connect()throws Exception{
        // MC may warm up before DC enters its level. Keep this worker in standby for
        // the pinned session lifetime; a missed 30-second startup window must not
        // poison the one-shot input lease. Native game ticks never wait here.
        while(System.currentTimeMillis()<expires){
            int actualPort=port;
            if(actualPort==0){
                if(!Files.exists(endpoint)){Thread.sleep(50);continue;}
                if(Files.size(endpoint)>4096)throw new IOException("endpoint size");
                var value=JsonParser.parseString(Files.readString(endpoint)).getAsJsonObject();
                if(!value.get("session").getAsString().equals(session.toString())||!value.get("dcBuild").getAsString().equals(dcBuild))throw new IOException("endpoint identity");
                actualPort=value.get("port").getAsInt();if(actualPort<1024||actualPort>65535)throw new IOException("endpoint port");
            }
            Socket socket=new Socket();try{socket.connect(new InetSocketAddress(InetAddress.getByName("127.0.0.1"),actualPort),200);return socket;}catch(IOException ex){socket.close();Thread.sleep(50);}
        }
        throw new ConnectException("native host did not connect before session expiry");
    }
    private void run(){
        try(Socket socket=connect()){
            socket.setTcpNoDelay(true);socket.setSoTimeout(20);var output=socket.getOutputStream();
            output.write(Wire.encode(new Wire.Envelope(1,session,0,0,1,0,Control.hello("mc",nonce,mcBuild,ProcessHandle.current().pid(),ProcessHandle.current().info().startInstant().orElseThrow().toEpochMilli()*1_000_000L))));
            var decoder=new Wire.StreamDecoder();byte[] buffer=new byte[4096];long sequence=1,next=0;
            while(System.currentTimeMillis()<expires){
                try{
                    int read=socket.getInputStream().read(buffer);if(read<0)throw new EOFException("host disconnected");
                    decoder.feed(buffer,0,read,message->{
                        if(inbox==null){var peer=new Control.Handshake().accept(message,session,2,"dc",nonce,dcBuild);inbox=new InputInbox(peer,worldEpoch,1);}
                        else {if(!receive(message))throw new IllegalArgumentException("native input lab refused packet");if(message.type()==13)firstInput=true;}
                    });
                }catch(SocketTimeoutException timeout){/* Worker only; native ticks never wait. */}
                var snapshot=state.get();
                if(inbox!=null&&snapshot!=null&&System.nanoTime()>=next){
                    inbox.outboundSent(++sequence);output.write(Wire.encode(new Wire.Envelope(14,session,worldEpoch,1,sequence,snapshot.ack,snapshot.body)));next=System.nanoTime()+50_000_000L;
                    if(snapshot.terminal)return;
                }
            }
            throw new IOException("native input lab expired");
        }catch(Exception ex){failure=ex.getClass().getSimpleName()+": "+ex.getMessage();var value=inbox;if(value!=null)value.revoke("input-lab-disconnected");}
    }
}
