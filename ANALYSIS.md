# Assignment 4 — analysis (complete in English)

## Environment and commands

- **Language:** Java (`submission.json`: `"language": "Java"`). Source: `Java/source/Algorithms.java`; `Main.java` and `Json.java` are the supplied transport and were not changed.
- **Compilation target:** `javac --release 17` (as in the official launcher). **Runtime used for all runs below:** Java HotSpot(TM) 64-Bit Server VM (build 25.0.1+8-LTS-27, java version "25.0.1"). Python version: Python 3.15.0a3.
- **Machine used for all measurements and test runs in this file:** Windows 11 Pro (10.0.26200), 12th Gen Intel(R) Core(TM) i7-12700H (14 cores, 20 logical threads), 16 GB RAM, JVM heap limit 384 MiB (`-Xmx384m`, the launcher default).
- **Commands** (repository root):

```
python tools/run.py --language Java --setup          # compile + startup check
python tools/run.py --language Java --check          # 44 public cases + repeated mixed batch
python tests/student/oracle_test.py                  # own tests: hand-written, random vs. oracles, large domain tests
python tests/student/oracle_test.py --table          # prints the hand-written table used below
javac --release 17 -encoding UTF-8 -d tests/student/build Java/source/*.java tests/student/Bench.java
java -Xmx384m -cp tests/student/build Bench          # naive / KMP / RK comparison
```

- **Results actually obtained:** `--setup` passed; `--check` passed all 44 public cases and the state-reset batch (two complete batches in one process); `oracle_test.py` ended with `RESULT: ALL PASSED` (details in "Own tests").
- The final commit URL (with the full 40-character SHA) is recorded in Moodle.

## Algorithm explanations

General conventions: all positions/indices are zero-based; costs, weights and counts are `long` (signed 64-bit); every method keeps all its arrays local, so nothing survives from one request to the next (the repeated mixed batch in the public checks and in my own tests confirms this). No built-in search (`indexOf`, `contains`, regex) is used by the algorithms.

### 1. `lcs` — prefix DP

- **State:** `dp[i][j]` = length of a longest common subsequence of the prefixes `a[0..i)` and `b[0..j)`; `i` in `0..|a|`, `j` in `0..|b|` (the index is a prefix *length*, so row/column 0 is the empty prefix). Stored as one flat `int[(|a|+1)(|b|+1)]`.
- **Base cases:** `dp[0][j] = dp[i][0] = 0`. If either input is empty the table has a zero row/column only, the reconstruction loop does not run, and the result is `length=0, sequence=""`.
- **Transition:** if `a[i-1] == b[j-1]` then `dp[i][j] = dp[i-1][j-1] + 1`, else `dp[i][j] = max(dp[i-1][j], dp[i][j-1])`.
- **Order:** rows by increasing `i`, columns by increasing `j`; every cell only reads cells above, left and diagonal, which are already final.
- **Correctness:** if the last characters are equal, some LCS can end with that character (exchange argument: any common subsequence not using both last characters can be extended or re-aligned to use them), so dropping both characters loses exactly 1. If they differ, an LCS cannot use both last characters, so it lies entirely in `a[0..i-1)` vs `b[0..j)` or in `a[0..i)` vs `b[0..j-1)`, hence the max.
- **Reconstruction / ties:** start at `(|a|,|b|)`. Equal characters: emit the character and move diagonally. Otherwise move to the neighbour with the larger `dp` (ties: move up, i.e. decrease `i`). Characters are collected backwards and reversed. Different tie rules give different but equally long sequences; any optimal sequence is valid.
- **Complexity:** time `O((|a|+1)(|b|+1))`, memory `O((|a|+1)(|b|+1))` ints (at most about 1.0 M ints ≈ 4 MB for the published limit `|a|·|b| ≤ 1 000 000`); the output is `O(|a|+|b|)`.
- **Boundary test:** `a="tea_time", b="team"` must give length 4 (`team` is a subsequence, not a substring); a longest-common-*substring* implementation would return 3.

### 2. `merge` — interval DP (ordered adjacent blocks)

- **State:** `cost[l][r]` = minimum total cost of merging the original blocks `l..r` (inclusive) into one block; `pre` holds prefix sums so `sum(l..r) = pre[r+1]-pre[l]` in O(1). `split[l][r]` remembers the best last split.
- **Base cases:** `cost[l][l] = 0` (a single block needs no merge). For `n ≤ 1` the answer is `cost=0, plan=[]`.
- **Transition:** `cost[l][r] = min_{l ≤ k < r} (cost[l][k] + cost[k+1][r]) + sum(l..r)`. The last merge joins `[l,k]` and `[k+1,r]` and pays their combined size, which is the whole interval sum regardless of `k`; the two sub-intervals are independent optimal sub-problems (the cost of a merge depends only on the sizes of the two merged blocks).
- **Order:** by increasing interval length `2..n`, so both children (shorter intervals) are final.
- **Plan reconstruction:** `emit(l,r)` recurses into `(l,k)` and `(k+1,r)` first and only then appends `[l,k,r]`. Children before parent is exactly a valid chronological order, because a block `[l,r]` exists only after its two halves have been merged. The plan has `n-1` steps. Recursion depth ≤ n-1 ≤ 199.
- **Ties:** the first minimal `k` wins (strict `<`); any optimal plan is accepted.
- **Complexity:** `O(n³)` time, `O(n²)` memory (`long[n][n]` + `int[n][n]`); `O(1)` for `n=0`. Largest value: ≤ 2·10¹¹ (sum) × depth ≤ 199, i.e. < 4·10¹³, safe in `long`.
- **Boundary tests:** `[10,1,1,10]` → 36 (a greedy “merge the two smallest *blocks*” or any non-adjacent merge gives a different number); 200 × 10⁹ → 1 544 000 000 000 (does not fit in 32 bits; equals 10⁹·(56·7+144·8)).

