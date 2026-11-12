import java.util.Map;
import java.util.concurrent.ConcurrentSkipListMap;
import java.util.concurrent.atomic.LongAccumulator;
import java.util.concurrent.atomic.LongAdder;

/**
 * Stats - thread-safe statistics collector. Many threads record at the same time without a single
 * lock: LongAdder (striped counters, low contention) for sums, LongAccumulator for min/max.
 */
final class Stats {
    private final LongAdder planesServed   = new LongAdder();
    private final LongAdder paxDisembarked = new LongAdder();
    private final LongAdder paxBoarded     = new LongAdder();
    private final LongAdder paxDisembarkPlanned = new LongAdder();
    private final LongAdder paxBoardPlanned     = new LongAdder();
    private final LongAdder emergencies    = new LongAdder();
    private final LongAdder totalWaitMs    = new LongAdder();
    private final LongAdder waitSamples    = new LongAdder();
    private final LongAccumulator maxWaitMs = new LongAccumulator(Math::max, Long.MIN_VALUE);
    private final LongAccumulator minWaitMs = new LongAccumulator(Math::min, Long.MAX_VALUE);
    private final ConcurrentSkipListMap<Integer, Long> waitByPlane = new ConcurrentSkipListMap<Integer, Long>();

    void recordWait(int planeNo, long ms) {
        totalWaitMs.add(ms);
        waitSamples.increment();
        maxWaitMs.accumulate(ms);
        minWaitMs.accumulate(ms);
        waitByPlane.put(planeNo, ms);
    }

    void planned(int disembark, int board) { paxDisembarkPlanned.add(disembark); paxBoardPlanned.add(board); }
    void planeServed()      { planesServed.increment(); }
    void passengerOff()     { paxDisembarked.increment(); }
    void passengerOn()      { paxBoarded.increment(); }
    void emergencyLanding() { emergencies.increment(); }

    long planesServed()   { return planesServed.sum(); }
    long paxDisembarked() { return paxDisembarked.sum(); }
    long paxBoarded()     { return paxBoarded.sum(); }
    long paxDisembarkPlanned() { return paxDisembarkPlanned.sum(); }
    long paxBoardPlanned()     { return paxBoardPlanned.sum(); }
    long emergencies()    { return emergencies.sum(); }
    long maxWaitMs()      { return waitSamples.sum() == 0 ? 0 : maxWaitMs.get(); }
    long minWaitMs()      { return waitSamples.sum() == 0 ? 0 : minWaitMs.get(); }
    double avgWaitMs()    { long n = waitSamples.sum(); return n == 0 ? 0 : (double) totalWaitMs.sum() / n; }
    Map<Integer, Long> waitByPlane() { return waitByPlane; }
}
