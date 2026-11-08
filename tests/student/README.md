# Your own tests

| File | Purpose |
|---|---|
| `oracle_test.py` | 43 hand-written boundary cases, 9 600 random requests checked against independent brute-force oracles/validators, repeated-batch state-reset check, and large tests on the full published domains (LCS 1000x1000, merge n=200, tree n=100000, KMP 200000/100000, RK 10000x2000, suffix n=50000, Aho-Corasick with dense matches). |
| `Bench.java` | Reproducible naive / KMP / Rabin-Karp comparison used in the "Search comparison" section of `ANALYSIS.md`. |

Run from the repository root:

```
python tools/run.py --setup
python tests/student/oracle_test.py            # add --quick to skip the large tests, --table for the Markdown table
javac --release 17 -encoding UTF-8 -d tests/student/build Java/source/*.java tests/student/Bench.java
java -Xmx384m -cp tests/student/build Bench
```

`ANALYSIS.md` explains what defect each case detects.