### 3. `tree` — maximum-weight independent set (take/skip)

- **State:** `take[v]` = best weight inside the subtree of `v` if `v` is selected; `skip[v]` = best weight inside the subtree of `v` if `v` is not selected.
- **Base/update:** initially `take[v] = w[v]`, `skip[v] = 0`. When a child `c` is finished, its parent `p` receives `take[p] += skip[c]` and `skip[p] += max(take[c], skip[c])`. A leaf therefore has `take = w`, `skip = 0`. The empty set is allowed, so the answer is `max(take[root], skip[root])` and is never negative; `n = 0` returns `weight=0, selected=[]`.
- **Order:** the tree is traversed by an iterative BFS from vertex 0 (parent array + BFS order) and processed in **reverse BFS order**, so all children are finished before their parent. No recursion, hence a chain of 100 000 vertices is safe. The root choice does not change the optimum (verified against an oracle that roots the tree at the last vertex).
- **Correctness:** if `v` is selected none of its children may be, so each child contributes `skip[c]`; if `v` is skipped each child is free, so it contributes the better of its two states. Subtrees of different children are disjoint and independent.
- **Reconstruction:** top-down in BFS order: if the parent is selected the vertex is forced to “skip”; otherwise it is selected iff `take[v] > skip[v]` (ties → skip, so zero-weight vertices never create conflicts). The sum of selected weights equals the reported weight by construction; no vertex repeats; selected IDs are listed in increasing order.
- **Complexity:** `O(n)` time and memory (adjacency stored in `head/next/to` arrays, plus six `O(n)` arrays); `O(1)` for `n = 0`. The maximum total is 10¹⁴ in absolute value → `long`.
- **Boundary tests:** all-negative weights → `0` and `[]`; star with negative centre (`[-5,3,3,3,3]`) → 12 with the four leaves; a 100 000-vertex chain (checks stack safety and `long` sums).

### 4a. `naive` — baseline search

- **Invariant:** for start `i`, the first `j` pattern characters have matched `text[i..i+j)`.
- **Loop:** for every start `i = 0 .. n-m` compare left to right until mismatch or `j = m`. The last valid start is `n-m`; a pattern longer than the text gives `[]` (the loop does not execute). Overlapping occurrences are found automatically because every start is tried. **Empty pattern:** returns all boundaries `0..n` (`n+1` starts) before any indexing.
- **Complexity:** `O(n·m + n + 1)` time including output, `O(1)` auxiliary memory, `O(z+1)` output memory.
- **Boundary test:** `text="aaaaa", pattern="aaa"` → `[0,1,2]` (overlaps); `text="", pattern=""` → `[0]`.

### 4b. `kmp` — prefix function

- **Definition:** `pi[i]` = length of the longest *proper* prefix of `p[0..i]` that is also a suffix of `p[0..i]`. It is built left to right with the same fallback loop (`k = pi[k-1]` while mismatching).
- **Search state:** `k` = length of the longest pattern prefix that is a suffix of the text read so far. On a mismatch `k` falls back to `pi[k-1]` (the next-longest border) and the text pointer never moves backwards. After a full match (`k == m`) the occurrence start `i-m+1` is recorded and `k` also falls back to `pi[m-1]`, which keeps overlapping occurrences (`abababa` / `aba` → 0, 2, 4).
- **Empty pattern:** returns `0..n` before `pi` is built (no `pi[-1]`).
- **Complexity:** `O(n + m + z + 1)` time (each step either advances the text pointer or strictly decreases `k`, amortised), `O(m + 1)` auxiliary memory, `O(z + 1)` output.
- **Boundary tests:** `text="aaaaaaaa", pattern="aaaa"` → 0..4 (no fallback after a match would give 0 and 4 only); `aabaabaaa` / `aabaaa` → `[3]` (fallback must go to `pi[k-1]`, not to 0).

### 4c. `rk` — Rabin–Karp, base 31, modulus 101

