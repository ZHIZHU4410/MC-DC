using Mcdn.Protocol;
using System.Net;
using System.Net.Sockets;

try
{
if (args[0] == "pipeline-serve") { await PipelineBench.Serve(args[1]); return; }
if (args[0] == "world-vectors") { WorldBench.Vectors(args[1]); return; }
if (args[0] == "control-vectors") { ControlBench.Vectors(args[1]); return; }
if (args[0] == "control-serve") { await ControlBench.Serve(); return; }

static void Check(bool pass) { if (!pass) throw new Exception("assertion failed"); }
static void Reject(Action action)
{
    try { action(); } catch (InvalidDataException) { return; }
    throw new Exception("expected rejection");
}

if (args[0] == "serve")
{
    // Bench only: echo raw transport; deliberately has no game adapter or control authority.
    var listener = new TcpListener(IPAddress.Loopback, 0);
    listener.Start(1);
    Console.WriteLine(((IPEndPoint)listener.LocalEndpoint).Port);
    using var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(25));
    using var client = await listener.AcceptTcpClientAsync(cancel.Token);
    listener.Stop();
    client.NoDelay = true;
    using var stream = client.GetStream();
    var decoder = new StreamDecoder();
    var gate = new ReceiveGate(Guid.Parse("00112233-4455-6677-8899-aabbccddeeff"), ulong.MaxValue, 0x8000000000000000);
    int received = 0;
    byte[] buffer = new byte[127];
    int n;
    while ((n = await stream.ReadAsync(buffer, cancel.Token)) > 0)
        decoder.Feed(buffer.AsSpan(0, n), m =>
        {
            gate.Accept(m);
            var response = Wire.Encode(m);
            stream.Write(response); // Dedicated diagnostic worker, never a game thread.
            received++;
        });
    decoder.Complete();
    Check(received == 256);
    Console.WriteLine("TCP_PASS 256");
    return;
}

string root = args[1];
int vectors = 0;
foreach (var path in Directory.GetFiles(root, "*.wire"))
{
    byte[] bytes = File.ReadAllBytes(path);
    if (Path.GetFileName(path).StartsWith("bad-"))
    {
        Reject(() => Wire.Decode(bytes));
        Reject(() => { var d = new StreamDecoder(); d.Feed(bytes, _ => {}); d.Complete(); });
    }
    else
    {
        var m = Wire.Decode(bytes);
        Check(Wire.Encode(m).SequenceEqual(bytes));
        Check(m.Session.ToString() == "00112233-4455-6677-8899-aabbccddeeff");
        Check(m.WorldEpoch == ulong.MaxValue && m.ModeEpoch == 0x8000000000000000);
        // Every header boundary, plus byte-wise and coalesced input.
        for (int split = 0; split <= Math.Min(bytes.Length, 65); split++)
        {
            int count = 0; var d = new StreamDecoder();
            d.Feed(bytes.AsSpan(0, split), got => { Check(Wire.Encode(got).SequenceEqual(bytes)); count++; });
            d.Feed(bytes.AsSpan(split), got => { Check(Wire.Encode(got).SequenceEqual(bytes)); count++; });
            d.Complete(); Check(count == 1);
        }
        var joined = bytes.Concat(bytes).ToArray(); int delivered = 0;
        var coalesced = new StreamDecoder(); coalesced.Feed(joined, _ => delivered++); coalesced.Complete(); Check(delivered == 2);
    }
    vectors++;
}
foreach (var path in Directory.GetFiles(root, "*.frame"))
{
    byte[] bytes = File.ReadAllBytes(path);
    if (Path.GetFileName(path).StartsWith("bad-")) Reject(() => Frame.Decode(bytes));
    else
    {
        var f = Frame.Decode(bytes);
        Check(f.Encode().SequenceEqual(bytes));
        Check(f.FootX == 12.5 && f.FootY == -3.25 && f.FootZ == 0.125 && f.FrameId == ulong.MaxValue);
        Check(f.NativeTick == 0x8000000000000001 && f.ConsumedInputSeq == 9007199254740993);
        Check(f.Matches(f.Session, f.WorldEpoch, f.ModeEpoch, f.WorldRevision, f.CameraEpoch));
        Check(!f.Matches(f.Session, f.WorldEpoch - 1, f.ModeEpoch, f.WorldRevision, f.CameraEpoch));
        Check(!f.Matches(f.Session, f.WorldEpoch, f.ModeEpoch + 1, f.WorldRevision, f.CameraEpoch));
        Check(!f.Matches(f.Session, f.WorldEpoch, f.ModeEpoch, f.WorldRevision + 1, f.CameraEpoch));
        Check(!f.Matches(f.Session, f.WorldEpoch, f.ModeEpoch, f.WorldRevision, f.CameraEpoch + 1));
        var copy = f.Encode(); copy[112] ^= 1; Check(f.FootX == 12.5);
    }
    vectors++;
}
var sample = Wire.Decode(File.ReadAllBytes(Path.Combine(root, "good-small.wire")));
var receive = new ReceiveGate(sample.Session, sample.WorldEpoch, sample.ModeEpoch);
receive.Accept(sample);
Reject(() => receive.Accept(sample));
Reject(() => receive.Accept(sample with { Sequence = ulong.MaxValue, Session = Guid.NewGuid() }));
Reject(() => receive.Accept(sample with { Sequence = ulong.MaxValue, WorldEpoch = 1 }));
Reject(() => receive.Accept(sample with { Sequence = ulong.MaxValue, ModeEpoch = 1 }));
receive.Accept(sample with { Sequence = ulong.MaxValue });
Reject(() => receive.Accept(sample with { Sequence = 1 }));
var poisoned = new StreamDecoder();
Reject(() => poisoned.Feed(new byte[64], _ => {}));
Reject(() => poisoned.Feed(Wire.Encode(sample), _ => {}));
Console.WriteLine($"VECTORS_PASS {vectors}; fragmentation/coalescing/replay/epochs/poison PASS");
}
catch (Exception ex)
{
    // A failed bench must report a controlled exit, never trigger the Windows crash reporter.
    Console.Error.WriteLine($"BENCH_FAIL {ex.GetType().Name}: {ex.Message}");
    Environment.ExitCode = 1;
}
