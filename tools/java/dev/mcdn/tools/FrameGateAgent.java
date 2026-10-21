package dev.mcdn.tools;

import java.lang.instrument.Instrumentation;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** One read-only snapshot, scheduled on Minecraft's own thread. No transformer, input or game-state writes. */
public final class FrameGateAgent {
    private static Object field(Object value,String name)throws Exception{return value.getClass().getField(name).get(value);}
    private static Object call(Object value,String name)throws Exception{Method method=value.getClass().getMethod(name);method.setAccessible(true);return method.invoke(value);}
    private static Object own(Class<?> type,String name)throws Exception{Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(null);}
    public static void agentmain(String destination,Instrumentation instrumentation) {
        // Catch every failure in the diagnostic agent so it cannot escape onto a game thread.
        try {
            Class<?> probe=Arrays.stream(instrumentation.getAllLoadedClasses()).filter(c->c.getName().equals("dev.mcdn.frameprobe.FrameProbe")).findFirst().orElseThrow();
            Class<?> minecraft=Class.forName("net.minecraft.client.Minecraft",false,probe.getClassLoader());
            Object mc=minecraft.getMethod("getInstance").invoke(null);
            var future=new CompletableFuture<Properties>();
            Runnable read=()->{
                try {
                    Properties p=new Properties();p.setProperty("scope","read-only native render gate snapshot; no game-state mutation or bytecode transform");
                    p.setProperty("thread",Thread.currentThread().getName());
                    p.setProperty("gameDirectory",String.valueOf(field(mc,"gameDirectory")));
                    Path actual=Path.of(String.valueOf(field(mc,"gameDirectory"))).toAbsolutePath().normalize();
                    Path expected=Path.of(String.valueOf(own(probe,"game"))).toAbsolutePath().normalize();
                    if(!actual.equals(expected))throw new IllegalStateException("not the configured lab");
                    for(String name:new String[]{"configured","inFlight","failed","requests","id","next","game"})p.setProperty("probe."+name,String.valueOf(own(probe,name)));
                    p.setProperty("nowNanoTime",Long.toString(System.nanoTime()));
                    p.setProperty("hasLevel",Boolean.toString(field(mc,"level")!=null));p.setProperty("hasPlayer",Boolean.toString(field(mc,"player")!=null));
                    p.setProperty("hasServer",Boolean.toString(call(mc,"getSingleplayerServer")!=null));p.setProperty("paused",String.valueOf(call(mc,"isPaused")));
                    Object renderer=field(mc,"gameRenderer"),state=call(renderer,"gameRenderState"),target=call(renderer,"mainRenderTarget");
                    p.setProperty("shouldRenderLevel",String.valueOf(field(state,"shouldRenderLevel")));
                    Object levelState=field(state,"levelRenderState"),camera=field(levelState,"cameraRenderState"),player=field(levelState,"playerRenderState");
                    p.setProperty("camera.initialized",String.valueOf(field(camera,"initialized")));p.setProperty("renderState.hasPlayer",String.valueOf(field(player,"hasPlayer")));
                    p.setProperty("target.width",String.valueOf(field(target,"width")));p.setProperty("target.height",String.valueOf(field(target,"height")));
                    Object texture=call(target,"getColorTexture");p.setProperty("texture.exists",Boolean.toString(texture!=null));
                    if(texture!=null)p.setProperty("texture.format",String.valueOf(call(texture,"getFormat")));
                    future.complete(p);
                }catch(Throwable error){future.completeExceptionally(error);}
            };
            // execute is the thread-safe native task submission API; object fields above are read only inside the task.
            minecraft.getMethod("execute",Runnable.class).invoke(mc,read);
            Properties result=future.get(10,TimeUnit.SECONDS);
            try(var writer=Files.newBufferedWriter(Path.of(destination))){result.store(writer,"MCDN own offline lab gate diagnosis");}
        }catch(Throwable error){System.err.println("MCDN_FRAME_GATE_DIAG_FAILED "+error);}
    }
}