- **Hash:** `H(s) = Σ s[i]·31^(m-1-i) mod 101` with ASCII codes; the leftmost character has the highest power. `high = 31^(m-1) mod 101`.
- **Rolling update:** `H(i+1) = ((H(i) − t[i]·high) mod 101 · 31 + t[i+m]) mod 101`. The subtraction can be negative, so the remainder is normalised with `((x % 101) + 101) % 101`.
- **Verification:** equal hashes are only *candidates*; every candidate window is compared character by character before its start is reported (`ab` and `dj` both hash to 75, only `ab` is a match). Overlaps are kept because every window is tested.
- **Edge cases:** `m = 0` → `0..n` before any window is formed; `m > n` → `[]` before hashing.
- **Complexity:** for `1 ≤ m ≤ n`: `O(n + m + c·m)` time, where `c` is the number of equal-hash candidate windows. This is **not** linear in the worst case: when `c` is of order `n` the bound is `O(n·m)`. Valid bound for all permitted inputs: `O(n·m + n + m + 1)` including the `n+1` empty-pattern starts. Auxiliary memory `O(1)` (rolling window); output `O(z+1)`.
- **Boundary tests:** `abdj`/`ab` (hash collision, must not report 2); `zzzz` in `zzzzabzzzz` (windows that cross the changing region, exercises the negative-remainder normalisation); the benchmark case `a^(m-2)bB` has the same hash as `a^m` for every `m` (`31·1 + (66−97) = 0`) and therefore makes every window a candidate.

### 5. `suffix` — prefix doubling + Kasai

**Prefix doubling (suffix array).**

- **Invariant:** after round `k`, `rnk[i]` is the class (dense rank starting at 0) of the suffix `i` with respect to its first `k` characters, where a suffix shorter than `k` is compared as if padded with a smaller-than-everything symbol. Round 0 sorts by the single character (counting sort over the 256 character codes).
- **Update `k → 2k`:** the key of suffix `i` is the pair `(rnk[i], rnk[i+k])`, with `-1` as second component when `i+k ≥ n`. The pairs are sorted with two stable counting-sort passes (second key first, obtained for free by shifting the current `sa` by `k`; then first key). Classes are recomputed by comparing neighbouring pairs. The loop stops as soon as all `n` classes are distinct (or `k ≥ n`), after at most `⌈log₂ n⌉` rounds.
- **Output:** exactly the `n` non-empty suffixes — no sentinel and no empty suffix is added; `sa` is a permutation of `0..n-1`.
- **Complexity:** each round is `O(n + classes) = O(n)`, so construction is `O(n log n)`; memory `O(n)` (five `int[n]` arrays + a bucket array of size `max(256, n)+1`). No suffix string is ever materialised.

**Kasai (LCP).**

- `lcp[0] = 0` and `lcp[r] = LCP(suffix sa[r-1], suffix sa[r])`. Kasai processes suffixes in *text* order `i = 0..n-1` with `j = sa[rnk[i]-1]` (the lexicographic predecessor of suffix `i`) and a running value `h`.
- **Reuse:** if suffix `i` has LCP `h` with its predecessor, then suffix `i+1` has an LCP of at least `h-1` with *its* predecessor (drop the first matching character of both suffixes). So `h` only decreases by 1 per step and every character comparison that increases `h` is paid once: `O(n)` total. For `rnk[i] == 0` (no predecessor) `h` is reset to 0.
- **Longest repeated substring:** two distinct starts share a prefix of length `L` iff some adjacent pair in suffix-array order does (any two suffixes sharing an `L`-prefix are contiguous in `sa`, and the LCP of a range is the minimum of the adjacent LCPs). Hence the longest repeat has length `max(lcp)` and is the prefix of `sa[argmax]` of that length; overlapping occurrences are allowed (`banana` → `ana` at 1 and 3). If `max(lcp) = 0`, `repeated = ""`.
- **Boundary tests:** `""` → `[],[],""`; `"a"` → `sa=[0], lcp=[0], repeated=""`; `"aaaaa"` → `sa=[4,3,2,1,0]`, `lcp=[0,1,2,3,4]`, `repeated="aaaa"` (overlap, and doubling must terminate); `"banana"` → `lcp=[0,1,3,0,0,2]` (a wrong `h` decrement changes these values).

### 6. `aho` — Aho–Corasick

- **Automaton:** one trie per request (alphabet array of 128 slots per state; the input uses codes 32..126). Each dictionary position `i` stores `pstate[i]`, the trie state where its pattern ends; **duplicate patterns end in the same state** and therefore automatically receive equal counts.
- **Failure links / goto:** BFS from the root. `fail[u]` for a child `u = go[v][c]` is `go[fail[v]][c]`; a missing edge `go[v][c]` is filled with `go[fail[v]][c]` (root misses go to the root). After this, reading a text character is a single array lookup.
- **Counting without per-match traversal:** for each text, walk the automaton and only increment `cnt[state]` per character (a *visit* count). Then process the states in **reverse BFS order** and add `cnt[s]` to `cnt[fail[s]]`. After the pass, `cnt[s]` = number of text positions at which the string of state `s` ends, i.e. the number of occurrences of that string — this includes overlaps and occurrences of a pattern as a *proper suffix* of a longer pattern (e.g. `he` inside `she`). The answer for dictionary position `i` is `cnt[pstate[i]]`.
- **Independence of texts:** `cnt` is cleared (`Arrays.fill`) before every text and the walk restarts at the root, so no counts or automaton position leak between texts or between requests; all arrays are local to the call.
- **Edge cases:** empty dictionary → one empty row per text (`[[],[]]` for two texts); no texts → `[]`; empty text → a row of zeros.
- **Complexity:** `L` = total pattern length, `p` = number of patterns, `S ≤ L+1` states, alphabet `A = 128` slots. Construction `O(L + A·S + p)` time and `O(A·S + p)` memory (for the maximum `L = 100 000` the transition table is about 51 MB, within the 384/512 MiB heap). Each text: `O(|text| + S + p)` time (the `S` term is the reverse-failure propagation). Output `O(q·(p+1))` for `q` texts. No quadratic copying of per-state output lists exists because no output lists are stored.
- **Boundary test:** `patterns=["he","she","he"]`, `texts=["sheshe","sheshe",""]` → `[[2,2,2],[2,2,2],[0,0,0]]` (suffix pattern, duplicates, independent texts, empty text).

