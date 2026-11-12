import java.util.Random;

/**
 * Asia Pacific Airport - concurrent simulation (CT074-3-2 Individual Assignment).
 *
 * Threads in this program
 *   Main              : only wires things together and waits - it never acts for anybody else
 *   ATC               : air traffic controller (landing queue, ground permits, gates, final report)
 *   Generator         : creates a new plane every 0, 1 or 2 seconds (also stages the congestion scenario)
 *   Plane-N           : one pilot per aircraft
 *   Passenger-PN-xx   : one thread per passenger
 *   Supply-/Cleaning-Crew-PN, Refuel-Truck : ground services
 *   Watchdog          : deadlock / stall detector
 *   Logger-Writer     : serialises console output
 *
 * Run:  javac *.java   then   java AirportSimulation [randomSeed]
 */
public class AirportSimulation {

    public static void main(String[] args) throws InterruptedException {
        long seed = args.length > 0 ? Long.parseLong(args[0]) : 2026L;   // fixed default = reproducible demo; pass another number to vary the run
        SimLog.start();
        SimLog.log("=== Asia Pacific Airport simulation starting (random seed " + seed + ") ===");

        Airport airport = new Airport();
        Watchdog watchdog = new Watchdog();
        AirTrafficControl atc = new AirTrafficControl(airport, SimConfig.TOTAL_PLANES, watchdog);

        Thread watchdogThread = new Thread(watchdog, "Watchdog");
        watchdogThread.setDaemon(true);
        Thread truckThread = new Thread(airport.truck, "Refuel-Truck");
        Thread atcThread = new Thread(atc, "ATC");
        Thread generator = new Thread(new ArrivalGenerator(airport, atc, new Random(seed)), "Generator");

        watchdogThread.start();
        truckThread.start();
        atcThread.start();
        generator.start();

        atcThread.join();        // ATC ends once every plane has left and the report is printed
        generator.join();
        truckThread.join();
        watchdog.stop();
        SimLog.log("=== Simulation finished ===");
        SimLog.stop();
    }

    /**
     * ArrivalGenerator - a new plane every 0, 1 or 2 seconds. Plane number EMERGENCY_PLANE_NO is held
     * back until the congested situation of the brief really exists (2+ planes circling, 2+ gates
     * occupied, ground full) and then arrives with a fuel shortage.
     */
    private static final class ArrivalGenerator implements Runnable {
        private final Airport airport;
        private final AirTrafficControl atc;
        private final Random rng;

        ArrivalGenerator(Airport airport, AirTrafficControl atc, Random rng) {
            this.airport = airport;
            this.atc = atc;
            this.rng = rng;
        }

        public void run() {
            for (int no = 1; no <= SimConfig.TOTAL_PLANES; no++) {
                int fuel = 60 + rng.nextInt(41);                       // 60..100 %
                if (no == SimConfig.EMERGENCY_PLANE_NO) {
                    waitForCongestion();
                    fuel = SimConfig.EMERGENCY_FUEL_PERCENT;
                }
                int arriving = 10 + rng.nextInt(SimConfig.MAX_PASSENGERS - 9);   // 10..50
                int departing = 10 + rng.nextInt(SimConfig.MAX_PASSENGERS - 9);  // 10..50
                Plane plane = new Plane(no, airport, atc, fuel, arriving, departing);
                SimLog.log("Radar: new aircraft inbound -> Plane " + no);
                new Thread(plane, "Plane-" + no).start();
                if (no < SimConfig.TOTAL_PLANES) {
                    SimConfig.pause(rng.nextInt(3) * 1000L);           // next arrival in 0, 1 or 2 s
                }
            }
        }

        private void waitForCongestion() {
            long start = System.currentTimeMillis();
            long deadline = start + 20_000;
            while (System.currentTimeMillis() < deadline) {
                // First 8 s: insist on EXACTLY the brief's picture (2 circling, 2 gates occupied, ground full).
                // After that accept 2 or more occupied gates so the scenario can never stall the run.
                boolean strict = System.currentTimeMillis() - start < 8_000;
                int gates = airport.dockedGates();
                boolean gatesOk = strict ? gates == SimConfig.CONGESTION_GATES : gates >= SimConfig.CONGESTION_GATES;
                if (atc.circlingCount() >= SimConfig.CONGESTION_WAITING_MIN
                        && gatesOk
                        && atc.groundCount() >= SimConfig.GROUND_CAPACITY) {
                    SimLog.log("SCENARIO: congestion confirmed - " + atc.circlingCount() + " planes circling, "
                            + gates + " gates occupied, ground full. A plane with a fuel shortage now arrives!");
                    return;
                }
                SimConfig.pause(50);
            }
            SimLog.log("SCENARIO: congestion not reached within 20s - releasing the emergency plane anyway.");
        }
    }
}
