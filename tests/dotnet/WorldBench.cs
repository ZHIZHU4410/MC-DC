using Mcdn.Protocol;

static class WorldBench
{
    public static void Vectors(string root)
    {
        int count = 0;
        foreach (var path in Directory.GetFiles(root, "*.world"))
        {
            if (Path.GetFileName(path) == "exported.world") continue;
            bool accepted = true; var bytes = File.ReadAllBytes(path);
            try
            {
                var world = World.Decode(bytes);
                if (!world.Encode().SequenceEqual(bytes) || !World.Create(world.Session, world.Epoch, world.Revision, world.Boxes).Encode().SequenceEqual(bytes))
                    throw new Exception("world byte mismatch");
            }
            catch (InvalidDataException) { accepted = false; }
            if (accepted == Path.GetFileName(path).StartsWith("bad-")) throw new Exception("world vector: " + Path.GetFileName(path));
            count++;
        }
        var b = World.FromDc(1, 0.25, 0, 2.25, 0.125, 0, 0, 0, 0, 1, -1, 1);
        if (b.MinX != 0.25 || b.MaxX != 2.25 || b.MinY != -0.125 || b.MaxY != 0) throw new Exception("DC axis/precision");
        var source = World.Decode(File.ReadAllBytes(Path.Combine(root, "good-scene.world")));
        File.WriteAllBytes(Path.Combine(root, "exported.world"), World.Create(source.Session, source.Epoch, source.Revision, source.Boxes).Encode());
        Console.WriteLine($"WORLD_CS_PASS {count}; exact export; fractional DC transform");
    }
}
