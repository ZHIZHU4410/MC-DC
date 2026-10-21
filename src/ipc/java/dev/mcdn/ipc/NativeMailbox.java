package dev.mcdn.ipc;

import dev.mcdn.protocol.Frame;
import dev.mcdn.protocol.WorldColorFrame;
import java.nio.ByteBuffer;
import java.nio.file.*;
import java.security.*;
import java.util.*;

/** JNI-backed latest-frame mailbox. All waits are native Win32 0ms attempts. Single owning thread. */
public final class NativeMailbox implements AutoCloseable {
    private static String loaded;
    private final Thread owner=Thread.currentThread();
    private final UUID session;
    private long handle;
    private boolean fault;
    private final boolean worldColor;
    @SuppressWarnings("restricted") // Explicit JNI loading; runtime must opt in with --enable-native-access=ALL-UNNAMED.
    public static synchronized void load(Path dll,String sha256) throws Exception {
        String actual=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(dll)));
        if(!actual.equals(sha256))throw new IllegalArgumentException("native library hash mismatch");
        if(loaded!=null){if(!loaded.equals(actual))throw new IllegalStateException("different native library already loaded");return;}
        System.load(dll.toAbsolutePath().toString());
        if(api0()!=1)throw new IllegalStateException("native mailbox ABI mismatch");loaded=actual;
    }
    public NativeMailbox(Path file,UUID session,int slotBytes){this(file,session,slotBytes,false);}
    public NativeMailbox(Path file,UUID session,int slotBytes,boolean worldColor) {
        this.worldColor=worldColor;
        if(loaded==null)throw new IllegalStateException("load verified native library first");
        this.session=session;
        byte[] id=ByteBuffer.allocate(16).putLong(session.getMostSignificantBits()).putLong(session.getLeastSignificantBits()).array();
        handle=worldColor?openWorld0(file.toAbsolutePath().toString(),id,slotBytes):open0(file.toAbsolutePath().toString(),id,slotBytes);
        if(handle==0)throw new IllegalStateException("native open failed");
    }
    private void thread(){if(Thread.currentThread()!=owner||handle==0||fault)throw new IllegalStateException("closed/faulted mailbox or wrong owner thread");}
    public boolean publish(Frame frame) {
        thread();if(worldColor)throw new IllegalStateException("MCDF method on world-color channel");if(!frame.session().equals(session))throw new IllegalArgumentException("frame session");
        try{return publish0(handle,frame.encode());}catch(RuntimeException ex){fault=true;poison0(handle);throw ex;}
    }
    public Frame read() {
        thread();if(worldColor)throw new IllegalStateException("MCDF method on world-color channel");try{byte[] bytes=read0(handle);return bytes==null?null:Frame.decode(bytes);}
        catch(RuntimeException ex){fault=true;poison0(handle);throw ex;}
    }
    public boolean publishWorldColor(WorldColorFrame frame) {
        thread();if(!worldColor||!frame.session().equals(session))throw new IllegalArgumentException("world-color channel/session");
        try{return publish0(handle,frame.encode());}catch(RuntimeException ex){fault=true;poison0(handle);throw ex;}
    }
    public WorldColorFrame readWorldColor() {
        thread();if(!worldColor)throw new IllegalStateException("world-color method on MCDF channel");
        try{byte[] value=read0(handle);return value==null?null:WorldColorFrame.decode(value);}catch(RuntimeException ex){fault=true;poison0(handle);throw ex;}
    }
    public static long qpc(){return qpc0();}
    public static long frequency(){return frequency0();}
    public long[] diagnosticCapture(){thread();return capture0(handle);}
    public boolean diagnosticLock(int which){thread();return lock0(handle,which);}
    public void diagnosticUnlock(int which){thread();unlock0(handle,which);}
    public void diagnosticPartialWrite(int which){thread();corrupt0(handle,which);}
    @Override public void close(){if(Thread.currentThread()!=owner)throw new IllegalStateException("mailbox owner thread only");if(handle!=0){close0(handle);handle=0;}}
    private static native int api0();
    private static native long openWorld0(String file,byte[] session,int slotBytes);
    private static native long open0(String file,byte[] session,int slotBytes);
    private static native void close0(long handle);
    private static native boolean publish0(long handle,byte[] packet);
    private static native byte[] read0(long handle);
    private static native void poison0(long handle);
    private static native long qpc0();
    private static native long frequency0();
    private static native long[] capture0(long handle);
    private static native boolean lock0(long handle,int which);
    private static native void unlock0(long handle,int which);
    private static native void corrupt0(long handle,int which);
}
