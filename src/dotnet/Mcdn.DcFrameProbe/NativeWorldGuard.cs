using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using Mcdn.Protocol;

namespace Mcdn.DcFrameProbe;

public sealed partial class FrameProbeMod
{
    // Current DC solid-cell identity verification only. Unsupported cell semantics remain excluded.
    private sealed class NativeWorldGuard
    {
        private readonly int uid,x,y,width,height;
        private readonly bool[] solids;
        private readonly string? requiredAtlas;
        private nint pinnedCollision;
        public int MapUid=>uid;
        public NativeWorldGuard(JsonElement cfg,string directory)
        {
            requiredAtlas=cfg.TryGetProperty("requiredDcAtlas",out var atlas)?atlas.GetString():null;
            if(requiredAtlas!=null&&requiredAtlas!="prison")throw new InvalidDataException("unsupported DC visual atlas");
            string path=Path.GetFullPath(cfg.GetProperty("sourceWorld").GetString()!);
            string metadata=Path.GetFullPath(cfg.GetProperty("sourceMetadata").GetString()!);
            if(Path.GetDirectoryName(path)!=directory||Path.GetDirectoryName(metadata)!=directory||new FileInfo(metadata).Length>16384||new FileInfo(path).Length>World.HeaderBytes+World.MaxShapes*World.ShapeBytes)throw new InvalidDataException("private source world proof bounds");
            byte[] data=File.ReadAllBytes(path),raw=File.ReadAllBytes(metadata);
            if(Convert.ToHexStringLower(SHA256.HashData(data))!=cfg.GetProperty("sourceWorldSha256").GetString()||Convert.ToHexStringLower(SHA256.HashData(raw))!=cfg.GetProperty("sourceMetadataSha256").GetString())throw new InvalidDataException("source proof digest");
            using var json=JsonDocument.Parse(raw);var meta=json.RootElement;var world=World.Decode(data);
            if(world.Digest!=meta.GetProperty("digest").GetString()||world.Session!=Guid.Parse(meta.GetProperty("session").GetString()!)||world.Epoch!=ulong.Parse(meta.GetProperty("worldEpoch").GetString()!)||world.Revision!=ulong.Parse(meta.GetProperty("revision").GetString()!))throw new InvalidDataException("source proof identity");
            uid=meta.GetProperty("MapUid").GetInt32();x=meta.GetProperty("X").GetInt32();y=meta.GetProperty("Y").GetInt32();width=meta.GetProperty("Width").GetInt32();height=meta.GetProperty("Height").GetInt32();
            if(uid<=0||x<0||y<0||width is <1 or >64||height is <1 or >48)throw new InvalidDataException("source proof region");
            solids=new bool[checked(width*height)];
            foreach(var box in world.Boxes){ulong cell=box.Id-1;int cx=checked((int)(cell&0xffffffff)),cy=checked((int)(cell>>32));if(cx<x||cx>=x+width||cy<y||cy>=y+height)throw new InvalidDataException("source ID outside proof region");solids[(cy-y)*width+cx-x]=true;}
        }
        public bool Matches(dc.en.Hero hero,bool pin,out string reason)
        {
            var map=hero._level?.map;
            if(map==null||map.__uid!=uid||x+width>map.wid||y+height>map.hei||map.collisions.bytes==0||map.collisions.length<(long)map.wid*map.hei){reason="dc-world-identity";return false;}
            if(requiredAtlas!=null&&map.biome?.atlasName?.ToString()!=requiredAtlas){reason="dc-visual-atlas-mismatch";return false;}
            nint pointer=map.collisions.bytes;
            if(pinnedCollision!=0&&pinnedCollision!=pointer){reason="dc-world-storage-changed";return false;}
            for(int row=0;row<height;row++)for(int col=0;col<width;col++){
                int cell=Marshal.ReadInt32(pointer,checked(((y+row)*map.wid+x+col)*4));
                if((cell is 3 or 35)!=solids[row*width+col]){reason="dc-solid-revision-changed";return false;}
            }
            if(pin)pinnedCollision=pointer;reason="current-dc-solid-region-matches";return true;
        }
    }
}
