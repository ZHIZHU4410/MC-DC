using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using Mcdn.Protocol;
using Microsoft.Win32.SafeHandles;

namespace Mcdn.Ipc;

public sealed class MailboxFaultException(int status) : IOException($"Native mailbox fault {status}; create a new session")
{
    public int Status { get; } = status;
}

public sealed class FrameMailbox : IDisposable
{
    public const int MaximumSlotBytes=256+1024*1024*4;
    private readonly int owner=Environment.CurrentManagedThreadId;
    private readonly Guid session;
    private readonly Handle handle;
    private readonly byte[] buffer;
    private bool fault;
    private readonly bool worldColor;
    public static void LoadNative(string dll,string sha256) => Native.Load(dll,sha256);
    public static void CreatePrivateDirectory(string path)
    { Native.RequireLoaded();if(Native.PrivateDirectory(path)!=1)throw new Win32Exception(Marshal.GetLastPInvokeError(),"private session directory creation failed"); }
    public FrameMailbox(string path,Guid session,int slotBytes,bool create,bool worldColor=false)
    {
        this.worldColor=worldColor;
        if(slotBytes<(worldColor?384:256)||slotBytes>(worldColor?384+1024*1024*4:MaximumSlotBytes))throw new ArgumentOutOfRangeException(nameof(slotBytes));
        Native.RequireLoaded();this.session=session;buffer=new byte[slotBytes];
        nint raw=worldColor?Native.OpenWorld(path,session.ToByteArray(bigEndian:true),(uint)slotBytes,create?1:0):Native.Open(path,session.ToByteArray(bigEndian:true),(uint)slotBytes,create?1:0);
        if(raw==0)throw new Win32Exception(Marshal.GetLastPInvokeError(),"open mailbox failed");
        handle=new Handle(raw);
    }
    private void Thread()
    {if(owner!=Environment.CurrentManagedThreadId||handle.IsClosed||fault)throw new InvalidOperationException("mailbox closed/faulted or wrong owning thread");}
    private bool Result(int status)
    {if(status>=0)return status==1;fault=true;Native.Poison(handle);throw new MailboxFaultException(status);}
    public bool Publish(Frame frame)
    {
        Thread();if(worldColor)throw new InvalidOperationException("MCDF method on world-color channel");if(frame.Session!=session)throw new ArgumentException("frame session");
        byte[] packet=frame.Encode();return Result(Native.Publish(handle,packet,(uint)packet.Length));
    }
    public Frame? Read()
    {
        Thread();if(worldColor)throw new InvalidOperationException("MCDF method on world-color channel");if(!Result(Native.Read(handle,buffer,(uint)buffer.Length,out uint size)))return null;
        try{return Frame.Decode(buffer.AsSpan(0,checked((int)size)));}
        catch{fault=true;Native.Poison(handle);throw;}
    }
    public bool PublishWorldColor(WorldColorFrame frame)
    {
        Thread();if(!worldColor||frame.Session!=session)throw new ArgumentException("world-color channel/session");
        byte[] packet=frame.Encode();return Result(Native.Publish(handle,packet,(uint)packet.Length));
    }
    public WorldColorFrame? ReadWorldColor()
    {
        Thread();if(!worldColor)throw new InvalidOperationException("world-color method on MCDF channel");
        if(!Result(Native.Read(handle,buffer,(uint)buffer.Length,out uint size)))return null;
        try{return WorldColorFrame.Decode(buffer.AsSpan(0,checked((int)size)));}catch{fault=true;Native.Poison(handle);throw;}
    }
    public readonly record struct Publication(uint Slot,ulong FrameId);
    public Publication? DiagnosticCapture()
    {Thread();return Result(Native.Capture(handle,out uint slot,out ulong id))?new(slot,id):null;}
    public Frame? DiagnosticReadCaptured(Publication publication)
    {
        Thread();if(!Result(Native.ReadCaptured(handle,publication.Slot,publication.FrameId,buffer,(uint)buffer.Length,out uint size)))return null;
        try{return Frame.Decode(buffer.AsSpan(0,checked((int)size)));}catch{fault=true;Native.Poison(handle);throw;}
    }
    public bool DiagnosticLock(int which){Thread();return Result(Native.Lock(handle,which));}
    public void DiagnosticUnlock(int which){Thread();if(Native.Unlock(handle,which)!=1)throw new IOException("diagnostic unlock failed");}
    public static long Qpc {get{Native.RequireLoaded();return Native.Qpc();}}
    public static long Frequency {get{Native.RequireLoaded();return Native.Frequency();}}
    public void Dispose(){if(owner!=Environment.CurrentManagedThreadId)throw new InvalidOperationException("mailbox owner thread only");handle.Dispose();}

