package dev.mcdn.physics;

import com.google.gson.*;
import dev.mcdn.protocol.*;
import java.net.*;
import java.nio.file.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** Opt-in local native-input experiment. Does not implement or grant production MODE. */
final class LabControlGuest {
    private record State(byte[] body,long ack,boolean terminal){}
    private final AtomicReference<State> state=new AtomicReference<>();
    private final UUID session;
    private final long worldEpoch;
    private final String nonce,mcBuild,dcBuild,digest;
    private final int port;
    private final long expires;
    private volatile InputInbox inbox;
    private volatile boolean firstInput;
    private volatile String failure;
    LabControlGuest(Path manifest,String expected,World world)throws Exception{
        if(Files.size(manifest)>16384)throw new IllegalArgumentException("input lab manifest size");
        byte[] raw=Files.readAllBytes(manifest);
        if(!HexFormat.of().formatHex(World.sha256(raw)).equals(expected))throw new IllegalArgumentException("input lab manifest digest");
        var cfg=JsonParser.parseString(new String(raw,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        if(!cfg.get("inputLab").getAsBoolean()||cfg.get("eligibleForControl").getAsBoolean()||!cfg.get("geometryDigest").getAsString().equals(world.stamp().digest()))throw new IllegalArgumentException("isolated input lab geometry/scope");
        session=UUID.fromString(cfg.get("session").getAsString());worldEpoch=world.stamp().epoch();digest=world.stamp().digest();
        nonce=cfg.get("controlNonce").getAsString();mcBuild=cfg.get("mcBuild").getAsString();dcBuild=cfg.get("dcBuild").getAsString();port=cfg.get("controlPort").getAsInt();expires=cfg.get("expiresUnixMs").getAsLong();
        if(port<1024||port>65535||expires<=System.currentTimeMillis()||expires-System.currentTimeMillis()>900000)throw new IllegalArgumentException("input lab endpoint/expiry");
        Path own=Path.of(LabControlGuest.class.getProtectionDomain().getCodeSource().getLocation().toURI());
        if(!HexFormat.of().formatHex(World.sha256(Files.readAllBytes(own))).equals(mcBuild))throw new IllegalArgumentException("actual native input build mismatch");
        Thread worker=new Thread(this::run,"MCDN-native-input-lab");worker.setDaemon(true);worker.start();
    }
    InputInbox inbox(){return inbox;}
    boolean requested(){return firstInput;}
    String failure(){return failure;}
    void publish(String stage,int tick,double x,double y,double z,boolean inputRestored){
        var value=inbox;long consumed=value==null?0:value.consumedInput(),ack=value==null?1:value.consumedAck();
        state.set(new State(Control.encode("schema","native-input-lab-1","state",stage,"geometry",digest,"tick",Integer.toString(tick),"x",Double.toString(x),"y",Double.toString(y),"z",Double.toString(z),"inputSeq",Long.toUnsignedString(consumed),"inputRestored",Boolean.toString(inputRestored)),ack,stage.equals("restored")));
    }
    private Socket connect()throws Exception{
        long deadline=System.nanoTime()+30_000_000_000L;
        while(System.nanoTime()<deadline){Socket socket=new Socket();try{socket.connect(new InetSocketAddress(InetAddress.getByName("127.0.0.1"),port),200);return socket;}catch(IOException ex){socket.close();Thread.sleep(50);}}
        throw new ConnectException("native host connect timeout");
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
                        else {if(!inbox.receive(message,System.nanoTime()))throw new IllegalArgumentException("native input lab refused packet");if(message.type()==13)firstInput=true;}
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
