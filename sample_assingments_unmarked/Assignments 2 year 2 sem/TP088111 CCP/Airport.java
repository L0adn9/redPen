import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicReferenceArray;

/**
 * Airport - the shared physical resources every thread competes for.
 *
 *  runway : ONE runway shared by landings and take-offs -> fair binary Semaphore (FIFO, no starvation).
 *  gates  : the 3 gates; slot holds the docked Plane or null. Changed only with compareAndSet, so two
 *           planes can never occupy the same gate even if a bug tried to put them there.
 *  truck  : the single refuelling truck (a thread of its own).
 */
final class Airport {
    final Semaphore runway = new Semaphore(1, true);
    final AtomicReferenceArray<Plane> gates = new AtomicReferenceArray<Plane>(SimConfig.GATES);
    final RefuelTruck truck = new RefuelTruck();
    final Stats stats = new Stats();

    int dockedGates() {
        int n = 0;
        for (int i = 0; i < gates.length(); i++) {
            if (gates.get(i) != null) {
                n++;
            }
        }
        return n;
    }

    boolean allGatesEmpty() { return dockedGates() == 0; }
}
