package dev.mcdn.tools;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Temporary lab window sizing through the game's own Window API; no input, world or bytecode edits. */
public final class FrameWindowAgent {
    private static Object call(Object value,String method)throws Exception{return value.getClass().getMethod(method).invoke(value);}
    private static Object own(Class<?> type,Object value,String name)throws Exception{Field field=type.getDeclaredField(name);field.setAccessible(true);return field.get(value);}
    public static void agentmain(String argument,Instrumentation instrumentation) {
        try {
            String[] parts=argument.split("\\|",2);boolean restore=parts[0].equals("restore");Path snapshot=Path.of(parts[1]);
            Class<?> probe=Arrays.stream(instrumentation.getAllLoadedClasses()).filter(c->c.getName().equals("dev.mcdn.frameprobe.FrameProbe")).findFirst().orElseThrow();
            Class<?> minecraft=Class.forName("net.minecraft.client.Minecraft",false,probe.getClassLoader());Object mc=minecraft.getMethod("getInstance").invoke(null);
            var inspected=new CompletableFuture<Properties>();
            minecraft.getMethod("execute",Runnable.class).invoke(mc,(Runnable)()->{
                try {
                    Path actual=((java.io.File)minecraft.getField("gameDirectory").get(mc)).toPath().toAbsolutePath().normalize();
                    if(!actual.equals(((Path)own(probe,null,"game")).toAbsolutePath().normalize()))throw new IllegalStateException("not configured lab");
                    Object window=call(mc,"getWindow");
                    if((Boolean)own(window.getClass(),window,"fullscreen"))throw new IllegalStateException("only windowed lab resizing supported");
                    Properties p=new Properties();p.setProperty("width",String.valueOf(call(window,"getScreenWidth")));p.setProperty("height",String.valueOf(call(window,"getScreenHeight")));p.setProperty("game",actual.toString());inspected.complete(p);
                }catch(Throwable error){inspected.completeExceptionally(error);}
            });
            Properties current=inspected.get(10,TimeUnit.SECONDS),requested=new Properties();
            if(restore){try(var reader=Files.newBufferedReader(snapshot)){requested.load(reader);}if(!requested.getProperty("game").equals(current.getProperty("game")))throw new IllegalStateException("restore lab differs");}
            else{if(Files.exists(snapshot))throw new IllegalStateException("size snapshot already exists");try(var writer=Files.newBufferedWriter(snapshot,StandardOpenOption.CREATE_NEW)){current.store(writer,"Before bounded MC GPU diagnostic resize");}requested.setProperty("width","960");requested.setProperty("height","540");}
            int width=Integer.parseInt(requested.getProperty("width")),height=Integer.parseInt(requested.getProperty("height"));
            var resized=new CompletableFuture<Boolean>();
            minecraft.getMethod("execute",Runnable.class).invoke(mc,(Runnable)()->{
                try{Object window=call(mc,"getWindow");window.getClass().getMethod("setWindowed",int.class,int.class).invoke(window,width,height);resized.complete(true);}
                catch(Throwable error){resized.completeExceptionally(error);}
            });
            resized.get(10,TimeUnit.SECONDS);System.out.println("MCDN_FRAME_WINDOW_"+(restore?"RESTORED":"SIZED")+" "+width+"x"+height);
        }catch(Throwable error){System.err.println("MCDN_FRAME_WINDOW_DIAG_FAILED "+error);}
    }
}
