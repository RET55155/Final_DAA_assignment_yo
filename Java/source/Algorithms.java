import java.util.*;

/** Implement these algorithms. docs/guide/CONTRACTS.md defines each field and limit. */
public final class Algorithms {
    private static String str(Map<String, Object> in, String key) {
        Object o = in.get(key);
        return o == null ? "" : (String) o;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> list(Map<String, Object> in, String key) {
        Object o = in.get(key);
        return o == null ? new ArrayList<>() : (List<Object>) o;
    }

    private static Map<String, Object> result() {
        return new LinkedHashMap<>();
    }
    /** Compare two versions of a sequence while preserving the order of shared characters. Implement lcs according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> lcs(Map<String, Object> input) {
        String a = str(input, "a"), b = str(input, "b");
        int n = a.length(), m = b.length(), w = m + 1;
        int[] dp = new int[(n + 1) * w];
        for (int i = 1; i <= n; i++) {
            char ca = a.charAt(i - 1);
            int row = i * w, prev = (i - 1) * w;
            for (int j = 1; j <= m; j++) {
                if (ca == b.charAt(j - 1)) dp[row + j] = dp[prev + j - 1] + 1;
                else dp[row + j] = Math.max(dp[prev + j], dp[row + j - 1]);
            }
        }
        StringBuilder sb = new StringBuilder();
        int i = n, j = m;
        while (i > 0 && j > 0) {
            if (a.charAt(i - 1) == b.charAt(j - 1)) {
                sb.append(a.charAt(i - 1));
                i--;
                j--;
            } else if (dp[(i - 1) * w + j] >= dp[i * w + j - 1]) {
                i--;
            } else {
                j--;
            }
        }
        sb.reverse();
        Map<String, Object> r = result();
        r.put("length", dp[n * w + m]);
        r.put("sequence", sb.toString());
        return r;
    }
    /** Plan the cheapest sequence of adjacent block merges when the original order must be preserved. Implement merge according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> merge(Map<String, Object> input) {
        List<Object> sz = list(input, "sizes");
        int n = sz.size();
        long[] pre = new long[n + 1];
        for (int i = 0; i < n; i++) pre[i + 1] = pre[i] + ((Number) sz.get(i)).longValue();
        long[][] cost = new long[Math.max(n, 1)][Math.max(n, 1)];
        int[][] split = new int[Math.max(n, 1)][Math.max(n, 1)];
        for (int len = 2; len <= n; len++) {
            for (int l = 0; l + len - 1 < n; l++) {
                int r = l + len - 1;
                long best = Long.MAX_VALUE;
                int bk = l;
                for (int k = l; k < r; k++) {
                    long c = cost[l][k] + cost[k + 1][r];
                    if (c < best) {
                        best = c;
                        bk = k;
                    }
                }
                cost[l][r] = best + (pre[r + 1] - pre[l]);
                split[l][r] = bk;
            }
        }
        List<Object> plan = new ArrayList<>();
        if (n > 1) emit(0, n - 1, split, plan);
        Map<String, Object> r = result();
        r.put("cost", n > 1 ? cost[0][n - 1] : 0L);
        r.put("plan", plan);
        return r;
    }

    private static void emit(int l, int r, int[][] split, List<Object> plan) {
        if (l >= r) return;
        int k = split[l][r];
        emit(l, k, split, plan);
        emit(k + 1, r, split, plan);
        plan.add(new ArrayList<>(Arrays.asList(l, k, r)));
    }
    /** Choose a maximum-value set when neighbouring vertices are incompatible and conflicts form a tree. Implement tree according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> tree(Map<String, Object> input) {
        int n = ((Number) input.get("n")).intValue();
        List<Object> ws = list(input, "weights");
        List<Object> es = list(input, "edges");
        Map<String, Object> res = result();
        if (n <= 0) {
            res.put("weight", 0L);
            res.put("selected", new ArrayList<Integer>());
            return res;
        }
        long[] w = new long[n];
        for (int i = 0; i < n; i++) w[i] = ((Number) ws.get(i)).longValue();

        int e = es.size();
        int[] head = new int[n];
        Arrays.fill(head, -1);
        int[] nxt = new int[2 * e], to = new int[2 * e];
        int cnt = 0;
        for (Object o : es) {
            List<?> pair = (List<?>) o;
            int u = ((Number) pair.get(0)).intValue(), v = ((Number) pair.get(1)).intValue();
            to[cnt] = v; nxt[cnt] = head[u]; head[u] = cnt++;
            to[cnt] = u; nxt[cnt] = head[v]; head[v] = cnt++;
        }

        int[] order = new int[n], parent = new int[n];
        boolean[] seen = new boolean[n];
        int qh = 0, qt = 0;
        order[qt++] = 0;
        seen[0] = true;
        parent[0] = -1;
        while (qh < qt) {
            int v = order[qh++];
            for (int p = head[v]; p != -1; p = nxt[p]) {
                int u = to[p];
                if (!seen[u]) {
                    seen[u] = true;
                    parent[u] = v;
                    order[qt++] = u;
                }
            }
        }

        long[] take = new long[n], skip = new long[n];
        for (int i = 0; i < n; i++) take[i] = w[i];
        for (int i = qt - 1; i >= 0; i--) {
            int v = order[i], p = parent[v];
            if (p >= 0) {
                take[p] += skip[v];
                skip[p] += Math.max(take[v], skip[v]);
            }
        }

        boolean[] chosen = new boolean[n];
        for (int i = 0; i < qt; i++) {
            int v = order[i], p = parent[v];
            if (p >= 0 && chosen[p]) chosen[v] = false;
            else chosen[v] = take[v] > skip[v];
        }
        List<Integer> selected = new ArrayList<>();
        for (int v = 0; v < n; v++) if (chosen[v]) selected.add(v);
        res.put("weight", Math.max(take[0], skip[0]));
        res.put("selected", selected);
        return res;
    }
    /** Establish a simple exact-search baseline against which the other two searches can be checked. Implement naive according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> naive(Map<String, Object> input) {
        String t = str(input, "text"), p = str(input, "pattern");
        int n = t.length(), m = p.length();
        List<Integer> pos = new ArrayList<>();
        if (m == 0) {
            for (int i = 0; i <= n; i++) pos.add(i);
        } else {
            for (int i = 0; i + m <= n; i++) {
                int j = 0;
                while (j < m && t.charAt(i + j) == p.charAt(j)) j++;
                if (j == m) pos.add(i);
            }
        }
        Map<String, Object> r = result();
        r.put("positions", pos);
        return r;
    }

    /** Reuse information about matched prefixes to avoid restarting the search after every mismatch. Implement kmp according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> kmp(Map<String, Object> input) {
        String t = str(input, "text"), p = str(input, "pattern");
        int n = t.length(), m = p.length();
        List<Integer> pos = new ArrayList<>();
        if (m == 0) {
            for (int i = 0; i <= n; i++) pos.add(i);
        } else {
            int[] pi = new int[m];
            for (int i = 1, k = 0; i < m; i++) {
                while (k > 0 && p.charAt(i) != p.charAt(k)) k = pi[k - 1];
                if (p.charAt(i) == p.charAt(k)) k++;
                pi[i] = k;
            }
            int k = 0;
            for (int i = 0; i < n; i++) {
                while (k > 0 && (k == m || t.charAt(i) != p.charAt(k))) k = pi[k - 1];
                if (t.charAt(i) == p.charAt(k)) k++;
                if (k == m) pos.add(i - m + 1);
            }
        }
        Map<String, Object> r = result();
        r.put("positions", pos);
        return r;
    }

    private static final int RK_BASE = 31, RK_MOD = 101;

    /** Reject windows with unequal fingerprints and verify every equal-hash candidate. Implement rk according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> rk(Map<String, Object> input) {
        String t = str(input, "text"), p = str(input, "pattern");
        int n = t.length(), m = p.length();
        List<Integer> pos = new ArrayList<>();
        if (m == 0) {
            for (int i = 0; i <= n; i++) pos.add(i);
        } else if (m <= n) {
            int high = 1;
            for (int i = 1; i < m; i++) high = (high * RK_BASE) % RK_MOD;
            int hp = 0, ht = 0;
            for (int i = 0; i < m; i++) {
                hp = (hp * RK_BASE + p.charAt(i)) % RK_MOD;
                ht = (ht * RK_BASE + t.charAt(i)) % RK_MOD;
            }
            for (int i = 0; ; i++) {
                if (hp == ht) {
                    int j = 0;
                    while (j < m && t.charAt(i + j) == p.charAt(j)) j++;
                    if (j == m) pos.add(i);
                }
                if (i + m >= n) break;
                ht = ((ht - t.charAt(i) * high) % RK_MOD + RK_MOD) % RK_MOD;
                ht = (ht * RK_BASE + t.charAt(i + m)) % RK_MOD;
            }
        }
        Map<String, Object> r = result();
        r.put("positions", pos);
        return r;
    }
    /** Order the text suffixes and use adjacent common prefixes to find repeated substrings. Implement suffix according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> suffix(Map<String, Object> input) {
        String text = str(input, "text");
        int n = text.length();
        Map<String, Object> res = result();
        if (n == 0) {
            res.put("sa", new ArrayList<Integer>());
            res.put("lcp", new ArrayList<Integer>());
            res.put("repeated", "");
            return res;
        }
        char[] s = text.toCharArray();
        int[] sa = new int[n], rnk = new int[n], tmp = new int[n], sa2 = new int[n];
        int[] bucket = new int[Math.max(256, n) + 1];

        for (int i = 0; i < n; i++) bucket[s[i] & 255]++;
        for (int i = 1; i < 256; i++) bucket[i] += bucket[i - 1];
        for (int i = n - 1; i >= 0; i--) sa[--bucket[s[i] & 255]] = i;
        rnk[sa[0]] = 0;
        for (int i = 1; i < n; i++) rnk[sa[i]] = rnk[sa[i - 1]] + (s[sa[i]] != s[sa[i - 1]] ? 1 : 0);
        int classes = rnk[sa[n - 1]] + 1;

        for (int k = 1; k < n && classes < n; k <<= 1) {
            int p = 0;
            for (int i = n - k; i < n; i++) sa2[p++] = i;
            for (int i = 0; i < n; i++) if (sa[i] >= k) sa2[p++] = sa[i] - k;
            Arrays.fill(bucket, 0, classes + 1, 0);
            for (int i = 0; i < n; i++) bucket[rnk[i]]++;
            for (int i = 1; i < classes; i++) bucket[i] += bucket[i - 1];
            for (int i = n - 1; i >= 0; i--) sa[--bucket[rnk[sa2[i]]]] = sa2[i];
            tmp[sa[0]] = 0;
            for (int i = 1; i < n; i++) {
                int a = sa[i - 1], b = sa[i];
                int a2 = a + k < n ? rnk[a + k] : -1, b2 = b + k < n ? rnk[b + k] : -1;
                tmp[b] = tmp[a] + ((rnk[a] == rnk[b] && a2 == b2) ? 0 : 1);
            }
            int[] sw = rnk; rnk = tmp; tmp = sw;
            classes = rnk[sa[n - 1]] + 1;
        }

        for (int i = 0; i < n; i++) rnk[sa[i]] = i;
        int[] lcp = new int[n];
        int h = 0, bestLen = 0, bestIdx = 0;
        for (int i = 0; i < n; i++) {
            if (rnk[i] > 0) {
                int j = sa[rnk[i] - 1];
                while (i + h < n && j + h < n && s[i + h] == s[j + h]) h++;
                lcp[rnk[i]] = h;
                if (h > bestLen) {
                    bestLen = h;
                    bestIdx = rnk[i];
                }
                if (h > 0) h--;
            } else {
                h = 0;
            }
        }
        List<Integer> saL = new ArrayList<>(n), lcpL = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            saL.add(sa[i]);
            lcpL.add(lcp[i]);
        }
        res.put("sa", saL);
        res.put("lcp", lcpL);
        res.put("repeated", bestLen == 0 ? "" : text.substring(sa[bestIdx], sa[bestIdx] + bestLen));
        return res;
    }
    /** Build one dictionary automaton and count its patterns in several independent texts. Implement aho according to docs/guide/CONTRACTS.md. */
    static Map<String, Object> aho(Map<String, Object> input) {
        List<Object> pats = list(input, "patterns");
        List<Object> texts = list(input, "texts");
        final int A = 128;
        int p = pats.size(), total = 0;
        for (Object o : pats) total += ((String) o).length();
        int maxStates = total + 1;
        int[] go = new int[maxStates * A];
        Arrays.fill(go, -1);
        int states = 1;
        int[] pstate = new int[p];
        for (int i = 0; i < p; i++) {
            String pat = (String) pats.get(i);
            int v = 0;
            for (int c = 0; c < pat.length(); c++) {
                int ch = pat.charAt(c) & 127;
                int idx = v * A + ch;
                if (go[idx] == -1) go[idx] = states++;
                v = go[idx];
            }
            pstate[i] = v;
        }
        int[] fail = new int[states], order = new int[states];
        int head = 0, tail = 0;
        for (int c = 0; c < A; c++) {
            int u = go[c];
            if (u == -1) go[c] = 0;
            else {
                fail[u] = 0;
                order[tail++] = u;
            }
        }
        while (head < tail) {
            int v = order[head++];
            int fv = fail[v];
            for (int c = 0; c < A; c++) {
                int u = go[v * A + c];
                if (u == -1) go[v * A + c] = go[fv * A + c];
                else {
                    fail[u] = go[fv * A + c];
                    order[tail++] = u;
                }
            }
        }
        List<Object> rows = new ArrayList<>();
        long[] cnt = new long[states];
        for (Object o : texts) {
            String t = (String) o;
            Arrays.fill(cnt, 0L);
            int v = 0;
            for (int i = 0; i < t.length(); i++) {
                v = go[v * A + (t.charAt(i) & 127)];
                cnt[v]++;
            }
            for (int i = tail - 1; i >= 0; i--) {
                int s = order[i];
                cnt[fail[s]] += cnt[s];
            }
            List<Long> row = new ArrayList<>(p);
            for (int i = 0; i < p; i++) row.add(cnt[pstate[i]]);
            rows.add(row);
        }
        Map<String, Object> r = result();
        r.put("counts", rows);
        return r;
    }
}
