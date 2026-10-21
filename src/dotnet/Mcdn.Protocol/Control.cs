using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace Mcdn.Protocol;

// control-1 deliberately restricts JSON to a flat object of unescaped ASCII strings.
// Game/world schemas are separate; this is not a general purpose JSON parser.
public static class Control
{
    public const string Layout = "mcdn-64-256-control-1";
    public const string WorldLayout = "mcdn-64-256-world-1";
    public const ulong ButtonsCapability = 1;
    public sealed record Peer(Guid Session, string Role, string Build, ulong Pid, ulong StartTime, ulong Capabilities);
    public sealed record Input(ulong InputSeq, ulong HostTick, ulong EventSeq, int Held, int Pressed, int Released);
    public sealed class Handshake
    {
        private bool used;
        public Peer Accept(Envelope m, Guid session, ushort type, string role, string nonce, string build, ulong capabilities = 1)
        {
            if (used) throw new InvalidDataException("handshake already used");
            used = true; return VerifyHello(m, session, type, role, nonce, build, capabilities);
        }
    }
    public sealed class AckWindow
    {
        private ulong sent, ack;
        public ulong Acknowledged => ack;
        public void Sent(ulong sequence)
        {
            if (sequence <= sent) throw new InvalidDataException("send sequence");
            sent = sequence;
        }
        public void Observe(ulong sequence)
        {
            if (sequence < ack || sequence > sent) throw new InvalidDataException("ack regression/future");
            ack = sequence;
        }
    }

    public static Dictionary<string, string> Parse(byte[] bytes)
    {
        if (bytes.Length > 16384 || bytes.Any(b => b >= 127)) throw new InvalidDataException("control encoding/limit");
        string text = Encoding.ASCII.GetString(bytes); int pos = 0;
        void Space() { while (pos < text.Length && " \t\r\n".Contains(text[pos])) pos++; }
        void Expect(char c) { Space(); if (pos == text.Length || text[pos++] != c) throw new InvalidDataException("control syntax"); }
        string ReadString(int max)
        {
            Expect('"'); int begin = pos;
            while (pos < text.Length && text[pos] != '"')
            {
                if (text[pos] < 32 || text[pos] == '\\' || pos - begin >= max) throw new InvalidDataException("control string");
                pos++;
            }
            if (pos == text.Length) throw new InvalidDataException("control string");
            return text[begin..pos++];
        }
        var fields = new Dictionary<string, string>(StringComparer.Ordinal);
        Expect('{'); Space();
        if (pos < text.Length && text[pos] != '}')
            while (true)
            {
                string key = ReadString(64); Expect(':'); string value = ReadString(2048);
                if (!fields.TryAdd(key, value) || fields.Count > 32) throw new InvalidDataException("duplicate/field limit");
                Space(); if (pos < text.Length && text[pos] == ',') { pos++; continue; }
                break;
            }
        Expect('}'); Space(); if (pos != text.Length) throw new InvalidDataException("control trailing data");
        return fields;
    }

    public static byte[] Encode(params (string Key, string Value)[] fields)
    {
        static string Quote(string s)
        {
            if (s.Any(c => c < 32 || c > 126 || c is '"' or '\\')) throw new InvalidDataException("control string");
            return "\"" + s + "\"";
        }
        byte[] bytes = Encoding.ASCII.GetBytes("{" + string.Join(",", fields.Select(f => Quote(f.Key) + ":" + Quote(f.Value))) + "}");
        Parse(bytes); return bytes;
    }

    public static ulong U64(string value)
    {
        if (value.Length == 0 || value.Length > 20 || (value.Length > 1 && value[0] == '0') ||
            value.Any(c => c < '0' || c > '9') || !ulong.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out ulong n))
            throw new InvalidDataException("canonical u64");
        return n;
    }
    public static void Fields(Dictionary<string, string> fields, params string[] keys)
    {
        if (fields.Count != keys.Length || keys.Any(k => !fields.ContainsKey(k))) throw new InvalidDataException("schema fields");
    }
    private static void Hex(string value)
    {
        if (value.Length != 64 || value.Any(c => !(c is >= '0' and <= '9' or >= 'a' and <= 'f')))
            throw new InvalidDataException("hex256");
    }

    public static byte[] Hello(string role, string nonce, string build, ulong pid, ulong startTime, ulong capabilities = 1) => Encode(
        ("schema", capabilities == 3 ? "world-1" : "control-1"), ("role", role), ("nonce", nonce), ("layout", capabilities == 3 ? WorldLayout : Layout), ("build", build),
        ("pid", pid.ToString(CultureInfo.InvariantCulture)), ("startTime", startTime.ToString(CultureInfo.InvariantCulture)),
        ("javaMajor", role == "mc" ? "25" : "0"), ("capabilities", capabilities.ToString(CultureInfo.InvariantCulture)));

    public static Peer VerifyHello(Envelope m, Guid session, ushort type, string role, string nonce, string build, ulong capabilities = 1)
    {
        if (capabilities is not (1 or 3)) throw new InvalidDataException("capabilities");
        if (m.Session != session || m.Type != type || m.WorldEpoch != 0 || m.ModeEpoch != 0 ||
            m.Sequence != 1 || m.AckSequence != (type == 2 ? 1UL : 0UL) ||
            (type != 1 && type != 2) || role != (type == 1 ? "mc" : "dc")) throw new InvalidDataException("hello envelope");
        var f = Parse(m.Body);
        Fields(f, "schema", "role", "nonce", "layout", "build", "pid", "startTime", "javaMajor", "capabilities");
        Hex(nonce); Hex(build); Hex(f["nonce"]); Hex(f["build"]);
        if (!CryptographicOperations.FixedTimeEquals(Convert.FromHexString(nonce), Convert.FromHexString(f["nonce"])) ||
            f["schema"] != (capabilities == 3 ? "world-1" : "control-1") || f["role"] != role ||
            f["layout"] != (capabilities == 3 ? WorldLayout : Layout) || f["build"] != build ||
            f["javaMajor"] != (role == "mc" ? "25" : "0") || U64(f["capabilities"]) != capabilities)
            throw new InvalidDataException("hello binding/auth/capability");
        ulong pid = U64(f["pid"]), start = U64(f["startTime"]);
        if (pid is 0 or > uint.MaxValue || start == 0) throw new InvalidDataException("process claim");
        return new(session, role, build, pid, start, capabilities);
    }

    public static byte[] EncodeInput(Input input) => Encode(("inputSeq", input.InputSeq.ToString(CultureInfo.InvariantCulture)),
        ("hostTick", input.HostTick.ToString(CultureInfo.InvariantCulture)), ("eventSeq", input.EventSeq.ToString(CultureInfo.InvariantCulture)),
        ("held", input.Held.ToString(CultureInfo.InvariantCulture)), ("pressed", input.Pressed.ToString(CultureInfo.InvariantCulture)),
        ("released", input.Released.ToString(CultureInfo.InvariantCulture)));

    public static Input ParseInput(byte[] bytes)
    {
        var f = Parse(bytes); Fields(f, "inputSeq", "hostTick", "eventSeq", "held", "pressed", "released");
        ulong held = U64(f["held"]), pressed = U64(f["pressed"]), released = U64(f["released"]);
        if ((held | pressed | released) > 127 || (pressed & released) != 0 || (pressed & held) != pressed || (released & held) != 0)
            throw new InvalidDataException("button masks");
        return new(U64(f["inputSeq"]), U64(f["hostTick"]), U64(f["eventSeq"]), (int)held, (int)pressed, (int)released);
    }
}
