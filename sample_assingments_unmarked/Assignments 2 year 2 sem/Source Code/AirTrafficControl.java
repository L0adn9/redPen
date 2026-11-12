import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

/**
 * AirTrafficControl - the ATC manager thread ("ATC").
 *
 * Responsibilities
 *  - Keeps the circle (holding) queue of planes that asked to land.
 *  - Lets a plane land ONLY when fewer than GROUND_CAPACITY (3) aircraft are on the ground. This
 *    permit is the airport-wide invariant that stops collisions on runway/gates.
 *  - Gives MAYDAY (low-fuel) planes priority over everybody else in the circle.
 *  - Reserves a gate at clearance time, so a cleared plane never needs to wait for a gate
 *    (the airport has no waiting area on the ground).
 *  - At the end performs the sanity checks and prints the statistics.
 *
 * Concurrency design: ONE ReentrantLock (fair) guards all ATC state; the ATC thread sleeps on the
 * Condition 'changed' and is woken by a plane that requests landing, declares an emergency or
 * departs. Replies to pilots travel through a CompletableFuture, so the pilot thread blocks
 * without polling and the ATC thread never executes pilot code.
 */
final class AirTrafficControl implements Runnable {

    /** One plane's request to land, waiting in the circle. */
    private static final class Request {
        final Plane plane;
        final long seq;                 // arrival order (FIFO tie-breaker)
        final long requestedAtMs;
        boolean emergency;
        boolean acknowledged;           // has the ATC thread already announced the MAYDAY?
        final CompletableFuture<Integer> clearance = new CompletableFuture<Integer>();

        Request(Plane plane, long seq, boolean emergency) {
            this.plane = plane;
            this.seq = seq;
            this.emergency = emergency;
            this.requestedAtMs = System.currentTimeMillis();
        }
    }

    private final Airport airport;
    private final int totalPlanes;
    private final Watchdog watchdog;

    private final ReentrantLock lock = new ReentrantLock(true);
    private final Condition changed = lock.newCondition();

    // ---- all fields below are guarded by 'lock' ------------------------------------------------
    private final List<Request> circle = new ArrayList<Request>();
    private final boolean[] gateReserved = new boolean[SimConfig.GATES];
    private final List<Integer> departureNotices = new ArrayList<Integer>();
    private int groundCount;
    private int departed;
    private long nextSeq;
    private int lastBlockedSize = -1;

    AirTrafficControl(Airport airport, int totalPlanes, Watchdog watchdog) {
        this.airport = airport;
        this.totalPlanes = totalPlanes;
        this.watchdog = watchdog;
    }

    // ================================ called by PILOT threads ====================================

    /** A pilot joins the circle. Returns a future that completes with the assigned gate number. */
    CompletableFuture<Integer> requestLanding(Plane plane, boolean emergency) {
        lock.lock();
        try {
            Request r = new Request(plane, nextSeq++, emergency);
            circle.add(r);
            changed.signalAll();          // wake the ATC thread
            return r.clearance;
        } finally {
            lock.unlock();
        }
    }

    /** A circling pilot whose fuel dropped below the threshold escalates its request to MAYDAY. */
    void declareEmergency(Plane plane) {
        lock.lock();
        try {
            for (Request r : circle) {
                if (r.plane == plane) {
                    r.emergency = true;
                }
            }
            changed.signalAll();
        } finally {
            lock.unlock();
        }
    }

    /** The pilot leaves the gate: its gate may be given to the next plane. */
    void releaseGate(int gate) {
        lock.lock();
        try {
            gateReserved[gate - 1] = false;
        } finally {
            lock.unlock();
        }
    }

    /** The plane has finished take-off: its ground permit is returned. */
    void planeDeparted(Plane plane) {
        lock.lock();
        try {
            groundCount--;
            Safety.leave("ground");
            departed++;
            departureNotices.add(plane.number());
            changed.signalAll();          // a ground slot is free -> wake the ATC thread
        } finally {
            lock.unlock();
        }
    }

    // ================================ read-only snapshots =======================================

    int circlingCount() {
        lock.lock();
        try {
            return circle.size();
        } finally {
            lock.unlock();
        }
    }

    int groundCount() {
        lock.lock();
        try {
            return groundCount;
        } finally {
            lock.unlock();
        }
    }

    // ================================ the ATC thread ============================================

