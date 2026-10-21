package dev.mcdn.tests;
import dev.mcdn.protocol.WorldColorFrame;
import dev.mcdn.ipc.NativeMailbox;
import java.nio.*;
import java.nio.file.*;
import java.net.Socket;
import java.io.*;
import java.util.*;

public final class WorldColorBench {
    public static void main(String[] args)throws Exception {
        Path vectors=Path.of(args[0]);int count=0;
        try(var files=Files.list(vectors)){for(Path path:files.filter(p->p.toString().endsWith(".bin")).sorted().toList()){
            byte[] bytes=Files.readAllBytes(path);boolean valid=path.getFileName().toString().startsWith("valid-");boolean accepted;
            try{var frame=WorldColorFrame.decode(bytes);accepted=Arrays.equals(bytes,frame.encode());}catch(IllegalArgumentException ex){accepted=false;}
            if(accepted!=valid)throw new IllegalStateException("codec vector "+path);count++;
        }}
        byte[] source=Files.readAllBytes(vectors.resolve("valid-frame.bin"));var base=WorldColorFrame.decode(source);
        NativeMailbox.load(Path.of(args[1]),args[2]);
        try(var box=new NativeMailbox(Path.of(args[3]),base.session(),source.length,true);
            var socket=new Socket("127.0.0.1",Integer.parseInt(args[4]));
            var input=new BufferedReader(new InputStreamReader(socket.getInputStream(),java.nio.charset.StandardCharsets.US_ASCII));
            var output=new PrintWriter(socket.getOutputStream(),true,java.nio.charset.StandardCharsets.US_ASCII)) {
            try{box.read();throw new IllegalStateException("mixed channel accepted");}catch(IllegalStateException expected){if(!expected.getMessage().contains("MCDF"))throw expected;}
            for(int i=1;i<=20;i++){
                ByteBuffer.wrap(source).order(ByteOrder.LITTLE_ENDIAN).putLong(56,i);
                if(!box.publishWorldColor(WorldColorFrame.decode(source)))throw new IllegalStateException("unexpected busy publish");
                output.println(i);if(!Integer.toString(i).equals(input.readLine()))throw new IllegalStateException("upload ack");
            }
            output.println("done");
        }
        System.out.println("WORLD_COLOR_JAVA_PASS vectors="+count+" nativeFrames=20");
    }
}
