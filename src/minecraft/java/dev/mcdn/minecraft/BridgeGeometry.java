package dev.mcdn.minecraft;

import dev.mcdn.protocol.World;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.minecraft.world.phys.shapes.BooleanOp;
import java.util.*;

/** Native immutable shape layer. Future Level collision hooks must route to this layer exclusively. */
public final class BridgeGeometry {
    private final Thread owner = Thread.currentThread();
    private final World.Stamp stamp;
    private final List<VoxelShape> shapes;
    public BridgeGeometry(World world) {
        stamp = world.stamp();
        var built = new ArrayList<VoxelShape>();
        for (var b : world.boxes()) built.add(Shapes.create(new AABB(b.minX(), b.minY(), b.minZ(), b.maxX(), b.maxY(), b.maxZ())));
        shapes = List.copyOf(built);
    }
    public World.Stamp applied() {
        if (Thread.currentThread() != owner) throw new IllegalStateException("geometry owning thread only");
        return stamp; // Only available after all native shapes were built successfully.
    }
    public List<VoxelShape> shapes() { return shapes; }
    /** Native block-collision callers assume every yielded shape intersects their query volume. */
    public List<VoxelShape> intersecting(AABB bounds) {
        var query=Shapes.create(bounds);
        return shapes.stream().filter(shape->Shapes.joinIsNotEmpty(query,shape,BooleanOp.AND)).toList();
    }
    public boolean isFree(AABB actualPoseBounds) {
        var body = Shapes.create(actualPoseBounds);
        for (var shape : shapes) if (Shapes.joinIsNotEmpty(body, shape, BooleanOp.AND)) return false;
        return true;
    }
}
