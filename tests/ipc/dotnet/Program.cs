using System.Buffers.Binary;
using System.ComponentModel;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using Mcdn.Ipc;
using Mcdn.Protocol;

// All failures exit normally: native process-death cases are triggered by the Java child only.
try { Run(args);return 0; }
catch(Exception ex){Console.Error.WriteLine("MAILBOX_DOTNET_FAIL "+ex);return 2;}

static void Require(bool condition,string reason){if(!condition)throw new InvalidOperationException(reason);}
static void Check(Frame frame,Guid session)
{
    byte[] bytes=frame.Encode();ulong id=frame.FrameId;
    Require(frame.Session==session&&bytes.Length==256+96*64*4,"identity/dimensions");
    Require(frame.NativeTick==id&&frame.FootX==(id&0xffffffffUL)+0.25,"frame/pose pairing");
    for(int j=0;j<bytes.Length-256;j++)Require(bytes[256+j]==(byte)((id>>((j&7)*8))^(ulong)(j*31)),"torn/pixel pattern");
    long ready=BinaryPrimitives.ReadInt64LittleEndian(bytes.AsSpan(216)),frequency=BinaryPrimitives.ReadInt64LittleEndian(bytes.AsSpan(224));
    Require(frequency==FrameMailbox.Frequency&&ready>0&&ready<=FrameMailbox.Qpc,"shared QPC clock");
}
static Frame Synthetic(byte[] template,Guid session)
{
    byte[] bytes=new byte[256+96*64*4];template.AsSpan(0,256).CopyTo(bytes);
    session.ToByteArray(bigEndian:true).CopyTo(bytes,16);
    void U32(int o,uint v)=>BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(o),v);
    void U64(int o,ulong v)=>BinaryPrimitives.WriteUInt64LittleEndian(bytes.AsSpan(o),v);
    U32(12,(uint)bytes.Length-256);U64(56,1);U64(64,1);U32(80,96);U32(84,64);U32(88,96*4);
    U64(112,BitConverter.DoubleToUInt64Bits(1.25));
    ulong qpc=(ulong)FrameMailbox.Qpc;for(int o=192;o<=216;o+=8)U64(o,qpc);U64(224,(ulong)FrameMailbox.Frequency);
    for(int j=0;j<bytes.Length-256;j++)bytes[256+j]=(byte)((1UL>>((j&7)*8))^(ulong)(j*31));
    uint crc=uint.MaxValue;foreach(byte value in bytes.AsSpan(256)){crc^=value;for(int bit=0;bit<8;bit++)crc=(crc>>1)^((crc&1)==0?0:0xedb88320u);}U32(236,~crc);
    return Frame.Decode(bytes);
}
static void Run(string[] args)
{
    FrameMailbox.LoadNative(args[0],args[1]);string mode=args[2];Guid session=Guid.NewGuid();
    string directory=Path.Combine(Path.GetFullPath(args[3]),session.ToString("N"));FrameMailbox.CreatePrivateDirectory(directory);
    string file=Path.Combine(directory,"frames.mcdm");const int capacity=256+96*64*4;
    using var box=new FrameMailbox(file,session,capacity,true);
    // Invalid identity/size and a second creator must not attach to a channel.
    foreach(var invalid in new[]{(Guid.NewGuid(),capacity,false),(session,capacity+4,false),(session,capacity,true)})
    {
        bool rejected=false;try{using var bad=new FrameMailbox(file,invalid.Item1,invalid.Item2,invalid.Item3);}catch(Win32Exception){rejected=true;}
        Require(rejected,"invalid channel attachment accepted");
    }
    using var listener=new TcpListener(IPAddress.Loopback,0);listener.Start(1);
    Console.WriteLine(JsonSerializer.Serialize(new{port=((IPEndPoint)listener.LocalEndpoint).Port,file,session,capacity}));Console.Out.Flush();
    using var client=listener.AcceptTcpClientAsync().WaitAsync(TimeSpan.FromSeconds(15)).GetAwaiter().GetResult();
    client.ReceiveTimeout=15000;client.SendTimeout=15000;
    using var reader=new StreamReader(client.GetStream(),Encoding.ASCII,false,1024,true);
    using var writer=new StreamWriter(client.GetStream(),Encoding.ASCII,1024,true){AutoFlush=true,NewLine="\n"};
    string Read()=>reader.ReadLine()??throw new IOException("unexpected Java EOF");
    string Command(string value){writer.WriteLine(value);return Read();}
    Require(Read()=="READY "+FrameMailbox.Frequency,"native frequency mismatch");
    long maxBusyNs=0;int seen=0;ulong previous=0;
    if(mode=="stress")
    {
        Require(box.Read()==null,"new channel not empty");
        foreach(int which in new[]{0,1})
        {
            int[] locks=which==0?[0]:[1,2,3];foreach(int item in locks)Require(box.DiagnosticLock(item),"test lock unavailable");
            try{string[] reply=Command("BUSY").Split(' ');Require(reply[0]=="BUSY_OK","busy result");maxBusyNs=Math.Max(maxBusyNs,long.Parse(reply[1]));}
            finally{foreach(int item in locks)box.DiagnosticUnlock(item);}
            Require(box.DiagnosticCapture()==null,"busy publish advanced frameId");
        }
        Require(Command("PUB 1")=="PUBLISHED","publish 1");var captured=box.DiagnosticCapture()??throw new IOException("missing frame1");
        for(int id=2;id<=4;id++)Require(Command("PUB "+id)=="PUBLISHED","publish sequence");
        Require(box.DiagnosticReadCaptured(captured)==null,"reused slot exposed a different frame");
        var latest=box.Read()??throw new IOException("missing latest4");Check(latest,session);Require(latest.FrameId==4,"latest selection");
        writer.WriteLine("STRESS");var timer=Stopwatch.StartNew();
        while(previous!=2000&&timer.Elapsed<TimeSpan.FromSeconds(15))
        {
            Frame? got=box.Read();if(got==null){Thread.Yield();continue;}Check(got,session);
            Require(got.FrameId>previous&&got.FrameId>=5&&got.FrameId<=2000,"replay/order");previous=got.FrameId;seen++;
        }
        Require(previous==2000&&seen>1,"stress did not reach latest");Require(Read()=="STRESS_DONE","stress completion");Require(box.Read()==null,"duplicate read");
        Require(Command("PUB 18446744073709551615")=="PUBLISHED","u64 publish");
        var maximum=box.Read()??throw new IOException("missing u64");Check(maximum,session);Require(maximum.FrameId==ulong.MaxValue,"unsigned sequence");Require(box.Read()==null,"u64 duplicate");
    }
    else if(mode=="reverse")
    {
        Require(box.Publish(Synthetic(File.ReadAllBytes(args[4]),session)),"reverse publish");Require(Command("READ")=="READ_OK","JNI reader");
    }
    else if(mode=="corrupt-pixels")
    {
        Require(Command("CORRUPT")=="CORRUPTED","corruption setup");bool rejected=false;
        try{box.Read();}catch(InvalidDataException){rejected=true;}
        Require(rejected,"CRC failure escaped decoder");bool reopenRejected=false;
        try{using var reopened=new FrameMailbox(file,session,capacity,false);}catch(Win32Exception){reopenRejected=true;}
        Require(reopenRejected,"decode failure did not poison shared session");
    }
    else if(mode=="abandoned-slot"||mode=="abandoned-publication")
    {
        string response=Command("ABANDON "+(mode=="abandoned-slot"?"slot":"publication"));Require(response.StartsWith("LOCKED_EXIT ",StringComparison.Ordinal),"abandonment setup");
        try{Require(reader.ReadLine()==null,"child did not close connection");}
        catch(IOException ex) when(ex.InnerException is SocketException socket&&socket.SocketErrorCode==SocketError.ConnectionReset) { /* Normal process exit can reset the diagnostic TCP socket on Windows. */ }
        bool faulted=false;var timer=Stopwatch.StartNew();
        while(!faulted&&timer.Elapsed<TimeSpan.FromSeconds(5))
        {
            try{Require(box.Read()==null,"partially written frame escaped");}catch(MailboxFaultException ex){Require(ex.Status==-2,"abandoned status");faulted=true;}
            if(!faulted)Thread.Yield();
        }
        Require(faulted,"abandoned mutex was not rejected");bool reopenRejected=false;
        try{using var reopened=new FrameMailbox(file,session,capacity,false);}catch(Win32Exception){reopenRejected=true;}
        Require(reopenRejected,"poisoned session reopened");
    }
    else throw new ArgumentException("test mode");
    if(!mode.StartsWith("abandoned",StringComparison.Ordinal))Require(Command("QUIT")=="BYE","normal exit");
    Console.WriteLine(JsonSerializer.Serialize(new{status="pass",mode,framesObserved=seen,maxBusyNs,scope="synthetic native IPC; no game capture/display"}));
}
