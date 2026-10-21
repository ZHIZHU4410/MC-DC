package dev.mcdn.protocol;

import java.util.Objects;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

/** Bounded nonblocking handoff. No game object may be passed from a network worker. */
public final class BoundedQueue<T> {
    private final ConcurrentLinkedQueue<T> queue = new ConcurrentLinkedQueue<>();
    private final AtomicInteger size = new AtomicInteger();
    private final int capacity;
    public BoundedQueue(int capacity) { if (capacity < 1) throw new IllegalArgumentException("capacity"); this.capacity = capacity; }
    public boolean offer(T item) {
        Objects.requireNonNull(item);
        if (size.incrementAndGet() > capacity) { size.decrementAndGet(); return false; }
        queue.add(item); return true;
    }
    public T poll() { T item = queue.poll(); if (item != null) size.decrementAndGet(); return item; }
    public int size() { return size.get(); }
}