## Own tests

All expected values come from independent oracles inside `tests/student/oracle_test.py` (brute force over all merge orders / all vertex subsets / all substrings, an LCS DP run from the end of the strings, `sorted(range(n), key=lambda i: s[i:])` for suffix arrays, a direct overlapping-occurrence counter, and `str.find` for the large search cases). Witnesses are validated by simulation (subsequence check, replaying the merge plan on the current block list, independence of the selected vertex set, repeated substring occurring at least twice), so any alternative optimum is accepted.

Summary of the actual run (`python tests/student/oracle_test.py`, environment above):

- hand-written cases: **43/43 passed**; additional exact-value assertions for the examples from the specification passed;
- random cases: 3 seeds × 400 rounds × 8 commands = **9 600 requests, all correct**, in randomly mixed task order inside one process (detects stale state);
- the same random batch sent twice in one process gave identical outputs (state reset);
- large cases (published limits): all passed (table below).

### Hand-written cases (generated by `python tests/student/oracle_test.py --table`)

|Command|Input or fixture path|Expected result|Actual result / log|What it checks|
|---|---|---|---|---|
|lcs|`lcs-both-empty`: `{"a": "", "b": ""}`|length=0, any valid LCS|`{"length": 0, "sequence": ""}` PASS|missing base case for empty prefixes|
|lcs|`lcs-one-empty`: `{"a": "abc", "b": ""}`|length=0, any valid LCS|`{"length": 0, "sequence": ""}` PASS|crash / wrong length when one string is empty|
|lcs|`lcs-subsequence-not-substring`: `{"a": "tea_time", "b": "team"}`|length=4, any valid LCS|`{"length": 4, "sequence": "team"}` PASS|returning longest common SUBSTRING (would give 3)|
|lcs|`lcs-repeated-chars`: `{"a": "aaaa", "b": "aa"}`|length=2, any valid LCS|`{"length": 2, "sequence": "aa"}` PASS|reconstruction reusing a character|
|lcs|`lcs-ties`: `{"a": "abcbdab", "b": "bdcaba"}`|length=4, any valid LCS|`{"length": 4, "sequence": "bcba"}` PASS|wrong tie handling in max(up,left) (length 4)|
|lcs|`lcs-case-space-punct`: `{"a": "Ab, c!", "b": "aB,  c"}`|length=3, any valid LCS|`{"length": 3, "sequence": ", c"}` PASS|case folding or trimming spaces/punctuation|
|merge|`merge-empty`: `{"sizes": []}`|cost=0, any valid plan|`{"cost": 0, "plan": []}` PASS|n=0 crash|
|merge|`merge-one`: `{"sizes": [7]}`|cost=0, any valid plan|`{"cost": 0, "plan": []}` PASS|n=1 must give cost 0 and empty plan|
|merge|`merge-zeros`: `{"sizes": [0, 0, 0]}`|cost=0, any valid plan|`{"cost": 0, "plan": [[1, 1, 2], [0, 0, 2]]}` PASS|zero sizes breaking plan or cost|
|merge|`merge-adjacent-vs-greedy`: `{"sizes": [10, 1, 1, 10]}`|cost=36, any valid plan|`{"cost": 36, "plan": [[1, 1, 2], [1, 2, 3], [0, 0, 3]]}` PASS|greedy / non-adjacent merging|
|merge|`merge-example`: `{"sizes": [2, 3, 4]}`|cost=14, any valid plan|`{"cost": 14, "plan": [[0, 0, 1], [0, 1, 2]]}` PASS|wrong last-split recurrence (cost 14)|
|merge|`merge-large-costs`: `{"sizes": [1000000000, 1000000000, 1000000000, 1000000000, 10000000...`|cost=1544000000000, any valid plan|`{"cost": 1544000000000, "plan": [[0, 0, 1], [2, 2, 3], [0, 1, 3], [...` PASS|32-bit overflow of total cost|
|tree|`tree-empty`: `{"n": 0, "weights": [], "edges": []}`|weight=0, any valid independent set|`{"weight": 0, "selected": []}` PASS|n=0 crash|
|tree|`tree-single-positive`: `{"n": 1, "weights": [5], "edges": []}`|weight=5, any valid independent set|`{"weight": 5, "selected": [0]}` PASS|root handling|
|tree|`tree-all-negative`: `{"n": 3, "weights": [-1, -2, -3], "edges": [[0, 1], [1, 2]]}`|weight=0, any valid independent set|`{"weight": 0, "selected": []}` PASS|must return weight 0 with empty set|
|tree|`tree-zero-ties`: `{"n": 4, "weights": [0, 0, 0, 0], "edges": [[0, 1], [1, 2], [2, 3]]}`|weight=0, any valid independent set|`{"weight": 0, "selected": []}` PASS|zero weights breaking adjacency|
|tree|`tree-star-negative-centre`: `{"n": 5, "weights": [-5, 3, 3, 3, 3], "edges": [[0, 1], [0, 2], [0,...`|weight=12, any valid independent set|`{"weight": 12, "selected": [1, 2, 3, 4]}` PASS|forcing the centre|
|tree|`tree-example`: `{"n": 3, "weights": [4, 9, 6], "edges": [[0, 1], [1, 2]]}`|weight=10, any valid independent set|`{"weight": 10, "selected": [0, 2]}` PASS|take/skip mixed up (answer 10)|
|naive|`naive-empty-pattern`: `{"text": "abc", "pattern": ""}`|positions=[0, 1, 2, 3]|`{"positions": [0, 1, 2, 3]}` PASS|empty pattern must give 0..n (n+1 starts)|
|naive|`naive-empty-text`: `{"text": "", "pattern": "a"}`|positions=[]|`{"positions": []}` PASS|empty text|
|naive|`naive-both-empty`: `{"text": "", "pattern": ""}`|positions=[0]|`{"positions": [0]}` PASS|must be [0]|
|naive|`naive-longer-pattern`: `{"text": "ab", "pattern": "abc"}`|positions=[]|`{"positions": []}` PASS|last valid start n-m / out-of-range read|
|naive|`naive-overlap`: `{"text": "aaaaa", "pattern": "aaa"}`|positions=[0, 1, 2]|`{"positions": [0, 1, 2]}` PASS|skipping overlapping matches|
|naive|`naive-case-punct`: `{"text": "Hello, hello! HELLO", "pattern": "hello"}`|positions=[7]|`{"positions": [7]}` PASS|case-insensitive search|
|kmp|`kmp-empty-pattern`: `{"text": "abc", "pattern": ""}`|positions=[0, 1, 2, 3]|`{"positions": [0, 1, 2, 3]}` PASS|indexing pi[-1] for empty pattern|
|kmp|`kmp-overlap`: `{"text": "abababa", "pattern": "aba"}`|positions=[0, 2, 4]|`{"positions": [0, 2, 4]}` PASS|no fallback after a full match|
|kmp|`kmp-self-overlap-pattern`: `{"text": "aaaaaaaa", "pattern": "aaaa"}`|positions=[0, 1, 2, 3, 4]|`{"positions": [0, 1, 2, 3, 4]}` PASS|wrong pi for periodic pattern|
|kmp|`kmp-mismatch-fallback`: `{"text": "aabaabaaa", "pattern": "aabaaa"}`|positions=[3]|`{"positions": [3]}` PASS|fallback to 0 instead of pi[k-1]|
|rk|`rk-collision`: `{"text": "abdj", "pattern": "ab"}`|positions=[0]|`{"positions": [0]}` PASS|reporting hash-equal window dj (hash 75 = hash of ab)|
|rk|`rk-empty-pattern`: `{"text": "xyz", "pattern": ""}`|positions=[0, 1, 2, 3]|`{"positions": [0, 1, 2, 3]}` PASS|empty pattern windows|
|rk|`rk-negative-remainder`: `{"text": "zzzzabzzzz", "pattern": "zzzz"}`|positions=[0, 6]|`{"positions": [0, 6]}` PASS|negative value after subtracting the leftmost char|
|rk|`rk-overlap`: `{"text": "aaaaa", "pattern": "aaa"}`|positions=[0, 1, 2]|`{"positions": [0, 1, 2]}` PASS|skipping overlapping matches|
|suffix|`suffix-empty`: `{"text": ""}`|sa=[], lcp=[0], repeated of length 0|`{"sa": [], "lcp": [], "repeated": ""}` PASS|empty text|
|suffix|`suffix-one`: `{"text": "a"}`|sa=[0], lcp=[0], repeated of length 0|`{"sa": [0], "lcp": [0], "repeated": ""}` PASS|single char: sa=[0], lcp=[0], repeated empty|
|suffix|`suffix-all-equal`: `{"text": "aaaaa"}`|sa=[4, 3, 2, 1, 0], lcp=[0, 1, 2, 3, 4], repeated of length 4|`{"sa": [4, 3, 2, 1, 0], "lcp": [0, 1, 2, 3, 4], "repeated": "aaaa"}` PASS|doubling not terminating / overlap not allowed|
|suffix|`suffix-all-distinct`: `{"text": "abcde"}`|sa=[0, 1, 2, 3, 4], lcp=[0, 0, 0, 0, 0], repeated of length 0|`{"sa": [0, 1, 2, 3, 4], "lcp": [0, 0, 0, 0, 0], "repeated": ""}` PASS|repeated must be empty|
|suffix|`suffix-banana`: `{"text": "banana"}`|sa=[5, 3, 1, 0, 4, 2], lcp=[0, 1, 3, 0, 0, 2], repeated of length 3|`{"sa": [5, 3, 1, 0, 4, 2], "lcp": [0, 1, 3, 0, 0, 2], "repeated": "...` PASS|Kasai h-decrement bug (lcp 0,1,3,0,0,2)|
|suffix|`suffix-space-punct`: `{"text": "a b a b!"}`|sa=[3, 1, 5, 7, 0, 4, 2, 6], lcp=[0, 1, 2, 0, 0, 3, 0, 1], repeated of length 3|`{"sa": [3, 1, 5, 7, 0, 4, 2, 6], "lcp": [0, 1, 2, 0, 0, 3, 0, 1], "...` PASS|treating spaces as separators|
|aho|`aho-empty-dict`: `{"patterns": [], "texts": ["abc", ""]}`|counts=[[], []]|`{"counts": [[], []]}` PASS|empty dictionary needs one empty row per text|
|aho|`aho-no-texts`: `{"patterns": ["a"], "texts": []}`|counts=[]|`{"counts": []}` PASS|must return counts=[]|
|aho|`aho-empty-text`: `{"patterns": ["a", "b"], "texts": [""]}`|counts=[[0, 0]]|`{"counts": [[0, 0]]}` PASS|empty text -> zero per pattern|
|aho|`aho-duplicates`: `{"patterns": ["he", "she", "he"], "texts": ["sheshe", "sheshe", ""]}`|counts=[[2, 2, 2], [2, 2, 2], [0, 0, 0]]|`{"counts": [[2, 2, 2], [2, 2, 2], [0, 0, 0]]}` PASS|duplicates / suffix patterns / stale counts|
|aho|`aho-overlap`: `{"patterns": ["aa", "aaa", "a"], "texts": ["aaaaa"]}`|counts=[[4, 3, 5]]|`{"counts": [[4, 3, 5]]}` PASS|overlapping occurrences|

