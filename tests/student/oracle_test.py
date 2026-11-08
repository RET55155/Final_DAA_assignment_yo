#!/usr/bin/env python3
"""Own tests for Assignment 4 (all eight commands).

Run from the repository root AFTER `python tools/run.py --setup` (it compiles the selected language):

    python tests/student/oracle_test.py            # hand-written + random + large tests
    python tests/student/oracle_test.py --quick    # skip the large (scale) tests
    python tests/student/oracle_test.py --table    # print the hand-written cases as Markdown rows

Every expected value comes from an INDEPENDENT oracle written here (brute force / different method), never
from the submitted implementation. Witnesses (LCS string, merge plan, tree set, repeated substring) are
validated by simulation, so any alternative optimum is accepted.
"""
import itertools, json, random, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import run as launcher  # noqa: E402  (reuses the official launcher so we test exactly what graders run)

LANG = json.loads((ROOT / "submission.json").read_text())["language"]
FAILS = []


_EXE = []


def run_batch(reqs):
    if not _EXE: _EXE.append(launcher.build(LANG))
    exe = _EXE[0]
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reqs)
    t = time.time()
    p = subprocess.run(exe, input=data, capture_output=True, text=True, encoding="utf-8", timeout=120)
    dt = time.time() - t
    lines = p.stdout.splitlines()
    if p.returncode != 0 or len(lines) != len(reqs):
        raise SystemExit(f"process failure rc={p.returncode} lines={len(lines)}/{len(reqs)}\n{p.stderr[:2000]}")
    return [json.loads(l) for l in lines], dt


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)

