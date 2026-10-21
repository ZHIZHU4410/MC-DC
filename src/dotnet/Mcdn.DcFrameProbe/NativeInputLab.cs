using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using Mcdn.Protocol;

namespace Mcdn.DcFrameProbe;

public sealed partial class FrameProbeMod
{
    private sealed record NativeLabState(string Stage,bool InputRestored,ulong Tick,ulong Consumed,double X,double Y,double Z,long Received);
    private sealed record InputHeroSample(int Uid,double X,double Y,int Life,bool Freeze,bool AlwaysUpdated,bool CanUpdate,bool GamePaused);
    private sealed record NativeKeys(int Held,ulong Tick,long Captured,InputHeroSample Hero);
    private sealed class HeroInputLease(dc.en.Hero hero)
    {
        public readonly int Uid=hero.__uid;
        private readonly bool freeze=hero.isFreeze,always=hero.isAlwaysUpdated;
        public void Enter(){if(freeze||Math.Abs(hero.dx)>.01||Math.Abs(hero.dy)>.01||hero.life<=0)throw new InvalidOperationException("standing unfrozen Hero required");hero.isAlwaysUpdated=false;hero.isFreeze=true;if(hero.canUpdate())throw new InvalidOperationException("Hero still owns updates");}
        public void Release(){hero.isFreeze=freeze;hero.isAlwaysUpdated=always;if(hero.isFreeze!=freeze||hero.isAlwaysUpdated!=always)throw new InvalidOperationException("Hero flags restore pending");}
        public bool Valid()=>hero.life>0&&!hero.destroyed&&hero.isFreeze&&!hero.isAlwaysUpdated&&!hero.canUpdate();
        public InputHeroSample Sample()=>new(hero.__uid,hero.cx+hero.xr,hero.cy+hero.yr,hero.life,hero.isFreeze,hero.isAlwaysUpdated,hero.canUpdate(),dc.pr.Game.Class.ME?.paused??true);
    }
    private readonly ConcurrentQueue<NativeKeys> nativeKeys=new();
    private NativeLabState? nativeLabState;
    private volatile bool nativeLabEnabled,nativeLabEnded,nativeLabRelease;
    private volatile string? nativeLabFault;
    private string? nativeLabDirectory;
    private HeroInputLease? heroInputLease;
    private bool nativeLabUsed,lastF7;
    private ulong nativeHostTick;
    private long nextNativeCapture,nativeReleaseAt,nativeBegan;
    [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int key);
    private static bool KeyDown(int key)=>(GetAsyncKeyState(key)&0x8000)!=0;
    private static bool NativeFrameFresh(long timestamp)=>timestamp>0&&Stopwatch.GetTimestamp()>=timestamp&&(Stopwatch.GetTimestamp()-timestamp)/(double)Stopwatch.Frequency<=.5;
    private void InitializeNativeInputLab(JsonElement cfg,string directory)
    {
        if(!cfg.TryGetProperty("inputLab",out var enabled)||!enabled.GetBoolean())return;
        if(Environment.GetEnvironmentVariable("MCDN_DC_GUARD_CHECK_ONLY")=="1")return;
        string mcBuild=cfg.GetProperty("mcBuild").GetString()!,dcBuild=cfg.GetProperty("dcBuild").GetString()!,nonce=cfg.GetProperty("controlNonce").GetString()!,geometry=cfg.GetProperty("geometryDigest").GetString()!;
        if(Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(Assembly.GetExecutingAssembly().Location)))!=dcBuild)throw new InvalidDataException("actual native input host build");
        int port=cfg.GetProperty("controlPort").GetInt32();ulong world=ulong.Parse(cfg.GetProperty("geometryEpoch").GetString()!,CultureInfo.InvariantCulture);
        if(port is <1024 or >65535||world==0)throw new InvalidDataException("native input endpoint/context");
        nativeLabDirectory=directory;nativeLabEnabled=true;
        new Thread(()=>NativeInputWorker(port,world,mcBuild,dcBuild,nonce,geometry)){IsBackground=true,Name="MCDN-native-input-host"}.Start();
        Logger.Information("MCDN_NATIVE_INPUT_LAB_HOST_INITIALIZED; F7 opt-in; no production MODE");
    }
    private void NativeInputWorker(int port,ulong world,string mcBuild,string dcBuild,string nonce,string geometry)
    {
        try
        {
            var listener=new TcpListener(IPAddress.Loopback,port);listener.Start(1);
            try
            {
                long acceptUntil=Stopwatch.GetTimestamp()+Stopwatch.Frequency*120;
                while(!listener.Pending()){if(stop.IsCancellationRequested||Stopwatch.GetTimestamp()>acceptUntil)throw new IOException("native guest connect timeout");Thread.Sleep(20);}
                using var client=listener.AcceptTcpClient();client.NoDelay=true;client.ReceiveTimeout=20;client.SendTimeout=200;using var stream=client.GetStream();
                var decoder=new StreamDecoder();var handshake=new Control.Handshake();bool verified=false,sentRelease=false;ulong sequence=1,inputSeq=0,eventSeq=0,lastIncoming=1;int previousHeld=0;
                var ack=new Control.AckWindow();ack.Sent(1);byte[] buffer=new byte[4096];
                void Send(Envelope packet){stream.Write(Wire.Encode(packet));}
                while(!stop.IsCancellationRequested)
                {
                    if(client.Client.Poll(0,SelectMode.SelectRead))
                    {
                        int length=stream.Read(buffer);if(length==0)throw new EndOfStreamException("native guest disconnected");
                        decoder.Feed(buffer.AsSpan(0,length),message=>
                        {
                            if(!verified)
                            {
                                handshake.Accept(message,liveSession,1,"mc",nonce,mcBuild);verified=true;
                                ulong started=checked((ulong)(Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks-621355968000000000)*100);
                                Send(new Envelope(2,liveSession,0,0,1,1,Control.Hello("dc",nonce,dcBuild,(ulong)Environment.ProcessId,started)));return;
                            }
                            if(message.Session!=liveSession||message.Type!=14||message.WorldEpoch!=world||message.ModeEpoch!=1||message.Sequence<=lastIncoming)throw new InvalidDataException("native status context/order");
                            ack.Observe(message.AckSequence);lastIncoming=message.Sequence;
                            var fields=Control.Parse(message.Body);Control.Fields(fields,"schema","state","geometry","tick","x","y","z","inputSeq","inputRestored");
                            if(fields["schema"]!="native-input-lab-1"||fields["geometry"]!=geometry||fields["state"] is not ("ready" or "active" or "releasing" or "restored"))throw new InvalidDataException("native state scope");
                            double Number(string key){double value=double.Parse(fields[key],CultureInfo.InvariantCulture);if(!double.IsFinite(value))throw new InvalidDataException("native pose finite");return value;}
                            var value=new NativeLabState(fields["state"],bool.Parse(fields["inputRestored"]),ulong.Parse(fields["tick"],CultureInfo.InvariantCulture),ulong.Parse(fields["inputSeq"],CultureInfo.InvariantCulture),Number("x"),Number("y"),Number("z"),Stopwatch.GetTimestamp());
                            Volatile.Write(ref nativeLabState,value);
                            File.AppendAllText(Path.Combine(nativeLabDirectory!,"native-input-states.jsonl"),JsonSerializer.Serialize(value)+"\n");
                        });
                    }
                    if(verified&&nativeLabRelease&&!sentRelease)
                    {
                        while(nativeKeys.TryDequeue(out _)){}
                        ack.Sent(++sequence);Send(new Envelope(12,liveSession,world,1,sequence,lastIncoming,Control.Encode(("reason","release"))));sentRelease=true;
                    }
                    if(verified&&!sentRelease&&nativeKeys.TryDequeue(out var sample))
                    {
                        if((Stopwatch.GetTimestamp()-sample.Captured)/(double)Stopwatch.Frequency>.1)throw new IOException("stale host input queue");
                        int pressed=sample.Held&~previousHeld,released=previousHeld&~sample.Held;if((pressed|released)!=0)eventSeq++;
                        var input=new Control.Input(++inputSeq,sample.Tick,eventSeq,sample.Held,pressed,released);ack.Sent(++sequence);
                        Send(new Envelope(13,liveSession,world,1,sequence,lastIncoming,Control.EncodeInput(input)));previousHeld=sample.Held;
                        File.AppendAllText(Path.Combine(nativeLabDirectory!,"native-host-input.jsonl"),JsonSerializer.Serialize(new{input.InputSeq,input.HostTick,input.EventSeq,input.Held,input.Pressed,input.Released,sample.Hero,captureQpc=sample.Captured,sentQpc=Stopwatch.GetTimestamp(),productionModeGranted=false})+"\n");
                    }
                    if(Volatile.Read(ref nativeLabState)?.Stage=="restored")return;
                    Thread.Sleep(5);
                }
            }
            finally{listener.Stop();}
        }
        catch(Exception ex){nativeLabFault=ex.GetType().Name+": "+ex.Message;Logger.Error("MCDN_NATIVE_INPUT_LAB_CHANNEL_ENDED {Error}",nativeLabFault);}
        finally{nativeLabEnded=true;}
    }
    private void ReleaseNativeInputLab(string reason)
    {
        if(heroInputLease==null)return;
        nativeLabRelease=true;if(nativeReleaseAt==0)nativeReleaseAt=Stopwatch.GetTimestamp();
        var state=Volatile.Read(ref nativeLabState);
        double grace=nativeLabEnded||nativeLabFault!=null?.4:1.5;
        if(state?.Stage!="restored"&&(Stopwatch.GetTimestamp()-nativeReleaseAt)/(double)Stopwatch.Frequency<grace)return;
        try{heroInputLease.Release();var restored=heroInputLease.Sample();heroInputLease=null;Logger.Information("MCDN_NATIVE_INPUT_LAB_HERO_RESTORED {Reason}; nativeReturnConfirmed={Confirmed} hero={@Hero}",reason,state?.Stage=="restored"&&state.InputRestored,restored);}
        catch(Exception ex){Logger.Error("MCDN_NATIVE_INPUT_LAB_HERO_RESTORE_PENDING {Error}",ex.Message);}
    }
    private void DisposeNativeInputHero()
    {
        nativeLabRelease=true;
        if(heroInputLease==null)return;
        try{heroInputLease.Release();heroInputLease=null;Logger.Information("MCDN_NATIVE_INPUT_LAB_HERO_FLAGS_RESTORED_BEFORE_DISPOSE");}
        catch(Exception ex){Logger.Error("MCDN_NATIVE_INPUT_LAB_DISPOSE_RESTORE_FAILED {Error}",ex.Message);}
    }
    private void TickNativeInputLab()
    {
        if(!nativeLabEnabled)return;
        try
        {
            if(!OwnForeground()){lastF7=false;ReleaseNativeInputLab("focus-lost");return;}
            bool f7=KeyDown(0x76),edge=f7&&!lastF7;lastF7=f7;
            var state=Volatile.Read(ref nativeLabState);long now=Stopwatch.GetTimestamp();
            if(heroInputLease==null)
            {
                if(!edge||nativeLabUsed||nativeLabEnded||state?.Stage!="ready"||(now-state.Received)/(double)Stopwatch.Frequency>.25||!NativeFrameFresh(lastLiveReady))return;
                var hero=ModCore.Modules.Game.Instance.HeroInstance;var game=dc.pr.Game.Class.ME;
                if(hero==null||game==null||game.paused)return;
                var lease=new HeroInputLease(hero);heroInputLease=lease;lease.Enter();nativeLabUsed=true;nativeBegan=now;
                Logger.Information("MCDN_NATIVE_INPUT_LAB_ACTIVE hero={Hero}; DC foreground / native MC input; no production MODE",lease.Uid);
            }
            else if(edge||nativeLabRelease||nativeLabEnded||nativeLabFault!=null||!heroInputLease.Valid()||dc.pr.Game.Class.ME?.paused!=false||ModCore.Modules.Game.Instance.HeroInstance?.__uid!=heroInputLease.Uid||!NativeFrameFresh(lastLiveReady)||(state!=null&&(now-state.Received)/(double)Stopwatch.Frequency>.5)||(now-nativeBegan)/(double)Stopwatch.Frequency>60)
            {ReleaseNativeInputLab("F7-or-watchdog");return;}
            if(now<nextNativeCapture)return;nextNativeCapture=now+Stopwatch.Frequency/20;
            int held=(KeyDown(0x57)?1:0)|(KeyDown(0x53)?2:0)|(KeyDown(0x41)?4:0)|(KeyDown(0x44)?8:0)|(KeyDown(0x20)?16:0)|(KeyDown(0x10)?32:0)|(KeyDown(0x11)?64:0);
            if(nativeKeys.Count>=64){ReleaseNativeInputLab("host-overflow");return;}
            nativeKeys.Enqueue(new NativeKeys(held,++nativeHostTick,now,heroInputLease.Sample()));
        }
        catch(Exception ex){nativeLabFault=ex.Message;ReleaseNativeInputLab("host-failure");}
    }
}