    public void run() {
        SimLog.log("Air traffic control online. Runway open. Ground capacity "
                + SimConfig.GROUND_CAPACITY + ", gates " + SimConfig.GATES + ".");
        lock.lock();
        try {
            while (true) {
                announceNotices();

                if (!circle.isEmpty() && groundCount < SimConfig.GROUND_CAPACITY) {
                    grantLanding(pickNext());
                    continue;                       // look for more work before sleeping
                }
                if (departed == totalPlanes && circle.isEmpty()) {
                    break;                          // everyone has left: end of the day
                }
                if (!circle.isEmpty() && circle.size() != lastBlockedSize) {
                    lastBlockedSize = circle.size();
                    SimLog.log("Ground is full (" + groundCount + "/" + SimConfig.GROUND_CAPACITY
                            + "). Holding in the circle: " + circleDescription());
                }
                try {
                    changed.await();                // sleep until something changes
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        } finally {
            lock.unlock();
        }
        finalReport();
        airport.truck.shutdown();
    }

    /** Called with the lock held: log MAYDAYs (once) and departures, using THIS thread's identity. */
    private void announceNotices() {
        for (Request r : circle) {
            if (r.emergency && !r.acknowledged) {
                r.acknowledged = true;
                SimLog.log("MAYDAY received from Plane " + r.plane.number()
                        + ". Plane " + r.plane.number() + " now has landing priority over all other traffic.");
            }
        }
        for (Integer no : departureNotices) {
            SimLog.log("Plane " + no + " has left our airspace. Ground " + groundCount + "/"
                    + SimConfig.GROUND_CAPACITY + ".");
        }
        departureNotices.clear();
    }

    /** Emergency first, then first-come-first-served. */
    private Request pickNext() {
        Request best = null;
        for (Request r : circle) {
            if (best == null
                    || (r.emergency && !best.emergency)
                    || (r.emergency == best.emergency && r.seq < best.seq)) {
                best = r;
            }
        }
        circle.remove(best);
        return best;
    }

    private void grantLanding(Request r) {
        groundCount++;
        Safety.enter("ground", SimConfig.GROUND_CAPACITY);
        int gate = reserveGate();
        long waited = System.currentTimeMillis() - r.requestedAtMs;
        airport.stats.recordWait(r.plane.number(), waited);
        if (r.emergency) {
            airport.stats.emergencyLanding();
        }
        lastBlockedSize = -1;
        SimLog.log("Plane " + r.plane.number() + ": cleared to land" + (r.emergency ? " [EMERGENCY PRIORITY]" : "")
                + ". Assigned Gate " + gate + ". Ground " + groundCount + "/" + SimConfig.GROUND_CAPACITY
                + ", still circling: " + circleDescription());
        r.clearance.complete(gate);                 // wakes the pilot thread
    }

    private int reserveGate() {
        for (int i = 0; i < gateReserved.length; i++) {
            if (!gateReserved[i]) {
                gateReserved[i] = true;
                return i + 1;
            }
        }
        // Cannot happen: at most 3 planes are on the ground and each holds at most one gate.
        Safety.violation("no free gate although ground count is " + groundCount);
        return 1;
    }

    private String circleDescription() {
        if (circle.isEmpty()) {
            return "none";
        }
        StringBuilder sb = new StringBuilder();
        for (Request r : circle) {
            if (sb.length() > 0) {
                sb.append(", ");
            }
            sb.append("Plane ").append(r.plane.number());
            if (r.emergency) {
                sb.append("(MAYDAY)");
            }
        }
        return sb.toString();
    }

    // ================================ sanity checks + statistics ================================

    private void finalReport() {
        Stats s = airport.stats;
        SimLog.log("All planes have left. Starting end-of-day sanity checks...");
        boolean ok = true;
        ok &= check("All gates are empty", airport.allGatesEmpty());
        ok &= check("No aircraft left on the ground (ground count = 0)", groundCount == 0);
        ok &= check("Runway is free (permit returned)", airport.runway.availablePermits() == 1);
        ok &= check("Refuel truck is idle", Safety.current("refuel-truck") == 0);
        ok &= check("Planes served = planes expected (" + s.planesServed() + "/" + totalPlanes + ")",
                s.planesServed() == totalPlanes);
        ok &= check("Passengers disembarked = expected (" + s.paxDisembarked() + "/" + s.paxDisembarkPlanned() + ")",
                s.paxDisembarked() == s.paxDisembarkPlanned());
        ok &= check("Passengers boarded = expected (" + s.paxBoarded() + "/" + s.paxBoardPlanned() + ")",
                s.paxBoarded() == s.paxBoardPlanned());
        ok &= check("Peak aircraft on ground <= " + SimConfig.GROUND_CAPACITY + " (peak " + Safety.peak("ground") + ")",
                Safety.peak("ground") <= SimConfig.GROUND_CAPACITY);
        ok &= check("Peak aircraft on runway <= 1 (peak " + Safety.peak("runway") + ")", Safety.peak("runway") <= 1);
        ok &= check("Peak refuel-truck users <= 1 (peak " + Safety.peak("refuel-truck") + ")",
                Safety.peak("refuel-truck") <= 1);
        long gatePeak = 0;
        for (int g = 1; g <= SimConfig.GATES; g++) {
            gatePeak = Math.max(gatePeak, Safety.peak("gate-" + g));
        }
        ok &= check("Peak planes at any single gate <= 1 (peak " + gatePeak + ")", gatePeak <= 1);
        ok &= check("Safety violations recorded = 0 (found " + Safety.violations() + ")", Safety.violations() == 0);
        ok &= check("Watchdog found no deadlock or stall", watchdog.isClean());
        SimLog.log("SANITY CHECK RESULT: " + (ok ? "ALL CHECKS PASSED" : "*** SOME CHECKS FAILED ***"));

        SimLog.log("================ STATISTICS ================");
        SimLog.log(String.format(Locale.ENGLISH, "Waiting time to land  - minimum: %.2fs | average: %.2fs | maximum: %.2fs",
                s.minWaitMs() / 1000.0, s.avgWaitMs() / 1000.0, s.maxWaitMs() / 1000.0));
        for (java.util.Map.Entry<Integer, Long> e : s.waitByPlane().entrySet()) {
            SimLog.log(String.format(Locale.ENGLISH, "   Plane %d waited %.2fs", e.getKey(), e.getValue() / 1000.0));
        }
        SimLog.log("Planes served        : " + s.planesServed());
        SimLog.log("Emergency landings   : " + s.emergencies());
        SimLog.log("Passengers boarded   : " + s.paxBoarded());
        SimLog.log("Passengers deplaned  : " + s.paxDisembarked());
        SimLog.log("============================================");
    }

    private boolean check(String what, boolean passed) {
        SimLog.log("  [" + (passed ? "PASS" : "FAIL") + "] " + what);
        return passed;
    }
}
