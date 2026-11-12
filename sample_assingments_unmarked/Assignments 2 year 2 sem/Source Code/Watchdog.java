import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;

/**
 * Watchdog - daemon thread that guards against the two classic liveness failures:
 *   1. Deadlock  : asks the JVM (ThreadMXBean) whether any threads wait on each other in a cycle.
 *   2. Stall     : if no thread has logged anything for WATCHDOG_STALL_MS the system is stuck.
 * Either finding is logged and remembered so the ATC can report it in the sanity checks.
 */
final class Watchdog implements Runnable {
    private volatile boolean stopped;
    private volatile boolean problemFound;

    public void run() {
        ThreadMXBean mx = ManagementFactory.getThreadMXBean();
        long lastProgress = -1;
        long lastChange = System.currentTimeMillis();
        while (!stopped) {
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                break;
            }
            long[] deadlocked = mx.findDeadlockedThreads();
            if (deadlocked != null) {
                problemFound = true;
                SimLog.log("WATCHDOG: DEADLOCK among " + deadlocked.length + " threads!");
            }
            long p = Safety.progressCount();
            if (p != lastProgress) {
                lastProgress = p;
                lastChange = System.currentTimeMillis();
            } else if (System.currentTimeMillis() - lastChange > SimConfig.WATCHDOG_STALL_MS) {
                problemFound = true;
                lastChange = System.currentTimeMillis();
                SimLog.log("WATCHDOG: no progress for " + SimConfig.WATCHDOG_STALL_MS / 1000 + "s - possible stall!");
            }
        }
    }

    boolean isClean() { return !problemFound; }

    void stop() { stopped = true; }
}
