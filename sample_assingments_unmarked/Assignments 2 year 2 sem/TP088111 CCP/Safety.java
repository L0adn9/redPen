import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAccumulator;

/**
 * Safety - run-time invariant checker ("black box" for the airport).
 *
 * Every critical zone (runway, ground, refuel truck, ...) reports enter()/leave() with its allowed
 * limit. The counters are lock-free atomics, so checking never slows or serialises the simulation.
 * If a limit is ever exceeded the breach is logged and counted; the ATC prints the totals in its
 * final sanity check, which turns "I think it is safe" into evidence.
 */
final class Safety {
    private Safety() { }

    private static final ConcurrentHashMap<String, AtomicInteger> CURRENT = new ConcurrentHashMap<String, AtomicInteger>();
    private static final ConcurrentHashMap<String, LongAccumulator> PEAK = new ConcurrentHashMap<String, LongAccumulator>();
    private static final AtomicInteger VIOLATIONS = new AtomicInteger();
    private static final AtomicLong PROGRESS = new AtomicLong();

    /** A thread enters a zone that may hold at most 'limit' occupants at once. */
    static void enter(String zone, int limit) {
        AtomicInteger c = CURRENT.computeIfAbsent(zone, k -> new AtomicInteger());
        LongAccumulator p = PEAK.computeIfAbsent(zone, k -> new LongAccumulator(Math::max, 0));
        int now = c.incrementAndGet();      // atomic read-modify-write: no lost updates
        p.accumulate(now);
        if (now > limit) {
            violation("zone '" + zone + "' holds " + now + " but the limit is " + limit);
        }
    }

    static void leave(String zone) {
        CURRENT.get(zone).decrementAndGet();
    }

    static void violation(String what) {
        VIOLATIONS.incrementAndGet();
        SimLog.log("*** SAFETY VIOLATION: " + what);
    }

    static int violations()           { return VIOLATIONS.get(); }
    static long peak(String zone)     { LongAccumulator p = PEAK.get(zone); return p == null ? 0 : p.get(); }
    static int current(String zone)   { AtomicInteger c = CURRENT.get(zone); return c == null ? 0 : c.get(); }
    static void progress()            { PROGRESS.incrementAndGet(); }
    static long progressCount()       { return PROGRESS.get(); }
}
