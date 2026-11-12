import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Plane - one thread per aircraft; the thread IS the pilot. It performs the whole life-cycle:
 *
 *   request landing -> circle until cleared -> land -> coast to gate -> dock -> passengers get off
 *   -> (refuel || restock || clean) -> passengers board -> undock -> coast to runway -> take off.
 *
 * Every log line a pilot prints is about the pilot's own plane; other actors (ATC, truck, crews,
 * passengers) print their own events from their own threads.
 */
final class Plane implements Runnable {
    private final int number;
    private final Airport airport;
    private final AirTrafficControl atc;
    private final int arrivingPassengers;
    private final int departingPassengers;
    private final Semaphore seats;                // one permit per FREE seat
    private volatile int fuel;                    // percent

    Plane(int number, Airport airport, AirTrafficControl atc, int fuel, int arriving, int departing) {
        this.number = number;
        this.airport = airport;
        this.atc = atc;
        this.fuel = fuel;
        this.arrivingPassengers = arriving;
        this.departingPassengers = departing;
        this.seats = new Semaphore(SimConfig.MAX_PASSENGERS - arriving);
        airport.stats.planned(arriving, departing);
    }

    int number()      { return number; }
    Semaphore seats() { return seats; }
    Stats stats()     { return airport.stats; }
    void fillTank()   { fuel = 100; }

    private void say(String msg) { SimLog.log("Plane " + number + ": " + msg); }

    public void run() {
        long arrivedAt = System.currentTimeMillis();

        // ---- 1. ask ATC for permission to land ---------------------------------------------------
        boolean mayday = fuel < SimConfig.LOW_FUEL_PERCENT;
        if (mayday) {
            say("MAYDAY MAYDAY MAYDAY! Fuel shortage (" + fuel + "%). Requesting EMERGENCY landing!");
        } else {
            say("Requesting permission to land! (fuel " + fuel + "%, " + arrivingPassengers + " passengers on board)");
        }
        CompletableFuture<Integer> clearance = atc.requestLanding(this, mayday);

        // ---- 2. circle until cleared, burning fuel; escalate to MAYDAY if it gets low -----------
        int gate = circleUntilCleared(clearance, mayday);

        // ---- 3. land (runway is exclusive) -----------------------------------------------------
        say("Cleared! Waiting for the runway to land...");
        useRunway("Touchdown! Landing on the runway.", "Landed, vacating the runway.", SimConfig.LAND);

        // ---- 4. coast to the assigned gate and dock -------------------------------------------
        say("Coasting to Gate " + gate + ".");
        SimConfig.pause(SimConfig.COAST);
        Safety.enter("gate-" + gate, 1);
        if (!airport.gates.compareAndSet(gate - 1, null, this)) {   // atomic: only succeeds if gate is empty
            Safety.violation("Gate " + gate + " already occupied when Plane " + number + " tried to dock");
        }
        SimConfig.pause(SimConfig.DOCK);
        say("Docked at Gate " + gate + ". Doors open.");

        // ---- 5. passengers get off (concurrent threads) -----------------------------------------
        runPassengers(Passenger.Kind.DISEMBARK, arrivingPassengers, gate);
        say("All " + arrivingPassengers + " passengers have disembarked.");

        // ---- 6. refuel (exclusive truck) || restock || clean : three activities at once ----------
        CountDownLatch services = new CountDownLatch(3);
        new Thread(new GroundCrew(GroundCrew.Job.SUPPLIES, this, gate, services), "Supply-Crew-P" + number).start();
        new Thread(new GroundCrew(GroundCrew.Job.CLEANING, this, gate, services), "Cleaning-Crew-P" + number).start();
        int ahead = airport.truck.submit(new RefuelTruck.Job(this, gate, services));
        say("Requested refuel truck" + (ahead > 0 ? " (" + ahead + " plane(s) ahead of me)" : "")
                + ". Crews are working on my plane.");
        awaitUninterruptibly(services);
        say("Refuel, supplies and cleaning complete.");

        // ---- 7. passengers board (concurrent threads) ---------------------------------------------
        runPassengers(Passenger.Kind.EMBARK, departingPassengers, gate);
        say("Boarding complete: " + departingPassengers + " passengers on board.");

        // ---- 8. undock, coast to the runway, take off ------------------------------------------
        SimConfig.pause(SimConfig.UNDOCK);
        airport.gates.compareAndSet(gate - 1, this, null);          // free the gate (atomic)
        Safety.leave("gate-" + gate);
        atc.releaseGate(gate);
        say("Undocked from Gate " + gate + ". Coasting to the runway.");
        SimConfig.pause(SimConfig.COAST);
        useRunway("Cleared for departure. Taking off!", "Airborne. Goodbye Asia Pacific Airport!", SimConfig.TAKEOFF);

        // ---- 9. hand the ground permit back --------------------------------------------------
        airport.stats.planeServed();
        atc.planeDeparted(this);
        say("Total time at/around the airport: "
                + String.format("%.1f", (System.currentTimeMillis() - arrivedAt) / 1000.0) + "s.");
    }

    /** Holding pattern: block on the future in short ticks, burning fuel, and call MAYDAY when low. */
    private int circleUntilCleared(CompletableFuture<Integer> clearance, boolean alreadyMayday) {
        boolean mayday = alreadyMayday;
        while (true) {
            try {
                return clearance.get((long) (SimConfig.HOLDING_TICK_MS * SimConfig.TIME_SCALE), TimeUnit.MILLISECONDS);
            } catch (TimeoutException tick) {
                fuel -= SimConfig.FUEL_BURN_PER_TICK;
                if (!mayday && fuel < SimConfig.LOW_FUEL_PERCENT) {
                    mayday = true;
                    say("Fuel low (" + fuel + "%) while circling! Declaring MAYDAY.");
                    atc.declareEmergency(this);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("Pilot of Plane " + number + " interrupted", e);
            } catch (ExecutionException e) {
                throw new IllegalStateException(e);
            }
        }
    }

    /** Take the single runway (fair semaphore => FIFO), use it, and always give it back. */
    private void useRunway(String onEntry, String onExit, int[] duration) {
        airport.runway.acquireUninterruptibly();
        try {
            Safety.enter("runway", 1);
            say(onEntry);
            SimConfig.pause(duration);
            say(onExit);
        } finally {
            Safety.leave("runway");
            airport.runway.release();
        }
    }

    private void runPassengers(Passenger.Kind kind, int count, int gate) {
        CountDownLatch latch = new CountDownLatch(count);
        String tag = kind == Passenger.Kind.DISEMBARK ? "D" : "B";
        for (int i = 1; i <= count; i++) {
            new Thread(new Passenger(kind, this, gate, i, count, latch), "Passenger-P" + number + "-" + tag + i).start();
        }
        awaitUninterruptibly(latch);
    }

    private static void awaitUninterruptibly(CountDownLatch latch) {
        boolean interrupted = false;
        while (latch.getCount() > 0) {
            try {
                latch.await();
            } catch (InterruptedException e) {
                interrupted = true;
            }
        }
        if (interrupted) {
            Thread.currentThread().interrupt();
        }
    }
}