### Large cases within the full published domains

|Command|Input|Expected result|Actual result / log|What it checks|
|---|---|---|---|---|
|lcs|5 requests up to 1000×1000 (random over `ab` and over 26 letters, equal strings, disjoint strings, one empty)|length from the independent DP, valid witness|all PASS, 0.15 s including JVM start|memory/time at len(a)·len(b) = 10⁶|
|merge|n = 200: random sizes up to 10⁹, all 10⁹, all 0, powers of two|cost from an independent memoised interval DP; plan replayed|all PASS, 0.13 s|`O(n³)` speed, 64-bit costs, plan validity|
|tree|n = 100 000: chain (random and all 10⁹), star, random tree, complete binary tree, all-negative|weight from an independent iterative DP rooted at another vertex; independence and sum of the set checked|all PASS, 0.95 s|stack safety on deep chains, `long` sums|
|naive|3000-char texts, patterns of length 1500, 8, 3000, 2999+`b`, empty|`str.find` loop|all PASS, 0.11 s|worst case `n·m`|
|kmp|text 200 000, pattern 100 000 (`a`-only, `ab`-periodic, random), pattern `a`, empty|`str.find` loop|all PASS, 0.54 s|linear time, overlap fallback|
|rk|text 10 000, pattern 2000 (`a`-only, random, `a…ab`), random short pattern, empty|`str.find` loop|all PASS, 0.13 s|domain limit `n·m ≤ 2·10⁷`, candidate verification|
|suffix|n = 50 000: all `a`, random `ab`, random 26 letters, `ab`-periodic, `abc`-periodic, 95 distinct ASCII codes|`sa` permutation + strict suffix order of neighbours, every `lcp` entry by direct comparison, `repeated` occurs twice with length `max(lcp)`|all PASS, 0.50 s|`O(n log n)` doubling, Kasai|
|aho|(a) 446 nested patterns `a^k` (≈ 99 700 total length) × 100 texts of `a^2000`; (b) 10 000 random patterns over `ab` (total ≤ 100 000) × 100 random texts of 2000|40 random pattern/text pairs per checked row compared with a `str.find` loop|all PASS, 0.23 s and 0.51 s|dense matches (reverse-failure propagation), memory of the automaton|
|mixed|aho, lcs, aho, tree, suffix, aho(empty dictionary) in one process|oracles|PASS|no state between consecutive tasks|

