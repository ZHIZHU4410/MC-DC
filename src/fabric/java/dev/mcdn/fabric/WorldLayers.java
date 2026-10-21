package dev.mcdn.fabric;

import dev.mcdn.minecraft.BridgeGeometry;
import net.minecraft.world.level.Level;
import java.util.*;
import java.util.concurrent.atomic.*;

/** Explicit Level identity binding; unrelated worlds always use vanilla queries. */
public final class WorldLayers {
    private record Entry(Level level, BridgeGeometry layer, AtomicLong queries) {}
    private static final AtomicReference<List<Entry>> entries = new AtomicReference<>(List.of());
    private WorldLayers() {}
    public static void install(Level level, BridgeGeometry layer) {
        entries.updateAndGet(old -> { var next=new ArrayList<Entry>(); for(var e:old)if(e.level!=level)next.add(e);
            next.add(new Entry(level,layer,new AtomicLong())); return List.copyOf(next); });
    }
    public static BridgeGeometry lookup(Object world) {
        for(var e:entries.get())if(e.level==world){e.queries.incrementAndGet();return e.layer;} return null;
    }
    public static long queries(Level level) { for(var e:entries.get())if(e.level==level)return e.queries.get();return 0; }
    public static void clear() { entries.set(List.of()); }
}
