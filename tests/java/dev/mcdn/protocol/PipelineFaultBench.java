package dev.mcdn.protocol;

import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** Adversarial ordering tests at the reader/game-consumer boundary; no game objects. */
public final class PipelineFaultBench {
    private static void check(boolean ok) { if (!ok) throw new AssertionError("pipeline fault assertion"); }
    private static void rejects(Runnable task) {
        try { task.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("expected rejection");
    }
    private static Control.Peer peer(UUID id, long caps) {
        String nonce="a".repeat(64), build="b".repeat(64);
        return new Control.Handshake().accept(new Wire.Envelope(2,id,0,0,1,1,
            Control.hello("dc",nonce,build,123,456,caps)),id,2,"dc",nonce,build,caps);
    }
    private static final class Harness implements GuestSession.Ports {
        final World world; final Frame frame; final GuestSession session;
        InputInbox inbox; long sequence=1; int held, installs, enters, releases;
        Harness(World world, Frame frame) {
            this.world=world; this.frame=frame; session=new GuestSession(peer(world.stamp().session(),3),this);
        }
        public long qpc(){return 101;} public long frequency(){return 1000;}
        public void installWorld(World next) {
            installs++; session.applied("client",next.stamp(),1); session.applied("server",next.stamp(),1);
        }
        public ModeGate.Binding binding(InputInbox next) {
            inbox=next;
            return new ModeGate.Binding() {
                public boolean matches(World.Stamp stamp,long mode){return inbox.matches(stamp.session(),stamp.epoch(),mode);}
                public boolean enter(){enters++; return true;}
                public boolean release(){releases++; inbox.revoke("release"); inbox.tick(System.nanoTime(),v->held=v);return true;}
                public String fault(){return inbox.fault();}
            };
        }
        boolean receive(int type,long mode,byte[] body) {
            return session.receive(new Wire.Envelope(type,world.stamp().session(),world.stamp().epoch(),mode,++sequence,1,body),System.nanoTime());
        }
        void beginWorld() {
            check(receive(4,0,Control.encode("revision",Long.toUnsignedString(world.stamp().revision()),"digest",world.stamp().digest(),"totalBytes",Integer.toString(world.encode().length))));
        }
        void transfer() {
            beginWorld(); byte[] bytes=world.encode();
            for(int offset=0,index=0;offset<bytes.length;index++) {
                int end=Math.min(offset+1024,bytes.length);
                check(receive(5,0,Control.encode("revision",Long.toUnsignedString(world.stamp().revision()),"index",Integer.toString(index),
                    "data",Base64.getEncoder().encodeToString(Arrays.copyOfRange(bytes,offset,end)))));offset=end;
            }
            check(receive(6,0,stamp()));
        }
        byte[] stamp(String... more) {
            String[] fields=new String[4+more.length];fields[0]="revision";fields[1]=Long.toUnsignedString(world.stamp().revision());
            fields[2]="digest";fields[3]=world.stamp().digest();System.arraycopy(more,0,fields,4,more.length);return Control.encode(fields);
        }
        void activate() {
            transfer();session.beginTick();session.endTick();
            check(receive(9,1,stamp("cameraEpoch","1","carrierPrepared","1")));session.beginTick();
            check(session.offerFrame(frame));check(session.spaceChecked("client",world.stamp(),frame.frameId(),frame.nativeTick(),true));
            check(session.spaceChecked("server",world.stamp(),frame.frameId(),frame.nativeTick(),true));
            check(receive(11,1,stamp("cameraEpoch","1","frameId",Long.toUnsignedString(frame.frameId()),"nativeTick",Long.toUnsignedString(frame.nativeTick()))));
            session.beginTick();session.endTick();check(session.state()==ModeGate.State.ACTIVE&&enters==1);
        }
        void input(long n,int held,int pressed,int released) {
            check(receive(13,1,Control.encodeInput(new Control.Input(n,n,n,held,pressed,released))));
        }
    }
    public static void main(String[] args) throws Exception {
        World world=World.decode(Files.readAllBytes(Path.of(args[0])));Frame frame=Frame.decode(Files.readAllBytes(Path.of(args[1])));
        UUID id=world.stamp().session();Control.Peer peer=peer(id,3);
        SessionFlow flow=new SessionFlow(peer);
        var first=flow.accept(new Wire.Envelope(3,id,1,0,2,1,new byte[0]));
        var second=flow.accept(new Wire.Envelope(3,id,1,0,3,1,new byte[0]));
        SessionFlow.complete(second);flow.flushConsumed();check(flow.consumed()==1);
        SessionFlow.complete(first);flow.flushConsumed();check(flow.consumed()==3);
        rejects(()->flow.accept(new Wire.Envelope(3,id,1,0,4,2,new byte[0]))); // cannot ACK an unsent message
        flow.sent(2);var third=flow.accept(new Wire.Envelope(3,id,1,0,4,2,new byte[0]));
        rejects(()->flow.accept(new Wire.Envelope(3,id,1,0,5,1,new byte[0])));
        rejects(()->flow.accept(new Wire.Envelope(3,UUID.randomUUID(),1,0,5,2,new byte[0])));
        SessionFlow.complete(third);flow.flushConsumed();check(flow.consumed()==4);
        SessionFlow bounded=new SessionFlow(peer);
        for(int i=2;i<130;i++)bounded.accept(new Wire.Envelope(3,id,1,0,i,1,new byte[0]));
        rejects(()->bounded.accept(new Wire.Envelope(3,id,1,0,130,1,new byte[0])));
        Harness dummy=new Harness(world,frame);rejects(()->new GuestSession(peer(id,1),dummy));

        Harness cancelled=new Harness(world,frame);cancelled.transfer();cancelled.beginWorld();
        cancelled.session.beginTick();cancelled.session.endTick();
        check(cancelled.installs==0&&cancelled.session.consumedAck()==cancelled.sequence&&cancelled.session.fault()==null);

        Harness tap=new Harness(world,frame);tap.activate();long committed=tap.sequence;
        tap.input(1,1,1,0);tap.input(2,0,0,1);tap.session.beginTick();
        check(tap.session.consumedAck()==committed); // enqueue is not native consumption
        tap.inbox.tick(System.nanoTime(),v->tap.held=v);tap.session.endTick();
        check(tap.held==1&&tap.session.consumedAck()==committed+1);
        tap.inbox.tick(System.nanoTime(),v->tap.held=v);tap.session.endTick();
        check(tap.held==0&&tap.session.consumedAck()==tap.sequence);

        Harness release=new Harness(world,frame);release.activate();release.input(1,1,1,0);
        check(release.receive(12,1,Control.encode("reason","focus-lost")));release.session.beginTick();release.session.endTick();
        check(release.held==0&&release.releases==1&&release.session.state()==ModeGate.State.HERO&&release.session.consumedAck()==release.sequence);

        Harness bad=new Harness(world,frame);bad.activate();bad.input(1,1,1,0);bad.session.beginTick();
        bad.inbox.tick(System.nanoTime(),v->bad.held=v);bad.session.endTick();check(bad.held==1);
        check(!bad.receive(5,0,Control.encode("revision","1","index","0","data","AA=="))); // no transfer baseline
        bad.session.beginTick();bad.session.endTick();check(bad.held==0&&bad.releases==1&&bad.session.state()==ModeGate.State.HERO);

        AtomicReference<Throwable> failure=new AtomicReference<>();
        Thread wrong=new Thread(()->{try{tap.session.beginTick();}catch(Throwable ex){failure.set(ex);}});wrong.start();wrong.join();
        check(failure.get() instanceof IllegalStateException);
        System.out.println("PIPELINE_FAULTS_PASS ACK holes/bounds/auth; superseded-world cancellation; native short-tap consumption; urgent release; malformed-stream clear; thread ownership");
    }
}