## Search comparison

**Setup.** Benchmark program: `tests/student/Bench.java`. Generator: `java.util.Random(seed = 20261108 + n)` for the random case, deterministic strings for the repetitive cases (stated in the table). Sizes (n, m) = (1000, 500), (2000, 1000), (3000, 1500); all are inside the common domain of the three algorithms (n, m ≤ 3000, n·m ≤ 2·10⁷). Four cases are measured separately: `random` (alphabet `abcd`, pattern = random substring of the text, so there is at least one match), `repetitive-nomatch` (text `a^n`, pattern `a^(m-1)b`), `repetitive-allmatch` (text `a^n`, pattern `a^m`: all `n-m+1` overlapping occurrences) and `repetitive-collision` (text `a^n`, pattern `a^(m-2)bB`, which has the same base-31/mod-101 hash as `a^m`, so every window is an equal-hash candidate and none is a real match).

**Correctness before timing.** For each (case, size) naive, KMP and RK were first run on the identical input and their position lists were compared with each other and with an `String.indexOf`-loop reference that exists only in the benchmark; the program aborts if they differ. All 12 inputs (4 cases × 3 sizes) passed (the last column says so, with the number of starts).

**Timing scope and policy.** One timed unit is a call of `Algorithms.naive/kmp/rk(request)` on an already parsed request (building the positions list is inside the call); JSON parsing, printing, process start and compilation are excluded; the same boundary for all three methods. Each (case, size, algorithm) cell: 300 untimed warm-up calls (JIT warm-up), then 3 measured runs; **one run = mean time per call over 20 consecutive calls**, measured with `System.nanoTime`, reported in **microseconds**; the median of the 3 runs is reported. Hardware/runtime: see "Environment and commands" (Intel Core i7-12700H, Java 25.0.1, `-Xmx384m`). Commands are listed there.

