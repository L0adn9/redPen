import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * SimLog - asynchronous console logger (producer/consumer).
 *
 * Every thread calls log(); the line is stamped with the NAME OF THE CALLING THREAD and the
 * simulation clock, then handed to one dedicated writer thread through a BlockingQueue.
 * Result: lines never interleave mid-sentence, and the output proves WHICH thread did WHAT
 * (the brief forbids one thread printing on behalf of another).
 */
final class SimLog {
    private SimLog() { }

    private static final BlockingQueue<String> QUEUE = new LinkedBlockingQueue<String>();
    private static final String POISON = "<<end-of-log>>";
    private static final long START = System.nanoTime();
    private static Thread writer;

    static void start() {
        writer = new Thread(new Runnable() {
            public void run() {
                try {
                    while (true) {
                        String line = QUEUE.take();
                        if (POISON.equals(line)) {
                            return;
                        }
                        System.out.println(line);
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }, "Logger-Writer");
        writer.start();
    }

    /** Thread-safe: stamping + enqueue are done together so timestamps stay in order. */
    static void log(String message) {
        Safety.progress(); // every log line counts as "the system is alive" for the watchdog
        synchronized (QUEUE) {
            double t = (System.nanoTime() - START) / 1e9;
            QUEUE.add(String.format("[%6.2fs] %-20s: %s", t, Thread.currentThread().getName(), message));
        }
    }

    /** Flush everything and stop the writer. */
    static void stop() throws InterruptedException {
        QUEUE.add(POISON);
        writer.join();
    }
}
