using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using ModCore.Mods;
using ModCore.Events.Interfaces;
using ModCore.Events.Interfaces.Game;
using ModCore.Events.Interfaces.Game.Hero;

namespace Mcdn.DcFrameProbe;

// Native HUD presentation of recorded diagnostic frames. Never changes Hero, input or world authority.
public sealed partial class FrameProbeMod(ModInfo info):ModBase(info),IOnFrameUpdate,IOnHeroDispose,IOnGameExit
{
    private sealed record Pixels(int Index,ulong FrameId,int Width,int Height,byte[] Data,string RawHash,string PngHash,string Source,string PacketHash="",ulong StreamEpoch=0,ulong Tick=0,long ReadyQpc=0);
    private sealed record Upload(Pixels Frame,long Timestamp);
    private readonly CancellationTokenSource stop=new();
    private Pixels? pending;
    private Upload? observed;
    private int uploaded=-1;
    private volatile bool failed;
    private string? directory;
    private byte[]? playlist;
    private dc.h3d.mat.Texture? texture;
    private dc.h2d.Bitmap? bitmap;
    private int width,height;
    private int gameThread;
    private bool layoutReported;
    public override void Initialize()
    {
        gameThread=Environment.CurrentManagedThreadId;
        string? lab=Environment.GetEnvironmentVariable("MCDN_LAB_ROOT");
        if(Environment.GetEnvironmentVariable("MCDN_DC_ISOLATED_LAB")!="1"||string.IsNullOrWhiteSpace(lab))return;
        directory=Path.Combine(Path.GetFullPath(lab),"dc-frame");
        if(!File.Exists(Path.Combine(Path.GetFullPath(lab),"dc-game","MCDN_ISOLATED_DC_LAB")))throw new InvalidOperationException("marked DC lab required");
        InitializePauseLab(lab);
        if(pauseDirectory!=null)return;
        if(InitializeLive(lab)){Logger.Information("MCDN_DC_FRAME_PROBE_INITIALIZED live diagnostic only; input/Hero takeover disabled");return;}
        string manifest=Path.Combine(directory,"playlist.json"),expected=Environment.GetEnvironmentVariable("MCDN_DC_FRAME_PLAYLIST_SHA256")??"";
        long length=new FileInfo(manifest).Length;if(length is <1 or >32768)throw new InvalidDataException("playlist size");
        playlist=new byte[(int)length];using(var stream=File.OpenRead(manifest)){stream.ReadExactly(playlist);if(stream.ReadByte()!=-1)throw new InvalidDataException("playlist grew");}
        if(!Regex.IsMatch(expected,"^[a-f0-9]{64}$")||Convert.ToHexStringLower(SHA256.HashData(playlist))!=expected)
            throw new InvalidDataException("pinned recorded frame playlist required");
        _=Task.Run(Replay);
        Logger.Information("MCDN_DC_FRAME_PROBE_INITIALIZED recorded replay only; input/Hero takeover disabled");
    }
    private async Task Replay()
    {
        try
        {
            string root=directory!;using var json=JsonDocument.Parse(playlist!);var top=json.RootElement;
            if(top.GetProperty("kind").GetString()!="recorded-native-mc-world-color-diagnostic"||top.GetProperty("eligibleForControl").GetBoolean())throw new InvalidDataException("diagnostic scope required");
            string source=top.GetProperty("sourceRun").GetString()!;_ = Guid.ParseExact(source,"D");
            var entries=top.GetProperty("frames");if(entries.GetArrayLength() is <1 or >12)throw new InvalidDataException("bounded frame count");
            ulong previous=0;int index=0;
            foreach(var entry in entries.EnumerateArray())
            {
                stop.Token.ThrowIfCancellationRequested();int w=entry.GetProperty("width").GetInt32(),h=entry.GetProperty("height").GetInt32();
                if(w is <1 or >1024||h is <1 or >1024)throw new InvalidDataException("frame size");
                ulong id=ulong.Parse(entry.GetProperty("frameId").GetString()!,NumberStyles.None,CultureInfo.InvariantCulture);
                if(id<=previous)throw new InvalidDataException("frame order");previous=id;
                string name=entry.GetProperty("rawFile").GetString()!,rawHash=entry.GetProperty("rawSha256").GetString()!,pngHash=entry.GetProperty("pngSha256").GetString()!;
                if(!Regex.IsMatch(name,"^frame-[1-9][0-9]*\\.rgba$")||!Regex.IsMatch(rawHash,"^[a-f0-9]{64}$")||!Regex.IsMatch(pngHash,"^[a-f0-9]{64}$"))throw new InvalidDataException("frame name/hash");
                string path=Path.Combine(root,source,name);if(new FileInfo(path).Length!=(long)w*h*4)throw new InvalidDataException("raw length");
                byte[] bytes=new byte[w*h*4];await using(var stream=File.OpenRead(path)){await stream.ReadExactlyAsync(bytes,stop.Token);if(stream.ReadByte()!=-1)throw new InvalidDataException("raw grew");}
                if(bytes.Length!=w*h*4||Convert.ToHexStringLower(SHA256.HashData(bytes))!=rawHash)throw new InvalidDataException("raw pixels differ");
                Interlocked.Exchange(ref pending,new Pixels(index,id,w,h,bytes,rawHash,pngHash,source));
                while(Volatile.Read(ref uploaded)<index){FlushObservation();await Task.Delay(50,stop.Token);}
                FlushObservation();index++;await Task.Delay(1000,stop.Token);
            }
            FlushObservation();Logger.Information("MCDN_DC_FRAME_REPLAY_FINISHED frames={Count}; recorded native images only",index);
        }
        catch(OperationCanceledException){}
        catch(Exception ex){failed=true;Logger.Error("MCDN DC frame worker disabled: {Error}",ex.ToString());}
    }
    private void FlushObservation()
    {
        Upload? value=Interlocked.Exchange(ref observed,null);if(value==null)return;
        if(liveMode){FlushLiveObservation(value);return;}
        var report=new{kind="dc-native-texture-upload-diagnostic",recordedReplay=true,eligibleForControl=false,
            sourceRun=value.Frame.Source,frameId=value.Frame.FrameId.ToString(CultureInfo.InvariantCulture),index=value.Frame.Index,
            rawSha256=value.Frame.RawHash,pngSha256=value.Frame.PngHash,width=value.Frame.Width,height=value.Frame.Height,
            gameThreadUploadTimestamp=value.Timestamp,scope="native Texture/uploadPixels + HUD Bitmap; visible output still requires inspection"};
        string text=JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true});
        string path=Path.Combine(directory!,"observed.json");File.WriteAllText(path+".tmp",text);File.Move(path+".tmp",path,true);
        File.WriteAllText(Path.Combine(directory!,"upload-"+value.Frame.Index+".json"),text);
    }
    void IOnFrameUpdate.OnFrameUpdate(double dt)
    {
        if(directory==null)return;
        TickNativeInputLab();
        TickPauseLab();
        if(failed){Cleanup();return;}
        try
        {
            if(Environment.CurrentManagedThreadId!=gameThread)throw new InvalidOperationException("native texture game thread required");
            var game=dc.pr.Game.Class.ME;
            if(liveMode&&bitmap!=null&&(liveEnded||!Fresh(lastLiveReady)||ModCore.Modules.Game.Instance.HeroInstance==null||game?.hud?.root==null))
            {Cleanup();Logger.Information("MCDN_LIVE_COLOR_PREVIEW_CLEARED stale/end/menu; session={Session}",liveSession);}

            if(ModCore.Modules.Game.Instance.HeroInstance==null||game?.hud?.root==null)return;
            Pixels? frame=Interlocked.Exchange(ref pending,null);if(frame==null)return;
            if(liveMode&&(liveEnded||!Fresh(frame.ReadyQpc)))return;
            if(liveMode&&shownStream!=frame.StreamEpoch){Cleanup();shownStream=frame.StreamEpoch;}
            // HashLink's no-argument enums are canonical objects. A freshly allocated
            // RGBA wrapper has the same tag but fails the driver's identity check.
            var format=dc.h3d.mat.Texture.Class.nativeFormat;
            if(format is not dc.hxd.PixelFormat.RGBA)throw new InvalidDataException("native texture format must be RGBA");
            var native=dc.hxd.Pixels.Class.alloc(frame.Width,frame.Height,format);
            try
            {
                if(native.bytesPerPixel!=4||native.offset<0||native.bytes.b==IntPtr.Zero||native.bytes.length<(long)native.offset+frame.Data.Length)throw new InvalidDataException("native pixel allocation");
                Marshal.Copy(frame.Data,0,native.bytes.b+native.offset,frame.Data.Length);
                if(texture==null||width!=frame.Width||height!=frame.Height)
                {
                    Cleanup();texture=dc.h3d.mat.Texture.Class.fromPixels(native,null!);
                    var tile=dc.h2d.Tile.Class.fromTexture(texture);bitmap=new dc.h2d.Bitmap(tile,fullView?game.hud.root.getScene():game.hud.root);
                    bitmap.x=fullView?0:12;bitmap.y=fullView?0:12;bitmap.scaleX=220d/frame.Width;bitmap.scaleY=220d/frame.Width;
                    width=frame.Width;height=frame.Height;
                }
                else{int face=0,mip=0;texture.uploadPixels(native,ref face,ref mip);}
            }
            finally{native.dispose();}
            if(fullView&&bitmap!=null)
            {
                var scene=bitmap.getScene();
                int windowWidth=scene.window.get_width(),windowHeight=scene.window.get_height();
                if(windowWidth<1||windowHeight<1)throw new InvalidDataException("native window dimensions");
                // Scene dimensions can be physical pixels while its root already has a render scale.
                // Convert the actual window corners through the native inverse object transform.
                double zero=0,cornerX=windowWidth,cornerY=windowHeight;
                var start=new dc.h2d.col.Point(HaxeProxy.Runtime.Ref<double>.From(ref zero),HaxeProxy.Runtime.Ref<double>.From(ref zero));
                var end=new dc.h2d.col.Point(HaxeProxy.Runtime.Ref<double>.From(ref cornerX),HaxeProxy.Runtime.Ref<double>.From(ref cornerY));
                start=scene.globalToLocal(start);end=scene.globalToLocal(end);
                double w=end.x-start.x,h=end.y-start.y;
                if(!double.IsFinite(w)||!double.IsFinite(h)||w<=0||h<=0)throw new InvalidDataException("native view transform");
                bitmap.x=start.x;bitmap.y=start.y;bitmap.scaleX=w/frame.Width;bitmap.scaleY=h/frame.Height;
                if(!layoutReported){layoutReported=true;Logger.Information("MCDN_FULL_VIEW_LAYOUT scene={W}x{H} zoom={Z} scale={SX},{SY} window={WW}x{WH} local={LW}x{LH}",scene.width,scene.height,scene.zoom,scene.scaleX,scene.scaleY,windowWidth,windowHeight,w,h);}
            }
            if(liveMode)lastLiveReady=frame.ReadyQpc;
            Interlocked.Exchange(ref observed,new Upload(frame,System.Diagnostics.Stopwatch.GetTimestamp()));
            Volatile.Write(ref uploaded,frame.Index);
            Logger.Information("MCDN_DC_NATIVE_TEXTURE_UPLOADED index={Index} sourceFrame={Frame}; recordedReplay={Recorded}",frame.Index,frame.FrameId,!liveMode);
        }
        catch(Exception ex){failed=true;Cleanup();Logger.Error("MCDN DC native display disabled: {Error}",ex.ToString());}
    }
    private void Cleanup()
    {
        var oldBitmap=bitmap;var oldTexture=texture;bitmap=null;texture=null;width=height=0;
        try{oldBitmap?.remove();}catch(Exception ex){Logger.Warning("MCDN bitmap cleanup: {Error}",ex.Message);}
        try{oldTexture?.dispose();}catch(Exception ex){Logger.Warning("MCDN texture cleanup: {Error}",ex.Message);}
    }
    void IOnHeroDispose.OnHeroDispose(){DisposeNativeInputHero();RestorePauseLab("hero-dispose");Cleanup();}
    void IOnGameExit.OnGameExit()=>stop.Cancel(); // VM/driver lifetime may already be ending; do not invoke native objects here.
}