|Case|n|m|Seed/generator|Algorithm|Run 1 (us)|Run 2 (us)|Run 3 (us)|Median (us)|Correct outputs checked|
|---|---:|---:|---|---|---:|---:|---:|---:|---|
|random|1000|500|Random(20262108), alphabet abcd, pattern = random substring of text (offset 414)|naive|13.5|16.2|12.1|13.5|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|1000|500|Random(20262108), alphabet abcd, pattern = random substring of text (offset 414)|kmp|28.7|28.6|32.8|28.7|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|1000|500|Random(20262108), alphabet abcd, pattern = random substring of text (offset 414)|rk|39.2|44.3|39.5|39.5|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|2000|1000|Random(20263108), alphabet abcd, pattern = random substring of text (offset 338)|naive|24.0|24.5|24.1|24.1|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|2000|1000|Random(20263108), alphabet abcd, pattern = random substring of text (offset 338)|kmp|13.6|9.3|7.2|9.3|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|2000|1000|Random(20263108), alphabet abcd, pattern = random substring of text (offset 338)|rk|46.3|45.6|45.6|45.6|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|3000|1500|Random(20264108), alphabet abcd, pattern = random substring of text (offset 241)|naive|3.9|3.6|3.8|3.8|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|3000|1500|Random(20264108), alphabet abcd, pattern = random substring of text (offset 241)|kmp|10.2|9.7|9.7|9.7|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|random|3000|1500|Random(20264108), alphabet abcd, pattern = random substring of text (offset 241)|rk|27.1|27.2|29.6|27.2|yes (naive=kmp=rk=indexOf reference, 1 starts)|
|repetitive-nomatch|1000|500|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|naive|210.6|210.0|212.0|210.6|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|1000|500|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|kmp|10.4|5.9|4.9|5.9|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|1000|500|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|rk|8.7|7.5|7.6|7.6|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|2000|1000|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|naive|823.5|820.4|822.1|822.1|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|2000|1000|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|kmp|9.7|9.8|9.5|9.7|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|2000|1000|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|rk|15.4|14.7|15.2|15.2|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|3000|1500|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|naive|1838.1|1892.4|1846.3|1846.3|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|3000|1500|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|kmp|14.2|14.5|14.0|14.2|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-nomatch|3000|1500|deterministic: text a^n, pattern a^(m-1)b (no occurrence)|rk|24.0|22.6|25.0|24.0|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-allmatch|1000|500|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|naive|215.2|213.4|212.4|213.4|yes (naive=kmp=rk=indexOf reference, 501 starts)|
|repetitive-allmatch|1000|500|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|kmp|8.5|7.4|7.4|7.4|yes (naive=kmp=rk=indexOf reference, 501 starts)|
|repetitive-allmatch|1000|500|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|rk|432.9|426.1|425.3|426.1|yes (naive=kmp=rk=indexOf reference, 501 starts)|
|repetitive-allmatch|2000|1000|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|naive|828.0|829.7|831.0|829.7|yes (naive=kmp=rk=indexOf reference, 1001 starts)|
|repetitive-allmatch|2000|1000|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|kmp|13.2|70.6|12.0|13.2|yes (naive=kmp=rk=indexOf reference, 1001 starts)|
|repetitive-allmatch|2000|1000|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|rk|1671.1|1665.0|1679.2|1671.1|yes (naive=kmp=rk=indexOf reference, 1001 starts)|
|repetitive-allmatch|3000|1500|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|naive|1840.1|1841.4|1838.7|1840.1|yes (naive=kmp=rk=indexOf reference, 1501 starts)|
|repetitive-allmatch|3000|1500|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|kmp|14.3|14.8|13.8|14.3|yes (naive=kmp=rk=indexOf reference, 1501 starts)|
|repetitive-allmatch|3000|1500|deterministic: text a^n, pattern a^m (n-m+1 overlapping occurrences)|rk|4282.3|4311.8|4300.5|4300.5|yes (naive=kmp=rk=indexOf reference, 1501 starts)|
|repetitive-collision|1000|500|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|naive|210.3|208.1|208.2|208.2|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|1000|500|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|kmp|5.6|4.5|4.6|4.6|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|1000|500|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|rk|453.0|442.0|457.9|453.0|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|2000|1000|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|naive|817.2|806.2|814.9|814.9|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|2000|1000|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|kmp|9.8|9.3|9.6|9.6|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|2000|1000|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|rk|1879.8|1879.2|1745.9|1879.2|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|3000|1500|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|naive|1840.0|1844.1|1839.3|1840.0|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|3000|1500|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|kmp|14.8|13.7|15.1|14.8|yes (naive=kmp=rk=indexOf reference, 0 starts)|
|repetitive-collision|3000|1500|deterministic: text a^n, pattern a^(m-2)bB (same hash as a^m: every window collides, no occurrence)|rk|4288.3|4306.7|4301.7|4301.7|yes (naive=kmp=rk=indexOf reference, 0 starts)|

