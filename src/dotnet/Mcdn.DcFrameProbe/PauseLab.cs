using System.Collections.Concurrent;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;

namespace Mcdn.DcFrameProbe;

// Isolated calibration for a reversible carrier prerequisite. Never grants MC/production ownership.
public sealed partial class FrameProbeMod
{
    private readonly ConcurrentQueue<object> pauseEvents=new();
    private volatile bool pauseBegin;
    private volatile bool pauseFinished;
    private string? pauseDirectory;
    private dc.pr.Game? pausedGame;
    private dc.en.Hero? pausedHero;
    private bool previousPaused,pauseHeld;
    private bool selectiveHero,previousFreeze,previousAlwaysUpdated;
    private long heroEligibilityCalls,otherEligibleCalls;
    private long pauseStarted;
    private int pauseFrames,pausedUid,pauseRestores;
    [DllImport("user32.dll")] private static extern nint GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(nint window,out uint pid);
    private static bool OwnForeground(){GetWindowThreadProcessId(GetForegroundWindow(),out uint pid);return pid==(uint)Environment.ProcessId;}
    private void InitializePauseLab(string lab)
    {
        string? kind=Environment.GetEnvironmentVariable("MCDN_DC_PAUSE_LAB");
        if(kind is not ("1" or "hero")||Environment.GetEnvironmentVariable("MCDN_DC_GUARD_CHECK_ONLY")=="1")return;
        selectiveHero=kind=="hero";
        if(selectiveHero)dc.Hook_Entity.canUpdate+=ObserveEligibility;
        string parent=Path.Combine(lab,"dc-frame","pause-lab");Directory.CreateDirectory(parent);
        pauseDirectory=Path.Combine(parent,Guid.NewGuid().ToString("D"));Directory.CreateDirectory(pauseDirectory);
        string run=pauseDirectory;
        new Thread(()=>
        {
            try
            {
                File.WriteAllText(Path.Combine(parent,"current.json"),JsonSerializer.Serialize(new{directory=run,pid=Environment.ProcessId,productionModeGranted=false}));
                while(!stop.IsCancellationRequested&&(!pauseFinished||!pauseEvents.IsEmpty))
                {
                    if(File.Exists(Path.Combine(run,"begin")))pauseBegin=true;
                    while(pauseEvents.TryDequeue(out var item))File.AppendAllText(Path.Combine(run,"events.jsonl"),JsonSerializer.Serialize(item)+"\n");
                    Thread.Sleep(10);
                }
            }
            catch(Exception ex){Logger.Error("MCDN_PAUSE_LAB_WORKER_FAILED {Error}",ex.Message);pauseBegin=false;}
        }){IsBackground=true,Name="MCDN-pause-lab-files"}.Start();
        Logger.Information("MCDN_PAUSE_LAB_INITIALIZED {Directory}; bounded prerequisite test, no MC ownership",run);
    }
    private bool ObserveEligibility(dc.Hook_Entity.orig_canUpdate original,dc.Entity self)
    {
        bool eligible=original(self);
        if(pauseHeld){if(self.__uid==pausedUid)heroEligibilityCalls++;else if(eligible)otherEligibleCalls++;}
        return eligible;
    }
    private void PauseSample(string kind,string reason="")
    {
        var hero=pausedHero;var game=pausedGame;
        if(pauseEvents.Count>=256)return;
        pauseEvents.Enqueue(new{kind,reason,frame=pauseFrames,qpc=Stopwatch.GetTimestamp(),paused=game?.paused,
            heroUid=hero?.__uid,x=hero==null?0:hero.cx+hero.xr,y=hero==null?0:hero.cy+hero.yr,life=hero?.life,
            foreground=OwnForeground(),previousPaused,selectiveHero,isFreeze=hero?.isFreeze,isAlwaysUpdated=hero?.isAlwaysUpdated,
            previousFreeze,previousAlwaysUpdated,heroEligibilityCalls,otherEligibleCalls,productionModeGranted=false});
    }
    private void RestorePauseLab(string reason)
    {
        if(!pauseHeld)return;
        try
        {
            if(selectiveHero)
            {
                pausedHero!.isFreeze=previousFreeze;pausedHero.isAlwaysUpdated=previousAlwaysUpdated;
                if(pausedHero.isFreeze!=previousFreeze||pausedHero.isAlwaysUpdated!=previousAlwaysUpdated)throw new InvalidOperationException("native Hero flags did not restore");
            }
            else
            {
                pausedGame!.paused=previousPaused;
                if(pausedGame.paused!=previousPaused)throw new InvalidOperationException("native pause state did not restore");
            }
            PauseSample("restored",reason);pauseHeld=false;pauseFinished=true;
            Logger.Information("MCDN_PAUSE_LAB_RESTORED reason={Reason} frames={Frames}",reason,pauseFrames);
        }
        catch(Exception ex){Logger.Error("MCDN_PAUSE_LAB_RESTORE_FAILED attempt={Attempt} {Error}",++pauseRestores,ex.Message);}
    }
    private void TickPauseLab()
    {
        if(pauseDirectory==null||pauseFinished)return;
        try
        {
            if(pauseHeld)
            {
                pauseFrames++;PauseSample("held");
                var current=ModCore.Modules.Game.Instance.HeroInstance;
                if(!OwnForeground()||current==null||current.__uid!=pausedUid||current.destroyed){RestorePauseLab("focus-or-hero-change");return;}
                if(selectiveHero){if(!pausedHero!.isFreeze||pausedHero.isAlwaysUpdated)throw new InvalidOperationException("external Hero flag owner changed");}
                else if(!pausedGame!.paused)throw new InvalidOperationException("external native pause owner changed");
                if(pauseFrames>=120||(Stopwatch.GetTimestamp()-pauseStarted)/(double)Stopwatch.Frequency>=3)RestorePauseLab("bounded-timeout");
                return;
            }
            if(!pauseBegin||!OwnForeground())return;
            var game=dc.pr.Game.Class.ME;var hero=ModCore.Modules.Game.Instance.HeroInstance;
            if(game==null||hero==null||hero.destroyed||hero.life<=0||game.paused)return;
            pausedGame=game;pausedHero=hero;pausedUid=hero.__uid;previousPaused=game.paused;pauseStarted=Stopwatch.GetTimestamp();
            previousFreeze=hero.isFreeze;previousAlwaysUpdated=hero.isAlwaysUpdated;
            if(selectiveHero&&(previousFreeze||Math.Abs(hero.dx)>.01||Math.Abs(hero.dy)>.01))return;
            PauseSample("before");pauseHeld=true;
            if(selectiveHero){hero.isAlwaysUpdated=false;hero.isFreeze=true;if(hero.canUpdate())throw new InvalidOperationException("native Hero eligibility did not close");}
            else{game.paused=true;if(!game.paused)throw new InvalidOperationException("native pause install failed");}
            PauseSample("installed");Logger.Information("MCDN_PAUSE_LAB_INSTALLED hero={Hero}",pausedUid);
        }
        catch(Exception ex){Logger.Error("MCDN_PAUSE_LAB_FAILED {Error}",ex.Message);RestorePauseLab("failure");}
    }
}
