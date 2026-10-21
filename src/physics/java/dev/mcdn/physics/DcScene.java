package dev.mcdn.physics;

import com.google.gson.JsonObject;
import dev.mcdn.protocol.World;
import java.util.*;

/** Frozen DC solid subset. No readiness or live-world authority is granted by this diagnostic. */
final class DcScene {
    final double x,y,z,wallX;
    final String sourceDigest;
    DcScene(JsonObject plan, World world) {
        if (!plan.get("kind").getAsString().equals("archived-real-dc-solid-scene") ||
            !plan.get("fixtureSha256").getAsString().equals(world.stamp().digest()) ||
            !plan.get("sourceSession").getAsString().equals(world.stamp().session().toString()) ||
            Long.parseUnsignedLong(plan.get("sourceEpoch").getAsString())!=world.stamp().epoch() ||
            Long.parseUnsignedLong(plan.get("sourceRevision").getAsString())!=world.stamp().revision() ||
            plan.get("productionModeGranted").getAsBoolean() || plan.get("shapeCount").getAsInt()!=world.boxes().size())
            throw new IllegalArgumentException("DC scene identity");
        var spawn=plan.getAsJsonArray("spawn");x=spawn.get(0).getAsDouble();y=spawn.get(1).getAsDouble();z=spawn.get(2).getAsDouble();
        wallX=plan.get("wallX").getAsDouble();sourceDigest=plan.get("sourceDigest").getAsString();
        if(!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z)||!Double.isFinite(wallX)||y!=200.5||wallX-x<3||wallX-x>7)
            throw new IllegalArgumentException("DC corridor bounds");
        for(var b:world.boxes())if(b.minY()<170||b.maxY()>230)throw new IllegalArgumentException("scene must be above native terrain");
    }
    /** Exact adjacent runs only. Physics keeps every original box; rendering covers the identical volume. */
    static List<World.Box> displayRuns(World world) {
        var sorted=new ArrayList<>(world.boxes());
        sorted.sort(Comparator.comparingDouble(World.Box::minY).thenComparingDouble(World.Box::maxY)
            .thenComparingDouble(World.Box::minZ).thenComparingDouble(World.Box::maxZ).thenComparingDouble(World.Box::minX));
        var result=new ArrayList<World.Box>();World.Box run=null;
        for(var b:sorted){
            if(run!=null&&run.maxX()==b.minX()&&run.minY()==b.minY()&&run.maxY()==b.maxY()&&run.minZ()==b.minZ()&&run.maxZ()==b.maxZ())
                run=new World.Box(run.id(),run.minX(),run.minY(),run.minZ(),b.maxX(),run.maxY(),run.maxZ());
            else {if(run!=null)result.add(run);run=b;}
        }
        if(run!=null)result.add(run);return List.copyOf(result);
    }
    static int held(int tick){
        if(tick>=20&&tick<80||tick>=166&&tick<170)return 1;
        if(tick==90||tick==145)return 16;
        if(tick>=120&&tick<130)return 2;
        return 0;
    }
}
