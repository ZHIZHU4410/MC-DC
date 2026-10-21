using System.Buffers.Binary;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using Mcdn.Ipc;
using Mcdn.Protocol;

try
{
    int count=0;foreach(string file in Directory.GetFiles(args[0],"*.bin"))
    {
        byte[] value=File.ReadAllBytes(file);bool valid=Path.GetFileName(file).StartsWith("valid-",StringComparison.Ordinal),accepted;
        try{accepted=WorldColorFrame.Decode(value).Encode().SequenceEqual(value);}catch(InvalidDataException){accepted=false;}
        if(accepted!=valid)throw new InvalidDataException("codec vector "+file);count++;
    }
    byte[] source=File.ReadAllBytes(Path.Combine(args[0],"valid-frame.bin"));var frame=WorldColorFrame.Decode(source);
    FrameMailbox.LoadNative(args[1],args[2]);string dir=Path.Combine(args[3],Guid.NewGuid().ToString("N"));FrameMailbox.CreatePrivateDirectory(dir);
    using var box=new FrameMailbox(Path.Combine(dir,"color.map"),frame.Session,source.Length,true,true);
    try{using var wrong=new FrameMailbox(Path.Combine(dir,"color.map"),frame.Session,source.Length,false);throw new InvalidOperationException("mixed mailbox opened");}catch(System.ComponentModel.Win32Exception){}
    var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();
    Console.WriteLine(JsonSerializer.Serialize(new{file=Path.Combine(dir,"color.map"),port=((IPEndPoint)listener.LocalEndpoint).Port}));Console.Out.Flush();
    using var client=listener.AcceptTcpClient();client.ReceiveTimeout=15000;client.SendTimeout=15000;listener.Stop();
    using var stream=client.GetStream();using var input=new StreamReader(stream);using var output=new StreamWriter(stream){AutoFlush=true};
    for(int i=1;i<=20;i++)
    {
        if(input.ReadLine()!=i.ToString(System.Globalization.CultureInfo.InvariantCulture))throw new InvalidDataException("publisher sequence");
        var actual=box.ReadWorldColor()??throw new InvalidDataException("missing world-color");BinaryPrimitives.WriteUInt64LittleEndian(source.AsSpan(56),(ulong)i);
        if(!actual.Encode().SequenceEqual(source)||actual.FrameId!=(ulong)i||box.ReadWorldColor()!=null)throw new InvalidDataException("world-color transfer/duplicate");
        output.WriteLine(i);
    }
    if(input.ReadLine()!="done")throw new InvalidDataException("publisher finish");
    Console.WriteLine(JsonSerializer.Serialize(new{status="pass",vectors=count,nativeFrames=20,mixedChannelRejected=true}));
}
catch(Exception ex){Console.Error.WriteLine(ex.ToString());Environment.ExitCode=2;}