# ---------------------------------------------------------------- independent oracles + validators
def lcs_len_oracle(a, b):  # DP from the END of the strings (different direction than the solution)
    n, m = len(a), len(b)
    f = [[0] * (m + 2) for _ in range(n + 2)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            f[i][j] = f[i + 1][j + 1] + 1 if a[i] == b[j] else max(f[i + 1][j], f[i][j + 1])
    return f[0][0]


def is_subseq(s, t):
    it = iter(t)
    return all(c in it for c in s)


def check_lcs(req, out):
    if not (is_int(out.get("length")) and isinstance(out.get("sequence"), str)):
        return "schema"
    want = lcs_len_oracle(req["a"], req["b"])
    if out["length"] != want: return f"length {out['length']} != {want}"
    s = out["sequence"]
    if len(s) != want or not is_subseq(s, req["a"]) or not is_subseq(s, req["b"]): return "bad witness"


def merge_oracle(sizes):  # brute force over every possible sequence of adjacent merges
    from functools import lru_cache
    @lru_cache(None)
    def go(blocks):
        if len(blocks) <= 1: return 0
        return min(blocks[i] + blocks[i + 1] + go(blocks[:i] + (blocks[i] + blocks[i + 1],) + blocks[i + 2:])
                   for i in range(len(blocks) - 1))
    return go(tuple(sizes))


def merge_interval_oracle(s):  # independent top-down memoised interval DP (used for n > 8)
    from functools import lru_cache
    pre = [0]
    for x in s: pre.append(pre[-1] + x)
    sys.setrecursionlimit(10000)
    @lru_cache(None)
    def f(l, r):
        return 0 if l == r else min(f(l, k) + f(k + 1, r) for k in range(l, r)) + pre[r + 1] - pre[l]
    return f(0, len(s) - 1) if s else 0


def check_merge(req, out, want=None):
    s = req["sizes"]
    if not (is_int(out.get("cost")) and isinstance(out.get("plan"), list)): return "schema"
    if want is None: want = merge_oracle(s) if len(s) <= 8 else merge_interval_oracle(s)
    if out["cost"] != want: return f"cost {out['cost']} != {want}"
    if len(s) <= 1:
        return None if out["plan"] == [] else "plan must be empty"
    blocks = {(i, i): s[i] for i in range(len(s))}
    total = 0
    if len(out["plan"]) != len(s) - 1: return "plan length"
    for st in out["plan"]:
        if not (isinstance(st, list) and len(st) == 3 and all(is_int(v) for v in st)): return "step schema"
        l, k, r = st
        if (l, k) not in blocks or (k + 1, r) not in blocks: return f"step {st} not adjacent current blocks"
        v = blocks.pop((l, k)) + blocks.pop((k + 1, r))
        total += v
        blocks[(l, r)] = v
    if total != out["cost"]: return "plan cost != reported cost"
    if list(blocks) != [(0, len(s) - 1)]: return "not fully merged"


def tree_brute(n, w, edges):
    best = 0
    for mask in range(1 << n):
        if any((mask >> u & 1) and (mask >> v & 1) for u, v in edges): continue
        best = max(best, sum(w[i] for i in range(n) if mask >> i & 1))
    return best


def check_tree(req, out, want=None):
    n, w, edges = req["n"], req["weights"], req["edges"]
    if not (is_int(out.get("weight")) and isinstance(out.get("selected"), list)
            and all(is_int(v) for v in out["selected"])): return "schema"
    sel = out["selected"]
    if len(set(sel)) != len(sel) or any(not 0 <= v < n for v in sel): return "repeated/out-of-range vertex"
    S = set(sel)
    if any(u in S and v in S for u, v in edges): return "adjacent vertices selected"
    if sum(w[v] for v in sel) != out["weight"]: return "weight != sum of selected"
    want = tree_brute(n, w, edges) if want is None else want
    if out["weight"] != want: return f"weight {out['weight']} != {want}"


def tree_dp_oracle(n, w, edges):  # independent: children lists from parent array built by DFS stack, own DP
    if n == 0: return 0
    adj = [[] for _ in range(n)]
    for u, v in edges: adj[u].append(v); adj[v].append(u)
    par, order, st = [-1] * n, [], [n - 1]  # DIFFERENT root (last vertex) on purpose
    par[n - 1] = n - 1
    while st:
        v = st.pop(); order.append(v)
        for u in adj[v]:
            if par[u] == -1: par[u] = v; st.append(u)
    a = [0] * n; b = [0] * n  # a: v taken, b: v skipped
    for v in reversed(order):
        a[v] += w[v]
        if par[v] != v:
            p = par[v]; a[p] += b[v]; b[p] += max(a[v], b[v])
    return max(a[n - 1], b[n - 1])


def occ(t, p):
    if p == "": return list(range(len(t) + 1))
    return [i for i in range(len(t) - len(p) + 1) if t[i:i + len(p)] == p]


def check_search(req, out):
    if not (isinstance(out.get("positions"), list) and all(is_int(v) for v in out["positions"])): return "schema"
    want = occ(req["text"], req["pattern"])
    if out["positions"] != want: return f"positions {out['positions'][:10]} != {want[:10]}"


def lcp_direct(s, a, b):
    h = 0
    while a + h < len(s) and b + h < len(s) and s[a + h] == s[b + h]: h += 1
    return h


def check_suffix(req, out, full=True):
    s = req["text"]; n = len(s)
    if not (isinstance(out.get("sa"), list) and isinstance(out.get("lcp"), list) and isinstance(out.get("repeated"), str)
            and all(is_int(v) for v in out["sa"] + out["lcp"])): return "schema"
    sa, lcp = out["sa"], out["lcp"]
    if len(sa) != n or len(lcp) != n or sorted(sa) != list(range(n)): return "sa not a permutation / wrong length"
    if full:
        if sa != sorted(range(n), key=lambda i: s[i:]): return "sa order"
    else:
        for i in range(1, n):
            if not s[sa[i - 1]:] < s[sa[i]:]: return f"sa order at {i}"
    if n and lcp[0] != 0: return "lcp[0] != 0"
    for i in range(1, n):
        a, b, h = sa[i - 1], sa[i], lcp[i]
        if not (s[a:a + h] == s[b:b + h] and (a + h == n or b + h == n or s[a + h] != s[b + h])): return f"lcp[{i}]"
    best = max(lcp) if n else 0
    if full:  # brute-force longest substring with two distinct starts
        bl = 0
        for i in range(n):
            for j in range(i + 1, n): bl = max(bl, lcp_direct(s, i, j))
        if bl != best: return "oracle mismatch on max lcp"
    r = out["repeated"]
    if len(r) != best: return f"repeated length {len(r)} != {best}"
    if best and sum(1 for i in range(n - best + 1) if s[i:i + best] == r) < 2: return "repeated occurs once"


def check_aho(req, out):
    c = out.get("counts")
    if not (isinstance(c, list) and all(isinstance(r, list) and all(is_int(v) for v in r) for r in c)): return "schema"
    if len(c) != len(req["texts"]): return "row count"
    for row, t in zip(c, req["texts"]):
        if len(row) != len(req["patterns"]): return "row width"
        for v, p in zip(row, req["patterns"]):
            if v != len(occ(t, p)): return f"count {v} != {len(occ(t, p))} for {p!r} in {t[:20]!r}"

CHECK = {"lcs": check_lcs, "merge": check_merge, "tree": check_tree, "naive": check_search, "kmp": check_search,
         "rk": check_search, "suffix": check_suffix, "aho": check_aho}

# ---------------------------------------------------------------- hand-written cases (name, request, defect it detects)
def S(task, **kw): return {"task": task, **kw}

HAND = [
    ("lcs-both-empty", S("lcs", a="", b=""), "missing base case for empty prefixes"),
    ("lcs-one-empty", S("lcs", a="abc", b=""), "crash / wrong length when one string is empty"),
    ("lcs-subsequence-not-substring", S("lcs", a="tea_time", b="team"), "returning longest common SUBSTRING (would give 3)"),
    ("lcs-repeated-chars", S("lcs", a="aaaa", b="aa"), "reconstruction reusing a character"),
    ("lcs-ties", S("lcs", a="abcbdab", b="bdcaba"), "wrong tie handling in max(up,left) (length 4)"),
    ("lcs-case-space-punct", S("lcs", a="Ab, c!", b="aB,  c"), "case folding or trimming spaces/punctuation"),
    ("merge-empty", S("merge", sizes=[]), "n=0 crash"),
    ("merge-one", S("merge", sizes=[7]), "n=1 must give cost 0 and empty plan"),
    ("merge-zeros", S("merge", sizes=[0, 0, 0]), "zero sizes breaking plan or cost"),
    ("merge-adjacent-vs-greedy", S("merge", sizes=[10, 1, 1, 10]), "greedy / non-adjacent merging"),
    ("merge-example", S("merge", sizes=[2, 3, 4]), "wrong last-split recurrence (cost 14)"),
    ("merge-large-costs", S("merge", sizes=[10**9] * 200), "32-bit overflow of total cost"),
    ("tree-empty", S("tree", n=0, weights=[], edges=[]), "n=0 crash"),
    ("tree-single-positive", S("tree", n=1, weights=[5], edges=[]), "root handling"),
    ("tree-all-negative", S("tree", n=3, weights=[-1, -2, -3], edges=[[0, 1], [1, 2]]), "must return weight 0 with empty set"),
    ("tree-zero-ties", S("tree", n=4, weights=[0, 0, 0, 0], edges=[[0, 1], [1, 2], [2, 3]]), "zero weights breaking adjacency"),
    ("tree-star-negative-centre", S("tree", n=5, weights=[-5, 3, 3, 3, 3], edges=[[0, 1], [0, 2], [0, 3], [0, 4]]), "forcing the centre"),
    ("tree-example", S("tree", n=3, weights=[4, 9, 6], edges=[[0, 1], [1, 2]]), "take/skip mixed up (answer 10)"),
    ("naive-empty-pattern", S("naive", text="abc", pattern=""), "empty pattern must give 0..n (n+1 starts)"),
    ("naive-empty-text", S("naive", text="", pattern="a"), "empty text"),
    ("naive-both-empty", S("naive", text="", pattern=""), "must be [0]"),
    ("naive-longer-pattern", S("naive", text="ab", pattern="abc"), "last valid start n-m / out-of-range read"),
    ("naive-overlap", S("naive", text="aaaaa", pattern="aaa"), "skipping overlapping matches"),
    ("naive-case-punct", S("naive", text="Hello, hello! HELLO", pattern="hello"), "case-insensitive search"),
    ("kmp-empty-pattern", S("kmp", text="abc", pattern=""), "indexing pi[-1] for empty pattern"),
    ("kmp-overlap", S("kmp", text="abababa", pattern="aba"), "no fallback after a full match"),
    ("kmp-self-overlap-pattern", S("kmp", text="aaaaaaaa", pattern="aaaa"), "wrong pi for periodic pattern"),
    ("kmp-mismatch-fallback", S("kmp", text="aabaabaaa", pattern="aabaaa"), "fallback to 0 instead of pi[k-1]"),
    ("rk-collision", S("rk", text="abdj", pattern="ab"), "reporting hash-equal window dj (hash 75 = hash of ab)"),
    ("rk-empty-pattern", S("rk", text="xyz", pattern=""), "empty pattern windows"),
    ("rk-negative-remainder", S("rk", text="zzzzabzzzz", pattern="zzzz"), "negative value after subtracting the leftmost char"),
    ("rk-overlap", S("rk", text="aaaaa", pattern="aaa"), "skipping overlapping matches"),
    ("suffix-empty", S("suffix", text=""), "empty text"),
    ("suffix-one", S("suffix", text="a"), "single char: sa=[0], lcp=[0], repeated empty"),
    ("suffix-all-equal", S("suffix", text="aaaaa"), "doubling not terminating / overlap not allowed"),
    ("suffix-all-distinct", S("suffix", text="abcde"), "repeated must be empty"),
    ("suffix-banana", S("suffix", text="banana"), "Kasai h-decrement bug (lcp 0,1,3,0,0,2)"),
    ("suffix-space-punct", S("suffix", text="a b a b!"), "treating spaces as separators"),
    ("aho-empty-dict", S("aho", patterns=[], texts=["abc", ""]), "empty dictionary needs one empty row per text"),
    ("aho-no-texts", S("aho", patterns=["a"], texts=[]), "must return counts=[]"),
    ("aho-empty-text", S("aho", patterns=["a", "b"], texts=[""]), "empty text -> zero per pattern"),
    ("aho-duplicates", S("aho", patterns=["he", "she", "he"], texts=["sheshe", "sheshe", ""]), "duplicates / suffix patterns / stale counts"),
    ("aho-overlap", S("aho", patterns=["aa", "aaa", "a"], texts=["aaaaa"]), "overlapping occurrences"),
]


def expected_str(req):
    """Expected result as computed by the independent oracles (witness fields: 'any valid ...')."""
    t = req["task"]
    if t == "lcs": return f"length={lcs_len_oracle(req['a'], req['b'])}, any valid LCS"
    if t == "merge":
        s = req["sizes"]
        return f"cost={merge_oracle(s) if len(s) <= 8 else merge_interval_oracle(s)}, any valid plan"
    if t == "tree": return f"weight={tree_brute(req['n'], req['weights'], req['edges'])}, any valid independent set"
    if t in ("naive", "kmp", "rk"): return f"positions={occ(req['text'], req['pattern'])}"
    if t == "suffix":
        x = req["text"]; sa = sorted(range(len(x)), key=lambda i: x[i:])
        lcp = [0] + [lcp_direct(x, sa[i - 1], sa[i]) for i in range(1, len(x))]
        return f"sa={sa}, lcp={lcp}, repeated of length {max(lcp) if lcp else 0}"
    return "counts=" + json.dumps([[len(occ(t_, p)) for p in req["patterns"]] for t_ in req["texts"]])


def validate(req, out, **kw):
    if "error" in out: return f"error: {out['error']}"
    return CHECK[req["task"]](req, out, **kw) if kw else CHECK[req["task"]](req, out)

# ---------------------------------------------------------------- random generators (small, vs brute force)
def rstr(rng, lo, hi, alpha):
    return "".join(rng.choice(alpha) for _ in range(rng.randint(lo, hi)))


def rtree(rng, n, shape):
    if shape == "chain": return [[i, i + 1] for i in range(n - 1)]
    if shape == "star": return [[0, i] for i in range(1, n)]
    perm = list(range(n)); rng.shuffle(perm)
    return [[perm[rng.randrange(i)], perm[i]] if rng.random() < .5 else [perm[i], perm[rng.randrange(i)]] for i in range(1, n)]


def random_cases(seed, count):
    rng = random.Random(seed)
    cases = []
    for _ in range(count):
        alpha = rng.choice(["ab", "abc", "a", "ab ,Z", "abcdefghij"])
        cases.append(S("lcs", a=rstr(rng, 0, 9, alpha), b=rstr(rng, 0, 9, alpha)))
        cases.append(S("merge", sizes=[rng.choice([0, 1, 2, 3, 7, 10**9]) for _ in range(rng.randint(0, 7))]))
        n = rng.randint(0, 12)
        cases.append(S("tree", n=n, weights=[rng.randint(-6, 9) for _ in range(n)], edges=rtree(rng, n, rng.choice(["chain", "star", "rand"]))))
        t, p = rstr(rng, 0, 30, alpha), rstr(rng, 0, 4, alpha)
        for task in ("naive", "kmp", "rk"): cases.append(S(task, text=t, pattern=p))
        cases.append(S("suffix", text=rstr(rng, 0, 18, alpha)))
        pats = [rstr(rng, 1, 4, alpha) for _ in range(rng.randint(0, 6))]
        if pats and rng.random() < .5: pats.append(rng.choice(pats))
        cases.append(S("aho", patterns=pats, texts=[rstr(rng, 0, 25, alpha) for _ in range(rng.randint(0, 4))]))
    rng.shuffle(cases)  # mixed tasks in one process also tests state reset
    return cases

# ---------------------------------------------------------------- large (scale) tests
def large_tests():
    rng = random.Random(2026)
    total_fail = 0

    def report(name, req_list, checker, dt_note=""):
        nonlocal total_fail
        outs, dt = run_batch(req_list)
        bad = None
        for r, o in zip(req_list, outs):
            bad = bad or ("error: " + o["error"] if "error" in o else checker(r, o))
        status = "PASS" if not bad else f"FAIL ({bad})"
        if bad: total_fail += 1; FAILS.append(name)
        print(f"  {status:6} {name}  [{dt:.2f}s incl. JVM start]")

    print("large tests (full published domains):")
    # LCS 1000x1000 (|a|*|b| = 1e6)
    reqs = [S("lcs", a=rstr(rng, 1000, 1000, "ab"), b=rstr(rng, 1000, 1000, "ab")),
            S("lcs", a=rstr(rng, 1000, 1000, "abcdefghijklmnopqrstuvwxyz"), b=rstr(rng, 1000, 1000, "abcdefghijklmnopqrstuvwxyz")),
            S("lcs", a="a" * 1000, b="a" * 1000), S("lcs", a="a" * 1000, b="b" * 1000),
            S("lcs", a="x" * 1000, b="")]
    report("lcs 1000x1000", reqs, check_lcs)
    # merge n = 200
    reqs = [S("merge", sizes=[rng.randint(0, 10**9) for _ in range(200)]), S("merge", sizes=[10**9] * 200),
            S("merge", sizes=[0] * 200), S("merge", sizes=[2 ** (i % 30) for i in range(200)])]
    report("merge n=200", reqs, check_merge)
    # tree n = 100000: chain, star, random, binary, all-negative, big weights
    n = 100000
    ws = lambda lo, hi: [rng.randint(lo, hi) for _ in range(n)]
    bin_edges = [[(i - 1) // 2, i] for i in range(1, n)]
    reqs = [S("tree", n=n, weights=ws(-10**9, 10**9), edges=rtree(rng, n, "chain")),
            S("tree", n=n, weights=[10**9] * n, edges=rtree(rng, n, "chain")),
            S("tree", n=n, weights=ws(-10**9, 10**9), edges=rtree(rng, n, "star")),
            S("tree", n=n, weights=ws(-10**9, 10**9), edges=rtree(rng, n, "rand")),
            S("tree", n=n, weights=ws(-10**9, 10**9), edges=bin_edges),
            S("tree", n=n, weights=ws(-10**9, -1), edges=rtree(rng, n, "rand"))]
    report("tree n=100000", reqs, lambda r, o: check_tree(r, o, want=tree_dp_oracle(r["n"], r["weights"], r["edges"])))
    # naive 3000x3000, kmp 200000/100000, rk 10000x2000
    def pyfind(t, p):
        res, i = [], t.find(p)
        while i != -1: res.append(i); i = t.find(p, i + 1)
        return res
    def sref(req, out):
        want = pyfind(req["text"], req["pattern"]) if req["pattern"] else list(range(len(req["text"]) + 1))
        return None if out.get("positions") == want else "positions differ from str.find oracle"
    reqs = [S("naive", text="a" * 3000, pattern="a" * 1500), S("naive", text=rstr(rng, 3000, 3000, "ab"), pattern=rstr(rng, 8, 8, "ab")),
            S("naive", text="a" * 3000, pattern="a" * 3000), S("naive", text="a" * 3000, pattern=""), S("naive", text="a" * 3000, pattern="a" * 2999 + "b")]
    report("naive 3000", reqs, sref)
    reqs = [S("kmp", text="a" * 200000, pattern="a" * 100000), S("kmp", text="a" * 200000, pattern="a"),
            S("kmp", text=rstr(rng, 200000, 200000, "ab"), pattern=rstr(rng, 12, 12, "ab")),
            S("kmp", text="ab" * 100000, pattern="ab" * 50000), S("kmp", text="a" * 200000, pattern="a" * 99999 + "b"),
            S("kmp", text="a" * 200000, pattern="")]
    report("kmp 200000/100000", reqs, sref)
    reqs = [S("rk", text="a" * 10000, pattern="a" * 2000), S("rk", text=rstr(rng, 10000, 10000, "ab"), pattern=rstr(rng, 2000, 2000, "ab")),
            S("rk", text=rstr(rng, 10000, 10000, "abc"), pattern=rstr(rng, 5, 5, "abc")), S("rk", text="a" * 10000, pattern="a" * 2000 + "b"),
            S("rk", text="a" * 10000, pattern="")]
    report("rk 10000x2000", reqs, sref)
    # suffix n = 50000
    reqs = [S("suffix", text="a" * 50000), S("suffix", text=rstr(rng, 50000, 50000, "ab")),
            S("suffix", text=rstr(rng, 50000, 50000, "abcdefghijklmnopqrstuvwxyz")),
            S("suffix", text="ab" * 25000), S("suffix", text=("abc" * 20000)[:50000]),
            S("suffix", text="".join(chr(32 + (i * 7919) % 95) for i in range(50000)))]
    report("suffix n=50000", reqs, lambda r, o: check_suffix(r, o, full=False))
    # aho: dense matches, many patterns
    pats = ["a" * k for k in range(1, 447)]  # total length ~ 99681, nested suffix patterns
    big = S("aho", patterns=pats, texts=["a" * 2000] * 100)
    pats2 = [rstr(rng, 1, 18, "ab") for _ in range(10000)]  # total <= 100000 (checked below)
    while sum(map(len, pats2)) > 100000: pats2.pop()
    texts2 = [rstr(rng, 2000, 2000, "ab") for _ in range(100)]
    def aho_spot(req, out):
        c = out.get("counts")
        if not (isinstance(c, list) and len(c) == len(req["texts"])): return "rows"
        for ti in (0, len(c) - 1):
            if len(c[ti]) != len(req["patterns"]): return "width"
            for pi in random.Random(ti).sample(range(len(req["patterns"])), min(40, len(req["patterns"]))):
                if c[ti][pi] != len(pyfind(req["texts"][ti], req["patterns"][pi])): return f"count mismatch text {ti} pattern {pi}"
    report("aho dense nested (a^k, k<=446)", [big], aho_spot)
    report("aho 10000 random patterns", [S("aho", patterns=pats2, texts=texts2)], aho_spot)
    # consecutive different tasks in ONE process with big inputs (state reset)
    mix = [S("aho", patterns=["a"], texts=["aaa"]), S("lcs", a="abc", b="abc"), S("aho", patterns=["a"], texts=["a"]),
           S("tree", n=1, weights=[3], edges=[]), S("suffix", text="aa"), S("aho", patterns=[], texts=["x"])]
    report("mixed consecutive requests", mix, lambda r, o: CHECK[r["task"]](r, o))
    return total_fail

# ---------------------------------------------------------------- main
def main():
    args = set(sys.argv[1:])
    if "--table" in args:
        outs, _ = run_batch([r for _, r, _ in HAND])
        print("|Command|Input or fixture path|Expected result|Actual result / log|What it checks|\n|---|---|---|---|---|")
        for (name, req, defect), out in zip(HAND, outs):
            j = lambda x: json.dumps(x, ensure_ascii=False)
            rs = j({k: v for k, v in req.items() if k != "task"})
            if len(rs) > 70: rs = rs[:67] + "..."
            ac = j(out) if len(j(out)) <= 70 else j(out)[:67] + "..."
            st = validate(req, out)
            print(f"|{req['task']}|`{name}`: `{rs}`|{expected_str(req) if st is None else 'MISMATCH'}|`{ac}` {'PASS' if st is None else 'FAIL: ' + st}|{defect}|")
        return
    print(f"language: {LANG}")
    outs, dt = run_batch([r for _, r, _ in HAND])
    bad = 0
    for (name, req, _), out in zip(HAND, outs):
        st = validate(req, out)
        if st: bad += 1; FAILS.append(name); print(f"  FAIL hand {name}: {st}  -> {json.dumps(out)[:200]}")
    print(f"hand-written: {len(HAND) - bad}/{len(HAND)} passed [{dt:.2f}s]")
    exact = {"naive-overlap": {"positions": [0, 1, 2]}, "kmp-overlap": {"positions": [0, 2, 4]}, "rk-collision": {"positions": [0]},
             "suffix-banana": {"sa": [5, 3, 1, 0, 4, 2], "lcp": [0, 1, 3, 0, 0, 2]}, "merge-example": {"cost": 14},
             "aho-duplicates": {"counts": [[2, 2, 2], [2, 2, 2], [0, 0, 0]]}, "tree-example": {"weight": 10}, "tree-all-negative": {"weight": 0, "selected": []},
             "lcs-subsequence-not-substring": {"length": 4, "sequence": "team"}, "naive-both-empty": {"positions": [0]},
             "merge-adjacent-vs-greedy": {"cost": 36}}
    for (name, _, _), out in zip(HAND, outs):
        if name in exact and any(out.get(k) != v for k, v in exact[name].items()):
            FAILS.append(name); print(f"  FAIL exact {name}: {out}")
    total = 0
    for seed in (1, 2, 3):
        cases = random_cases(seed, 400)
        outs, dt = run_batch(cases)
        b = 0
        for req, out in zip(cases, outs):
            st = validate(req, out)
            if st: b += 1; FAILS.append(f"random seed {seed}"); print(f"  FAIL random {req['task']} {json.dumps(req)[:150]}: {st}")
        total += len(cases)
        print(f"random seed {seed}: {len(cases) - b}/{len(cases)} passed (mixed tasks, one process) [{dt:.2f}s]")
    # the same batch twice in one process -> stale state would differ
    cases = random_cases(9, 150)
    outs, _ = run_batch(cases + cases)
    same = outs[:len(cases)] == outs[len(cases):]
    print(f"repeated batch in one process identical: {same}")
    if not same: FAILS.append("state reset")
    if "--quick" not in args: large_tests()
    print("\nRESULT:", "ALL PASSED" if not FAILS else f"FAILURES: {sorted(set(FAILS))}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
