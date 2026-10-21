package dev.mcdn.protocol;

import java.util.*;

/** Strict world-1 JSON commands. Numeric values remain canonical decimal strings. */
public final class WorldCommands {
    private WorldCommands() {}
    public record Command(Wire.Envelope envelope, Map<String, String> fields, byte[] chunk) {}
    public static World.Stamp stamp(Wire.Envelope m, Map<String, String> f) {
        long revision = Control.u64(f.get("revision")); String hash = f.get("digest");
        if (m.worldEpoch() == 0 || revision == 0 || !hash.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("world stamp");
        return new World.Stamp(m.session(), m.worldEpoch(), revision, hash);
    }
    public static Command parse(Wire.Envelope m) {
        var f = Control.parse(m.body()); byte[] data = null;
        switch (m.type()) {
            case 4 -> {
                Control.fields(f, "revision", "digest", "totalBytes"); stamp(m, f);
                long size = Control.u64(f.get("totalBytes"));
                if (Long.compareUnsigned(size, World.HEADER_BYTES) < 0 || Long.compareUnsigned(size, World.HEADER_BYTES + World.SHAPE_BYTES * World.MAX_SHAPES) > 0)
                    throw new IllegalArgumentException("world size");
            }
            case 5 -> {
                Control.fields(f, "revision", "index", "data");
                if (Control.u64(f.get("revision")) == 0 || Long.compareUnsigned(Control.u64(f.get("index")), 256) > 0)
                    throw new IllegalArgumentException("world chunk index");
                data = Base64.getDecoder().decode(f.get("data"));
                if (data.length == 0 || data.length > 1024 || !Base64.getEncoder().encodeToString(data).equals(f.get("data")))
                    throw new IllegalArgumentException("world base64");
            }
            case 6 -> { Control.fields(f, "revision", "digest"); stamp(m, f); }
            case 9 -> {
                Control.fields(f, "revision", "digest", "cameraEpoch", "carrierPrepared"); stamp(m, f);
                if (Control.u64(f.get("cameraEpoch")) == 0 || !Set.of("0", "1").contains(f.get("carrierPrepared")))
                    throw new IllegalArgumentException("mode prepare");
            }
            case 11 -> {
                Control.fields(f, "revision", "digest", "cameraEpoch", "frameId", "nativeTick"); stamp(m, f);
                if (Control.u64(f.get("cameraEpoch")) == 0 || Control.u64(f.get("frameId")) == 0 || Control.u64(f.get("nativeTick")) == 0)
                    throw new IllegalArgumentException("mode commit");
            }
            case 12 -> {
                Control.fields(f, "reason");
                if (!Set.of("release", "paused", "focus-lost", "world-change", "shutdown").contains(f.get("reason")))
                    throw new IllegalArgumentException("release reason");
            }
            case 13 -> Control.parseInput(m.body());
            default -> throw new IllegalArgumentException("unsupported world command");
        }
        if (m.worldEpoch() == 0 || (m.type() >= 4 && m.type() <= 6 ? m.modeEpoch() != 0 : m.modeEpoch() == 0))
            throw new IllegalArgumentException("world/mode context");
        return new Command(m, Map.copyOf(f), data);
    }
}
