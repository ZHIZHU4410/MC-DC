using Mcdn.Protocol;
using System.Net;
using System.Net.Sockets;

static class PipelineBench
{
    private static Envelope Read(NetworkStream s)
    {
        byte[] h = new byte[64]; s.ReadExactly(h); int n = Wire.ValidateHeader(h);
        byte[] p = new byte[64+n]; h.CopyTo(p, 0); s.ReadExactly(p.AsSpan(64)); return Wire.Decode(p);
    }
    public static async Task Serve(string scene)
    {
        var id = Guid.Parse(Environment.GetEnvironmentVariable("MCDN_BENCH_SESSION")!);
        string nonce = Environment.GetEnvironmentVariable("MCDN_BENCH_NONCE")!;
        var source = World.Decode(File.ReadAllBytes(scene)); var world = World.Create(id, source.Epoch, source.Revision, source.Boxes);
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start(1); Console.WriteLine(((IPEndPoint)listener.LocalEndpoint).Port);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        using var client = await listener.AcceptTcpClientAsync(timeout.Token); listener.Stop(); client.ReceiveTimeout = client.SendTimeout = 10000;
        using var stream = client.GetStream();
        var hello = Read(stream); new Control.Handshake().Accept(hello, id, 1, "mc", nonce, new string('b',64), 3);
        ulong sent = 1, remote = 1; var ack = new Control.AckWindow(); ack.Sent(1);
        void Send(ushort type, ulong mode, byte[] body)
        { var m = new Envelope(type, id, 1, mode, ++sent, remote, body); ack.Sent(sent); stream.Write(Wire.Encode(m)); }
        Envelope Receive(ushort type)
        {
            for (int budget = 0; budget < 32; budget++)
            {
                var m = Read(stream);
                if (m.Session != id || m.WorldEpoch != 1 || m.Sequence <= remote) throw new Exception("pipeline response order");
                remote = m.Sequence; ack.Observe(m.AckSequence);
                if (m.Type == type) return m;
                if (m.Type != 3) throw new Exception("pipeline unexpected response");
            }
            throw new Exception("pipeline response budget");
        }
        stream.Write(Wire.Encode(new(2, id, 0, 0, 1, 1, Control.Hello("dc", nonce, new string('c',64), 123, 456, 3))));
        Send(4, 0, WorldMessages.Begin(world)); byte[] bytes = world.Encode();
        for (int off=0, index=0; off<bytes.Length; index++)
        { int n = Math.Min(1024, bytes.Length-off); Send(5, 0, WorldMessages.Chunk(world.Revision,index,bytes.AsSpan(off,n))); off += n; }
        Send(6, 0, WorldMessages.End(world));
        WorldMessages.Applied(Receive(8), world, "client"); WorldMessages.Applied(Receive(8), world, "server");
        Send(9, 1, WorldMessages.Prepare(world, 1, true));
        var ready = Receive(10); var fields = Control.Parse(ready.Body);
        Control.Fields(fields, "revision","digest","cameraEpoch","frameId","nativeTick");
        if (ready.ModeEpoch != 1 || fields["digest"] != world.Digest || Control.U64(fields["revision"]) != world.Revision) throw new Exception("ready context");
        Send(11, 1, WorldMessages.Commit(world, 1, Control.U64(fields["frameId"]), Control.U64(fields["nativeTick"])));
        void WaitState(string state, ulong sequence)
        {
            for (int i=0; i<32; i++)
            {
                var m = Receive(3); var f = Control.Parse(m.Body); Control.Fields(f,"state");
                if (m.AckSequence >= sequence && f["state"] == state) return;
            }
            throw new Exception("pipeline state/ack");
        }
        WaitState("ACTIVE", sent);
        Send(13,1,Control.EncodeInput(new(1,1,1,1,1,0))); WaitState("ACTIVE",sent);
        Send(12,1,Control.Encode(("reason","focus-lost"))); WaitState("HERO",sent);
        Console.WriteLine("PIPELINE_CS_PASS capabilities=3; world chunks/applied; prepare/ready/commit; native-consumed ack; release");
    }
}
