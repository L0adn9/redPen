import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * RefuelTruck - the airport's ONLY refuelling truck, modelled as its own thread.
 *
 * Pilots put refuel jobs on a BlockingQueue; the single truck thread serves them one at a time, in
 * order. Because there is exactly one consumer, refuelling is mutually exclusive by construction,
 * and the queue is FIFO so no plane is starved. Safety.enter("refuel-truck", 1) double-checks it.
 */
final class RefuelTruck implements Runnable {

    /** A request from a pilot. */
    static final class Job {
        final Plane plane;
        final int gate;
        final CountDownLatch serviceDone;
        Job(Plane plane, int gate, CountDownLatch serviceDone) {
            this.plane = plane;
            this.gate = gate;
            this.serviceDone = serviceDone;
        }
    }

    private static final Job POISON = new Job(null, 0, null);
    private final BlockingQueue<Job> jobs = new LinkedBlockingQueue<Job>();

    /** Called by a pilot; returns how many jobs were already waiting (for the log message). */
    int submit(Job job) {
        int ahead = jobs.size();
        jobs.add(job);
        return ahead;
    }

    void shutdown() { jobs.add(POISON); }

    public void run() {
        SimLog.log("Refuel truck ready. Only one aircraft can be refuelled at a time.");
        try {
            while (true) {
                Job job = jobs.take();                    // blocks while idle
                if (job == POISON) {
                    break;
                }
                Safety.enter("refuel-truck", 1);
                SimLog.log("Refuelling Plane " + job.plane.number() + " at Gate " + job.gate
                        + " (truck in exclusive use). Waiting in line: " + jobs.size());
                SimConfig.pause(SimConfig.REFUEL);
                job.plane.fillTank();
                SimLog.log("Plane " + job.plane.number() + " refuelled to 100%. Truck is free again.");
                Safety.leave("refuel-truck");
                job.serviceDone.countDown();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