**Observations (not a proof of asymptotic complexity).**

- *Run-to-run noise.* The benchmark was run with 300 warm-up calls per cell and 3 measured runs (each averaging 20 consecutive calls). Across most cells, results are remarkably consistent, but occasional spikes occur in microsecond-scale measurements: for example, KMP on `repetitive-allmatch` at n = 2000 spiked to 70.6 µs in Run 2 compared to 13.2 µs in Run 1 and 12.0 µs in Run 3; similarly KMP on `repetitive-nomatch` at n = 1000 dropped from 10.4 µs in Run 1 to 4.9 µs in Run 3. Such sub-50 µs differences are typical of JIT tiering, background thread scheduling or garbage collection jitter, so asymptotic conclusions are drawn from the large and consistent multi-fold scaling effects across input sizes.
- *Random case:* all three algorithms complete within a few to tens of microseconds (3.8–45.6 µs). At n = 1000 naive is fastest (median 13.5 µs vs KMP 28.7 µs and RK 39.5 µs); at n = 2000 KMP leads (9.3 µs vs naive 24.1 µs and RK 45.6 µs); at n = 3000 naive finishes in 3.8 µs because the match happens early at offset 241. On random 4-letter texts, character mismatches occur almost immediately (probability 3/4 on the very first character), allowing naive to advance quickly without paying upfront overhead for pattern pre-processing (the $\pi$-table in KMP or power computations in RK). Differences here remain at the microsecond noise level.
- *Repetitive, no match:* naive performs about $(n-m+1) \cdot m$ character comparisons (250 500 at n = 1000; 1 001 000 at n = 2000; 2 251 500 at n = 3000). Its medians (210.6 → 822.1 → 1846.3 µs) scale quadratically (×3.90 and ×2.25, overall ×8.77, very close to the theoretical 9× comparison growth 1 : 4 : 9). KMP remains strictly linear (5.9 → 9.7 → 14.2 µs), running over 130× faster than naive at n = 3000. RK is also very fast and linear here (7.6 → 15.2 → 24.0 µs) because the rolling hash $H(a^m) = 0$ never matches $H(a^{m-1}b) = 1$ under modulus 101, resulting in zero candidate false alarms ($c = 0$) and zero candidate verifications.
- *Repetitive, all match:* every window is a full match ($n-m+1$ matches). Naive performs full length-$m$ comparisons at each position, yielding quadratic scaling (213.4 → 829.7 → 1840.1 µs). KMP executes linear $O(n+m+z)$ transitions with prefix-border fallbacks, finishing in 7.4 → 13.2 → 14.3 µs (roughly 28× to 128× faster than naive). RK performs the rolling-hash calculation and must additionally verify all $n-m+1$ matching windows; this full character verification plus rolling-hash overhead makes RK 2× slower than naive (426.1 → 1671.1 → 4300.5 µs, scaling ×10.09 overall).
- *Repetitive, collision:* this case isolates RK's worst-case candidate sensitivity $O(n + m + c \cdot m)$. Because $a^{m-2}bB$ has the exact same base-31 mod 101 hash as $a^m$, all $c = n-m+1$ windows collide, triggering full verification for every window before failing on the last characters. RK times scale quadratically (453.0 → 1879.2 → 4301.7 µs, growth 1 : 4.15 : 9.49), closely tracking the comparison count growth (1 : 4 : 9). Naive performs the same character comparisons (208.2 → 814.9 → 1840.0 µs), while RK pays hashing and collision checking on top. KMP is unaffected by hash collisions and stays linear (4.6 → 9.6 → 14.8 µs).
- *Modulus 101:* it is deliberately tiny so that collisions are easy to construct and test (`ab`/`dj`, and `a^(m-2)bB` versus `a^m`). With only 101 hash values an arbitrary non-matching window collides with probability about 1/101, so on random text the expected number of candidates is already about `n/101`. This laboratory choice says nothing about production implementations that use a large (often 61-bit or 64-bit) modulus and/or a randomly chosen base, where the collision probability per window is negligible and the expected running time is `O(n + m)`; the quadratic behaviour above comes from the weak fixed hash combined with an input constructed against it. The supplied pair `ab`/`dj` and my `a^(m-2)bB` family are *correctness* tests; the timing medians do not prove an asymptotic bound.

## Sources and AI assistance

- **Course material:** assignment specification and its docs in the template repository (`docs/Assignment_4_EN.md`, `docs/guide/*`, algorithm notes), lecture 8–10 topics (DP patterns, KMP/hash, suffix arrays/Kasai/Aho–Corasick).
- **AI assistance:** AI assistance was used to better understand the problem statements and requirements, clarify complex edge cases and contracts in the assignment specifications, and explore algorithm trade-offs. All code and benchmarks were executed and verified independently on the local machine.
- **Verification of the work:** the independent oracles and validators described under "Own tests" (they do not share code with the implementation), the 44 public checks, the random cross-checks and the large-domain tests. No external algorithm library and no built-in substring search is used in the algorithms.
