package dev.mcdn.ipc;

import dev.mcdn.protocol.Frame;
import java.io.*;
import java.net.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.CRC32;

/** Synthetic packets only. No Minecraft classes, game main, graphics or physical input. */
public final class MailboxBench {
    private static byte[] template;
    private static UUID session;
    private static Frame frame(long id) {
        byte[] packet=Arrays.copyOf(template,256+96*64*4);
        ByteBuffer b=ByteBuffer.wrap(packet).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(12,packet.length-256);b.putLong(56,id);b.putLong(64,id);
        ByteBuffer network=ByteBuffer.wrap(packet).order(ByteOrder.BIG_ENDIAN);
        network.putLong(16,session.getMostSignificantBits()).putLong(24,session.getLeastSignificantBits());
        b.putInt(80,96).putInt(84,64).putInt(88,96*4);
        b.putDouble(112,(id&0xffffffffL)+0.25);
        long qpc=NativeMailbox.qpc();for(int o=192;o<=216;o+=8)b.putLong(o,qpc);
        b.putLong(224,NativeMailbox.frequency());
        for(int j=0;j<packet.length-256;j++)packet[256+j]=(byte)((id>>>((j&7)*8))^(j*31));
        CRC32 crc=new CRC32();crc.update(packet,256,packet.length-256);b.putInt(236,(int)crc.getValue());
        return Frame.decode(packet);
    }
    private static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
    private static void publish(NativeMailbox box,long id){
        Frame frame=frame(id);long deadline=System.nanoTime()+5_000_000_000L;
        while(!box.publish(frame)){if(System.nanoTime()>deadline)throw new IllegalStateException("bounded publish timeout");Thread.yield();}
    }
    public static void main(String[] args) {
        try{run(args);}catch(Throwable ex){System.err.println("MAILBOX_JAVA_FAIL "+ex);System.exit(2);}
    }
    private static void run(String[] args)throws Exception {
        NativeMailbox.load(Path.of(args[0]),args[1]);template=Files.readAllBytes(Path.of(args[2]));
        session=UUID.fromString(args[4]);int capacity=Integer.parseInt(args[5]),port=Integer.parseInt(args[6]);
        try(NativeMailbox box=new NativeMailbox(Path.of(args[3]),session,capacity);
            Socket socket=new Socket(InetAddress.getLoopbackAddress(),port);
            BufferedReader input=new BufferedReader(new InputStreamReader(socket.getInputStream(),StandardCharsets.US_ASCII));
            PrintWriter output=new PrintWriter(new OutputStreamWriter(socket.getOutputStream(),StandardCharsets.US_ASCII),true)) {
            socket.setSoTimeout(15000);output.println("READY "+NativeMailbox.frequency());
            for(String command;(command=input.readLine())!=null;){
                String[] parts=command.split(" ");
                switch(parts[0]){
                    case "BUSY" -> {Frame busyFrame=frame(1);long before=System.nanoTime();boolean accepted=box.publish(busyFrame);long elapsed=System.nanoTime()-before;
                        require(!accepted,"busy lock advanced publication");output.println("BUSY_OK "+elapsed);}
                    case "PUB" -> {publish(box,Long.parseUnsignedLong(parts[1]));output.println("PUBLISHED");}
                    case "STRESS" -> {for(long id=5;id<=2000;id++)publish(box,id);output.println("STRESS_DONE");}
                    case "CORRUPT" -> {
                        publish(box,1);int which=(int)box.diagnosticCapture()[0]+1;
                        require(box.diagnosticLock(which),"corruption lock");box.diagnosticPartialWrite(which);box.diagnosticUnlock(which);
                        output.println("CORRUPTED");
                    }
                    case "ABANDON" -> {
                        publish(box,1);int which=parts[1].equals("publication")?0:(int)box.diagnosticCapture()[0]+1;
                        require(box.diagnosticLock(which),"lock before abandonment");box.diagnosticPartialWrite(which);
                        output.println("LOCKED_EXIT "+which);
                        // Normal process exit while the owning thread holds a partially written native mutex.
                        // Deliberately bypass AutoCloseable: test WAIT_ABANDONED without a JVM crash or WER dialog.
                        System.exit(0);
                    }
                    case "READ" -> {
                        Frame got=box.read();require(got!=null&&got.frameId()==1&&got.session().equals(session),"reverse read");
                        byte[] bytes=got.encode();for(int j=0;j<bytes.length-256;j++)require(bytes[256+j]==(byte)(1L>>>((j&7)*8)^(j*31)),"reverse pixels");
                        require(box.read()==null,"reverse duplicate");output.println("READ_OK");
                    }
                    case "QUIT" -> {output.println("BYE");return;}
                    default -> throw new IllegalArgumentException("unknown command");
                }
            }
        }
    }
}
