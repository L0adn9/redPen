/**
 * SimConfig - every tunable number of the Asia Pacific Airport simulation lives here,
 * so the behaviour can be changed (or scaled down for testing) in one place.
 *
 * Course : CT074-3-2 Concurrent Programming - Individual Assignment
 */
final class SimConfig {
    private SimConfig() { }

    // ---- Scenario sizes (taken from the case study) -------------------------------------------
    static final int TOTAL_PLANES     = 8;  // every one of these planes must land, be serviced and leave
    static final int GROUND_CAPACITY  = 3;  // max aircraft on the grounds INCLUDING the runway
    static final int GATES            = 3;  // gates in Figure 1 of the brief
    static final int MAX_PASSENGERS   = 50; // seats per aircraft

    // ---- Congestion / emergency scenario -------------------------------------------------------
    static final int EMERGENCY_PLANE_NO     = 6;  // the plane that arrives short of fuel
    static final int CONGESTION_WAITING_MIN = 2;  // planes that must already be circling
    static final int CONGESTION_GATES       = 2;  // gates that must be occupied (exactly) when the emergency plane arrives
    static final int EMERGENCY_FUEL_PERCENT = 8;  // fuel on arrival for the emergency plane
    static final int LOW_FUEL_PERCENT       = 20; // below this a circling pilot declares MAYDAY itself
    static final int FUEL_BURN_PER_TICK     = 1;  // % of fuel burnt every holding-pattern tick
    static final int HOLDING_TICK_MS        = 500;

    // ---- Timing (milliseconds, min..max) – "each step should take some time" ---------------------
    static final int[] LAND      = {900, 1200};
    static final int[] COAST     = {700, 1000};
    static final int[] DOCK      = {400, 600};
    static final int[] PASSENGER = {100, 600};   // one passenger walking through the gate door
    static final int[] SUPPLIES  = {800, 1200};
    static final int[] CLEANING  = {800, 1200};
    static final int[] REFUEL    = {1200, 1800};
    static final int[] UNDOCK    = {400, 600};
    static final int[] TAKEOFF   = {900, 1200};

    /** 1.0 = real time. Lower it (e.g. 0.1) for very quick test runs. */
    static final double TIME_SCALE = 1.0;

    /** false = passengers print only their first two and last event per group (keeps the video readable). */
    static final boolean LOG_EVERY_PASSENGER = false;

    /** Safety net: the whole simulation must finish inside this (brief: 60 s). */
    static final long WATCHDOG_STALL_MS = 15_000;

    /** Sleep for a random time in [range[0], range[1]] ms; this is how a "step takes some time". */
    static void pause(int[] range) {
        int ms = range[0] + java.util.concurrent.ThreadLocalRandom.current().nextInt(range[1] - range[0] + 1);
        pause((long) ms);
    }

    static void pause(long ms) {
        try {
            Thread.sleep((long) (ms * TIME_SCALE));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // preserve the interrupt status for the caller
        }
    }
}
