import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Semaphore;

/**
 * Passenger - one thread per passenger. Many passengers (of several planes at different gates) walk
 * through the gate doors AT THE SAME TIME: that is the "concurrent embark/disembark" requirement.
 *
 * Seat accounting: a plane owns a Semaphore with one permit per FREE seat (max 50).
 *   disembark -> release()  (a seat becomes free)
 *   embark    -> tryAcquire() (a seat is taken; failure would mean overbooking = safety violation)
 */
final class Passenger implements Runnable {
    enum Kind { DISEMBARK, EMBARK }

    private final Kind kind;
    private final Plane plane;
    private final int gate;
    private final int index;     // 1..total
    private final int total;
    private final CountDownLatch done;

    Passenger(Kind kind, Plane plane, int gate, int index, int total, CountDownLatch done) {
        this.kind = kind;
        this.plane = plane;
        this.gate = gate;
        this.index = index;
        this.total = total;
        this.done = done;
    }

    public void run() {
        SimConfig.pause(SimConfig.PASSENGER);                     // walking through the door
        Semaphore seats = plane.seats();
        if (kind == Kind.DISEMBARK) {
            seats.release();
            plane.stats().passengerOff();
        } else {
            if (!seats.tryAcquire()) {
                Safety.violation("Plane " + plane.number() + " overbooked (passenger " + index + ")");
            }
            plane.stats().passengerOn();
        }
        if (SimConfig.LOG_EVERY_PASSENGER || index <= 2 || index == total) {
            SimLog.log("I'm " + (kind == Kind.DISEMBARK ? "getting off Plane " : "boarding Plane ")
                    + plane.number() + " at Gate " + gate + " (" + index + "/" + total + ")"
                    + (index == total ? " - last one" : ""));
        }
        done.countDown();                                          // tell the pilot one more is through
    }
}
