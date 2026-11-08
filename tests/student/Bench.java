import java.util.*;

/**
 * Reproducible naive / KMP / Rabin-Karp comparison (Assignment 4, "Search comparison").
 *
 * Build and run from the repository root (compilation is NOT part of the timings):
 *   javac --release 17 -encoding UTF-8 -d tests/student/build Java/source/*.java tests/student/Bench.java
 *   java -Xmx384m -cp tests/student/build Bench
 *
 * Timing scope: one call of Algorithms.naive/kmp/rk on an already parsed request map (the returned
 * result map with the positions list is built inside the call); JSON parsing/printing and process start are excluded.
 * Warm-up: 300 untimed calls per (case, algorithm) so the JIT has compiled the code. A "run" is the mean time per call
 * of 20 consecutive calls (reported in microseconds); 3 runs per cell, median of the 3 runs.
 * Before any timing the three algorithms must return identical positions, equal to an independent
 * String.indexOf-based reference that lives only in this benchmark file.
 */
public final class Bench {
    static final long SEED = 20261108L;
    static final int WARMUP = 300, INNER = 20, RUNS = 3;

    static Map<String, Object> req(String t, String p) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("text", t);
        m.put("pattern", p);
        return m;
    }

    static List<Integer> reference(String t, String p) {
        List<Integer> r = new ArrayList<>();
        for (int i = t.indexOf(p); i != -1; i = t.indexOf(p, i + 1)) r.add(i);
        return r;
    }

    @SuppressWarnings("unchecked")
    static List<Integer> pos(Map<String, Object> out) {
        return (List<Integer>) out.get("positions");
    }

    static String random(Random rnd, int n, String alpha) {
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) sb.append(alpha.charAt(rnd.nextInt(alpha.length())));
        return sb.toString();
    }

    static double timeRun(String algo, Map<String, Object> r) {
        long t0 = System.nanoTime();
        int sink = 0;
        for (int i = 0; i < INNER; i++) {
            Map<String, Object> o = algo.equals("naive") ? Algorithms.naive(r) : algo.equals("kmp") ? Algorithms.kmp(r) : Algorithms.rk(r);
            sink += pos(o).size();
        }
        long dt = System.nanoTime() - t0;
        if (sink < 0) System.out.println(sink); // keep the loop alive
        return dt / 1000.0 / INNER; // microseconds per call
    }

    public static void main(String[] args) {
        System.out.println("<!-- java.version=" + System.getProperty("java.version") + " vm=" + System.getProperty("java.vm.name")
                + " os=" + System.getProperty("os.name") + " " + System.getProperty("os.version") + " arch=" + System.getProperty("os.arch")
                + " cpus=" + Runtime.getRuntime().availableProcessors() + " maxHeapMiB=" + Runtime.getRuntime().maxMemory() / 1048576
                + " seed=" + SEED + " -->");
        int[][] sizes = {{1000, 500}, {2000, 1000}, {3000, 1500}};
        String[] cases = {"random", "repetitive-nomatch", "repetitive-allmatch", "repetitive-collision"};
        System.out.println("|Case|n|m|Seed/generator|Algorithm|Run 1 (us)|Run 2 (us)|Run 3 (us)|Median (us)|Correct outputs checked|");
        System.out.println("|---|---:|---:|---|---|---:|---:|---:|---:|---|");
        for (String cs : cases) {
            for (int[] nm : sizes) {
                int n = nm[0], m = nm[1];
                Random rnd = new Random(SEED + n);
                String text, pat, gen;
                if (cs.equals("random")) {
                    text = random(rnd, n, "abcd");
                    int off = rnd.nextInt(n - m + 1);
                    pat = text.substring(off, off + m);
                    gen = "Random(" + (SEED + n) + "), alphabet abcd, pattern = random substring of text (offset " + off + ")";
                } else if (cs.equals("repetitive-nomatch")) {
                    text = "a".repeat(n);
                    pat = "a".repeat(m - 1) + "b";
                    gen = "deterministic: text a^n, pattern a^(m-1)b (no occurrence)";
                } else if (cs.equals("repetitive-allmatch")) {
                    text = "a".repeat(n);
                    pat = "a".repeat(m);
                    gen = "deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)";
                } else {
                    // hash(a^(m-2) b B) == hash(a^m) for base 31 / mod 101: 1*31 + (66-97) = 0, so EVERY window is an equal-hash candidate
                    text = "a".repeat(n);
                    pat = "a".repeat(m - 2) + "bB";
                    gen = "deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)";
                }
                Map<String, Object> r = req(text, pat);
                List<Integer> ref = reference(text, pat);
                boolean ok = ref.equals(pos(Algorithms.naive(r))) && ref.equals(pos(Algorithms.kmp(r))) && ref.equals(pos(Algorithms.rk(r)));
                if (!ok) throw new IllegalStateException("outputs differ for " + cs + " n=" + n + " m=" + m);
                for (String algo : new String[]{"naive", "kmp", "rk"}) {
                    for (int i = 0; i < WARMUP; i++) timeRunOnce(algo, r);
                    double[] runs = new double[RUNS];
                    for (int k = 0; k < RUNS; k++) runs[k] = timeRun(algo, r);
                    double[] sorted = runs.clone();
                    Arrays.sort(sorted);
                    System.out.printf(Locale.ROOT, "|%s|%d|%d|%s|%s|%.1f|%.1f|%.1f|%.1f|yes (naive=kmp=rk=indexOf reference, %d starts)|%n",
                            cs, n, m, gen, algo, runs[0], runs[1], runs[2], sorted[1], ref.size());
                }
            }
        }
    }

    static void timeRunOnce(String algo, Map<String, Object> r) {
        if (algo.equals("naive")) Algorithms.naive(r);
        else if (algo.equals("kmp")) Algorithms.kmp(r);
        else Algorithms.rk(r);
    }
}
