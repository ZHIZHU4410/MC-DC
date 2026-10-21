using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using Mcdn.Protocol;

static class ControlBench
{
    private static void Check(bool value) { if (!value) throw new Exception("control assertion failed"); }
    public static void Vectors(string root)
    {
        using var manifest = JsonDocument.Parse(File.ReadAllBytes(Path.Combine(root, "manifest.json")));
        int count = 0;
        foreach (var item in manifest.RootElement.EnumerateArray())
        {
            bool good = item.GetProperty("valid").GetBoolean();
            string kind = item.GetProperty("kind").GetString()!;
            byte[] bytes = File.ReadAllBytes(Path.Combine(root, item.GetProperty("file").GetString()!));
            bool accepted = true;
            try
            {
                if (kind == "hello")
                {
                    var m = new Envelope(1, Guid.Parse("00112233-4455-6677-8899-aabbccddeeff"), 0, 0, 1, 0, bytes);
                    var handshake = new Control.Handshake();
                    handshake.Accept(m, m.Session, 1, "mc", new string('a', 64), new string('b', 64));
                    try { handshake.Accept(m, m.Session, 1, "mc", new string('a', 64), new string('b', 64)); }
                    catch (InvalidDataException) { count++; }
                }
                else Control.ParseInput(bytes);
            }
            catch (InvalidDataException) { accepted = false; }
            Check(accepted == good); count++;
        }
        var ack = new Control.AckWindow(); ack.Sent(1); ack.Observe(1); ack.Sent(ulong.MaxValue); ack.Observe(ulong.MaxValue);
        bool future = false, regression = false;
        try { ack.Sent(1); } catch (InvalidDataException) { regression = true; }
        var other = new Control.AckWindow(); other.Sent(1);
        try { other.Observe(2); } catch (InvalidDataException) { future = true; }
        Check(future && regression && ack.Acknowledged == ulong.MaxValue);
        Guid id = Guid.Parse("00112233-4455-6677-8899-aabbccddeeff");
        var hello = new Envelope(1, id, 0, 0, 1, 0, Control.Hello("mc", new string('a', 64), new string('b', 64), 123, 456));
        foreach (var bad in new[] { hello with { Session = Guid.NewGuid() }, hello with { WorldEpoch = 1 },
            hello with { ModeEpoch = 1 }, hello with { Sequence = 2 }, hello with { AckSequence = 1 }, hello with { Type = 2 } })
        {
            var h = new Control.Handshake(); bool refused = false, terminal = false;
            try { h.Accept(bad, id, 1, "mc", new string('a', 64), new string('b', 64)); } catch (InvalidDataException) { refused = true; }
            try { h.Accept(hello, id, 1, "mc", new string('a', 64), new string('b', 64)); } catch (InvalidDataException) { terminal = true; }
            Check(refused && terminal);
        }
        Console.WriteLine($"CONTROL_VECTORS_PASS {manifest.RootElement.GetArrayLength()}; one-shot-handshake/ack PASS");
    }

    private static Envelope Read(NetworkStream stream)
    {
        byte[] header = new byte[64]; stream.ReadExactly(header);
        int size = Wire.ValidateHeader(header); byte[] packet = new byte[64 + size]; header.CopyTo(packet, 0);
        stream.ReadExactly(packet.AsSpan(64)); return Wire.Decode(packet);
    }
    public static async Task Serve()
    {
        Guid session = Guid.Parse(Environment.GetEnvironmentVariable("MCDN_BENCH_SESSION")!);
        string nonce = Environment.GetEnvironmentVariable("MCDN_BENCH_NONCE")!;
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start(1);
        Console.WriteLine(((IPEndPoint)listener.LocalEndpoint).Port);
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        using var client = await listener.AcceptTcpClientAsync(cts.Token); listener.Stop();
        client.ReceiveTimeout = client.SendTimeout = 10000;
        using var stream = client.GetStream();
        var hello = Read(stream);
        try { new Control.Handshake().Accept(hello, session, 1, "mc", nonce, new string('b', 64)); }
        catch (InvalidDataException)
        {
            Console.WriteLine("CONTROL_TCP_AUTH_REJECTED");
            return; // Expected negative test: close cleanly, no exception escapes the process.
        }
        var ackWindow = new Control.AckWindow();
        void Send(Envelope m) { stream.Write(Wire.Encode(m)); ackWindow.Sent(m.Sequence); }
        Send(new(2, session, 0, 0, 1, 1, Control.Hello("dc", nonce, new string('c', 64), 123, 456)));
        Send(new(13, session, 1, 1, 2, 1, Control.EncodeInput(new(1, 1, 1, 16, 16, 0))));
        var peer = new ReceiveGate(session, 1, 1);
        void State(ulong seq, ulong ack, int held, string fault)
        {
            var m = Read(stream); peer.Accept(m); ackWindow.Observe(m.AckSequence);
            var f = Control.Parse(m.Body); Control.Fields(f, "held", "fault");
            Check(m.Type == 3 && m.Sequence == seq && m.AckSequence == ack && f["held"] == held.ToString() && f["fault"] == fault);
        }
        State(2, 2, 16, "none");
        Send(new(12, session, 1, 1, 3, 2, Control.Encode(("reason", "focus-lost"))));
        State(3, 3, 0, "focus-lost");
        // A new mode needs a new inbox. Bench manually supplies readiness; no game is involved.
        Send(new(13, session, 1, 2, 4, 3, Control.EncodeInput(new(1, 2, 1, 1, 1, 0))));
        var final = Read(stream); ackWindow.Observe(final.AckSequence);
        var fields = Control.Parse(final.Body); Control.Fields(fields, "held", "fault");
        Check(final.Type == 3 && final.Session == session && final.WorldEpoch == 1 && final.ModeEpoch == 2 &&
            final.Sequence == 4 && final.AckSequence == 4 && fields["held"] == "1" && fields["fault"] == "none");
        Console.WriteLine("CONTROL_TCP_HOST_PASS authenticated handshake; consumed ack; explicit release; mode change; disconnect");
        // Disposing the connection below exercises the guest's EOF release.
    }
}
