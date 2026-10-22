using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using Mcdn.Ipc;

namespace Mcdn.DcFrameProbe;

public sealed partial class FrameProbeMod
{
    private bool liveMode;
    private volatile bool liveEnded;
    private string? liveDirectory;
    private long lastLiveReady;
    private ulong shownStream;
    private Guid liveSession;
    private bool fullView;
    private bool InitializeLive(string lab)
    {
        string? path=Environment.GetEnvironmentVariable("MCDN_DC_LIVE_COLOR_MANIFEST");if(path==null)return false;
        string full=Path.GetFullPath(path),allowed=Path.Combine(Path.GetFullPath(lab),"live-color")+Path.DirectorySeparatorChar;
        if(!full.StartsWith(allowed,StringComparison.OrdinalIgnoreCase)||new FileInfo(full).Length is <1 or >16384)throw new InvalidDataException("live manifest location/size");
        byte[] bytes=File.ReadAllBytes(full);
        if(Convert.ToHexStringLower(SHA256.HashData(bytes))!=Environment.GetEnvironmentVariable("MCDN_DC_LIVE_COLOR_SHA256"))throw new InvalidDataException("pinned live manifest required");
        using var json=JsonDocument.Parse(bytes);var cfg=json.RootElement;
        if(cfg.GetProperty("kind").GetString()!="mcdn-live-world-color-diagnostic-1"||cfg.GetProperty("eligibleForControl").GetBoolean()||Path.GetFullPath(cfg.GetProperty("dcGameRoot").GetString()!)!=Path.GetFullPath(Path.Combine(lab,"dc-game")))throw new InvalidDataException("live scope/root");
        string presentation=cfg.TryGetProperty("presentation",out var mode)?mode.GetString()??"":"thumbnail";
        if(presentation is not ("thumbnail" or "full-scene-diagnostic"))throw new InvalidDataException("live presentation");
        fullView=presentation=="full-scene-diagnostic";
        liveSession=Guid.ParseExact(cfg.GetProperty("session").GetString()!,"D");liveDirectory=Path.GetDirectoryName(full)!;
        string map=Path.GetFullPath(cfg.GetProperty("map").GetString()!),dll=Path.GetFullPath(cfg.GetProperty("dll").GetString()!),digest=cfg.GetProperty("dllSha256").GetString()!;
        if(Path.GetDirectoryName(map)!=liveDirectory||Path.GetDirectoryName(dll)!=liveDirectory)throw new InvalidDataException("private live session files required");
        long expires=cfg.GetProperty("expiresUnixMs").GetInt64(),now=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        if(expires<=now||expires-now>900000)throw new InvalidDataException("live session expiry");
        InitializeNativeInputLab(cfg,liveDirectory);
        liveMode=true;
        if(Environment.GetEnvironmentVariable("MCDN_DC_GUARD_CHECK_ONLY")!="1")
            new Thread(()=>LiveLoop(map,dll,digest,expires)){IsBackground=true,Name="MCDN-live-color-read"}.Start();
        Logger.Information("MCDN_DC_LIVE_COLOR_INITIALIZED session={Session}; input/Hero takeover disabled",liveSession);
        return true;
    }
    private static bool Fresh(long ready)=>ready>0&&Stopwatch.GetTimestamp()>=ready&&(Stopwatch.GetTimestamp()-ready)/(double)Stopwatch.Frequency<=1.5;
    private void LiveLoop(string map,string dll,string digest,long expires)
    {
        try
        {
            FrameMailbox.LoadNative(dll,digest);
            if(FrameMailbox.Frequency!=Stopwatch.Frequency)throw new InvalidDataException("native/managed QPC frequency mismatch");
            using var mailbox=new FrameMailbox(map,liveSession,384+1024*1024*4,false,true);
            ulong previous=0,epoch=0;int index=0;
            while(!stop.IsCancellationRequested&&DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()<expires)
            {
                FlushObservation();var frame=mailbox.ReadWorldColor();
                if(frame!=null)
                {
                    if(frame.Session!=liveSession||frame.FrameId<=previous||frame.StreamEpoch<epoch||frame.Frequency!=(ulong)Stopwatch.Frequency)throw new InvalidDataException("live session/order/clock");
                    previous=frame.FrameId;epoch=frame.StreamEpoch;
                    if(Fresh(checked((long)frame.ReadyQpc)))
                    {
                        byte[] raw=frame.Pixels();string rawHash=Convert.ToHexStringLower(SHA256.HashData(raw));
                        Interlocked.Exchange(ref pending,new Pixels(index++,frame.FrameId,frame.Width,frame.Height,raw,rawHash,"",liveSession.ToString("D"),Convert.ToHexStringLower(SHA256.HashData(frame.Encode())),frame.StreamEpoch,frame.NativeTick,(long)frame.ReadyQpc));
                    }
                }
                Thread.Sleep(10);
            }
            FlushObservation();
        }
        catch(Exception ex){failed=true;Logger.Error("MCDN DC live color disabled: {Error}",ex.ToString());}
        finally{liveEnded=true;Interlocked.Exchange(ref pending,null);Logger.Information("MCDN_DC_LIVE_COLOR_READER_STOPPED session={Session}",liveSession);}
    }
    private void FlushLiveObservation(Upload value)
    {
        var frame=value.Frame;
        var report=new{kind="dc-live-native-world-color-upload",session=frame.Source,frameId=frame.FrameId.ToString(System.Globalization.CultureInfo.InvariantCulture),streamEpoch=frame.StreamEpoch.ToString(System.Globalization.CultureInfo.InvariantCulture),nativeTick=frame.Tick.ToString(System.Globalization.CultureInfo.InvariantCulture),width=frame.Width,height=frame.Height,rawSha256=frame.RawHash,packetSha256=frame.PacketHash,readyQpc=frame.ReadyQpc,uploadedQpc=value.Timestamp,frequency=Stopwatch.Frequency,recordedReplay=false,eligibleForControl=false};
        string text=JsonSerializer.Serialize(report);
        File.AppendAllText(Path.Combine(liveDirectory!,"consumer.jsonl"),text+"\n");
        string path=Path.Combine(liveDirectory!,"consumer-latest.json");File.WriteAllText(path+".tmp",text);
        try{File.Move(path+".tmp",path,true);}
        catch(IOException ex) when((ex.HResult&0xffff) is 32 or 5){} // Optional snapshot; journal remains authoritative.
        catch(UnauthorizedAccessException){} // A Windows reader may deny delete/replace sharing.
    }
}
