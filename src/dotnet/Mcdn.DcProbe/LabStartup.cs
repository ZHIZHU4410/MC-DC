using System.Reflection;
using ModCore.Events;
using ModCore.Events.Interfaces.Game;
using Serilog;

namespace Mcdn.DcProbe;

/// <summary>Explicit DCCMShell custom startup, loaded before plugin/mod discovery.</summary>
public static class LabStartup
{
    public static void Main()
    {
        try
        {
            if(Environment.GetEnvironmentVariable("MCDN_DC_ISOLATED_LAB")!="1")throw new InvalidOperationException("isolated startup flag required");
            // These listeners exist even when the default mod loader or the probe fails to load.
            _ = new FirstEntryGuard();
            _ = new FinalEntryGate();
            Console.Error.WriteLine("MCDN_DC_BOOTSTRAP_ARMED independent pre/post game-entry checks");
            var startup=typeof(ModCore.Module).Assembly.GetType("ModCore.Startup",true)!;
            var method=startup.GetMethod("StartGame",BindingFlags.Static|BindingFlags.Public)??throw new MissingMethodException("ModCore.Startup.StartGame");
            method.Invoke(null,null);
        }
        catch(Exception ex){Refuse(ex.GetBaseException().Message);}
    }
    private sealed class FirstEntryGuard : ModCore.Module,IOnBeforeGameInit
    {
        public override int Priority => int.MinValue;
        void IOnBeforeGameInit.OnBeforeGameInit() => Before();
    }
    private static void Before()
    {
        try
        {
            string root=Environment.GetEnvironmentVariable("MCDN_LAB_ROOT")??throw new InvalidOperationException("lab root absent");
            Log.Information("MCDN_DC_LAB_GUARD_READY save={Save}; native cloud calls blocked; native local save/read/delete passed",LabSaveGuard.Install(root));
        }
        catch(Exception ex){Refuse(ex.Message);}
    }
    private sealed class FinalEntryGate : ModCore.Module,IOnBeforeGameInit
    {
        public override int Priority => int.MaxValue; // EventReceiverList traverses priorities in ascending order.
        void IOnBeforeGameInit.OnBeforeGameInit() => CompleteEntry();
    }
    private static void CompleteEntry()
    {
        if(!LabSaveGuard.IsInstalled||!ProbeMod.IsInitialized)Refuse("required probe/guard missing after mod initialization");
        Log.Information("MCDN_DC_PROBE_ENTRY_READY required probe loaded before original game entry");
        if(Environment.GetEnvironmentVariable("MCDN_DC_GUARD_CHECK_ONLY")=="1")
        {
            Console.Error.WriteLine("MCDN_DC_NATIVE_PREFLIGHT_PASS exiting before original game entry");
            Environment.Exit(0);
        }
        Log.Information("MCDN_DC_ORIGINAL_ENTRY_RELEASED guarded lab only");
    }
    private static void Refuse(string reason)
    {
        Log.Error("MCDN_DC_START_REFUSED {Reason}",reason);
        Console.Error.WriteLine("MCDN_DC_START_REFUSED "+reason);
        Environment.Exit(2);
    }
}
