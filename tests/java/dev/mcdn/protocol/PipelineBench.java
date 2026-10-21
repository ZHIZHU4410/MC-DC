package dev.mcdn.protocol;

import java.io.*;
import java.net.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.*;

public final class PipelineBench {
    private static void check(boolean ok) { if (!ok) throw new AssertionError("pipeline assertion"); }
    private static Wire.Envelope read(InputStream in) throws IOException {
        byte[] h=in.readNBytes(64); if(h.length!=64) throw new EOFException(); int n=Wire.validateHeader(h);
        byte[] body=in.readNBytes(n); if(body.length!=n) throw new EOFException();
        byte[] all=Arrays.copyOf(h,64+n); System.arraycopy(body,0,all,64,n); return Wire.decode(all);
    }
    private static final class Ports implements GuestSession.Ports {
        GuestSession session; World world; InputInbox inbox; int held, enters, releases;
        public long qpc(){return 101;} public long frequency(){return 1000;}
        public void installWorld(World world) {
            this.world=world; session.applied("client",world.stamp(),1); session.applied("server",world.stamp(),1);
        }
        public ModeGate.Binding binding(InputInbox inbox) {
            this.inbox=inbox;
            return new ModeGate.Binding() {
                public boolean matches(World.Stamp s,long mode){return inbox.matches(s.session(),s.epoch(),mode);}
                public boolean enter(){enters++; return true;}
                public boolean release(){releases++; inbox.revoke("release"); inbox.tick(System.nanoTime(),v->held=v); return true;}
                public String fault(){return inbox.fault();}
            };
        }
    }
    public static void main(String[] args) throws Exception {
        UUID id=UUID.fromString(System.getenv("MCDN_BENCH_SESSION")); String nonce=System.getenv("MCDN_BENCH_NONCE");
        try(Socket socket=new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1",Integer.parseInt(args[0])),5000); socket.setSoTimeout(15000);
            var in=socket.getInputStream(); var out=socket.getOutputStream();
            out.write(Wire.encode(new Wire.Envelope(1,id,0,0,1,0,Control.hello("mc",nonce,"b".repeat(64),123,456,3))));
            var peer=new Control.Handshake().accept(read(in),id,2,"dc",nonce,"c".repeat(64),3);
            Ports ports=new Ports(); var session=new GuestSession(peer,ports); ports.session=session;
            AtomicBoolean eof=new AtomicBoolean(), stop=new AtomicBoolean(); AtomicReference<Throwable> failure=new AtomicReference<>();
            Thread reader=new Thread(()->{
                try { while(!stop.get()) { if(!session.receive(read(in),System.nanoTime())) break; } }
                catch(EOFException expected){eof.set(true); session.disconnect();}
                catch(Throwable ex){failure.set(ex); session.failed("reader");}
            });
            Thread writer=new Thread(()->{
                try { while(!stop.get()) {
                    var m=session.pollOutgoing(); if(m==null){Thread.sleep(1);continue;} session.sent(m.sequence()); out.write(Wire.encode(m));
                }}catch(Throwable ex){if(!stop.get())failure.set(ex);}
            });
            reader.setDaemon(true);writer.setDaemon(true);reader.start();writer.start();
            byte[] raw=Files.readAllBytes(Path.of(args[1])); ByteBuffer b=ByteBuffer.wrap(raw).order(ByteOrder.BIG_ENDIAN);
            b.putLong(16,id.getMostSignificantBits());b.putLong(24,id.getLeastSignificantBits()); var frame=Frame.decode(raw);
            long lastAck=1,deadline=System.nanoTime()+15_000_000_000L;
            while(!eof.get()&&failure.get()==null&&System.nanoTime()<deadline) {
                session.beginTick();
                if(session.state()==ModeGate.State.PREPARING&&session.offerFrame(frame)) {
                    session.spaceChecked("client",ports.world.stamp(),frame.frameId(),frame.nativeTick(),true);
                    session.spaceChecked("server",ports.world.stamp(),frame.frameId(),frame.nativeTick(),true);
                }
                if(ports.inbox!=null)ports.inbox.tick(System.nanoTime(),v->ports.held=v);
                session.endTick();
                if(session.consumedAck()!=lastAck){lastAck=session.consumedAck();session.heartbeat(1,session.state()==ModeGate.State.HERO?0:1);}
                if(session.fault()!=null)break; Thread.sleep(1);
            }
            session.beginTick(); session.endTick();stop.set(true);reader.join(500);writer.join(500);
            check(failure.get()==null&&eof.get()&&session.state()==ModeGate.State.HERO&&ports.held==0&&ports.enters==1&&ports.releases==1);
        }
        System.out.println("PIPELINE_JAVA_PASS separate reader/writer/game threads; complete geometry; gated binding; consumed-prefix ACK; release/EOF");
    }
}
