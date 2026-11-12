import java.util.concurrent.CountDownLatch;

/**
 * GroundCrew - the supply crew and the cleaning crew. Each is a separate thread per plane, so
 * "refill supplies", "clean the cabin" and (via the truck) "refuel" all proceed at the same time
 * on one aircraft, and across the three gates at once.
 */
final class GroundCrew implements Runnable {
    enum Job { SUPPLIES, CLEANING }

    private final Job job;
    private final Plane plane;
    private final int gate;
    private final CountDownLatch serviceDone;

    GroundCrew(Job job, Plane plane, int gate, CountDownLatch serviceDone) {
        this.job = job;
        this.plane = plane;
        this.gate = gate;
        this.serviceDone = serviceDone;
    }

    public void run() {
        String what = job == Job.SUPPLIES ? "Restocking food and supplies on" : "Cleaning the cabin of";
        SimLog.log(what + " Plane " + plane.number() + " at Gate " + gate + "...");
        SimConfig.pause(job == Job.SUPPLIES ? SimConfig.SUPPLIES : SimConfig.CLEANING);
        SimLog.log((job == Job.SUPPLIES ? "Supplies restocked" : "Cabin cleaned") + " for Plane " + plane.number() + ".");
        serviceDone.countDown();
    }
}