    private sealed class Handle : SafeHandleZeroOrMinusOneIsInvalid
    {
        internal Handle(nint value):base(true){SetHandle(value);}
        protected override bool ReleaseHandle(){Native.Close(handle);return true;}
    }
    private static class Native
    {
        private static nint library;
        private static string? digest;
        private static readonly object loadLock=new();
        internal static void RequireLoaded(){if(library==0)throw new InvalidOperationException("load hash-verified native library first");}
        internal static void Load(string path,string expected)
        {lock(loadLock){LoadLocked(path,expected);}}
        private static void LoadLocked(string path,string expected)
        {
            if(!OperatingSystem.IsWindows()||!Environment.Is64BitProcess)throw new PlatformNotSupportedException("Win64 native mailbox required");
            string actual=Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path)));
            if(actual!=expected)throw new InvalidDataException("native DLL hash mismatch");
            if(library!=0){if(actual!=digest)throw new InvalidOperationException("different native DLL loaded");return;}
            library=NativeLibrary.Load(Path.GetFullPath(path));
            NativeLibrary.SetDllImportResolver(typeof(FrameMailbox).Assembly,(name,_,_)=>name=="mcdn_ipc"?library:0);
            if(Api()!=1)throw new InvalidDataException("native ABI mismatch");digest=actual;
        }
        [DllImport("mcdn_ipc",EntryPoint="mcdn_api_version",CallingConvention=CallingConvention.Cdecl)] internal static extern uint Api();
        [DllImport("mcdn_ipc",EntryPoint="mcdn_private_directory",CharSet=CharSet.Unicode,SetLastError=true,CallingConvention=CallingConvention.Cdecl)] internal static extern int PrivateDirectory(string path);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_open",CharSet=CharSet.Unicode,SetLastError=true,CallingConvention=CallingConvention.Cdecl)] internal static extern nint Open(string path,byte[] session,uint slotBytes,int create);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_open_world_color",CharSet=CharSet.Unicode,SetLastError=true,CallingConvention=CallingConvention.Cdecl)] internal static extern nint OpenWorld(string path,byte[] session,uint slotBytes,int create);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_close",CallingConvention=CallingConvention.Cdecl)] internal static extern void Close(nint value);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_poison",CallingConvention=CallingConvention.Cdecl)] internal static extern void Poison(Handle value);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_publish",CallingConvention=CallingConvention.Cdecl)] internal static extern int Publish(Handle value,byte[] packet,uint size);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_read",CallingConvention=CallingConvention.Cdecl)] internal static extern int Read(Handle value,[Out]byte[] output,uint capacity,out uint size);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_capture",CallingConvention=CallingConvention.Cdecl)] internal static extern int Capture(Handle value,out uint slot,out ulong id);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_read_captured",CallingConvention=CallingConvention.Cdecl)] internal static extern int ReadCaptured(Handle value,uint slot,ulong id,[Out]byte[] output,uint capacity,out uint size);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_diagnostic_lock",CallingConvention=CallingConvention.Cdecl)] internal static extern int Lock(Handle value,int which);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_diagnostic_unlock",CallingConvention=CallingConvention.Cdecl)] internal static extern int Unlock(Handle value,int which);
        [DllImport("mcdn_ipc",EntryPoint="mcdn_qpc",CallingConvention=CallingConvention.Cdecl)] internal static extern long Qpc();
        [DllImport("mcdn_ipc",EntryPoint="mcdn_frequency",CallingConvention=CallingConvention.Cdecl)] internal static extern long Frequency();
    }
}
