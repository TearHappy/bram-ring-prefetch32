# BRAM-ring CPU speed award submission

Entry for the [0.01 BTC CPU speed award](BOUNTY.md).

Implementation: [`cpu/verify_prefetch32.c`](cpu/verify_prefetch32.c), derived from the shipped
champion `cpu/verify_avx2.c`, which is left unchanged for back-to-back comparison.

The kernel changes in three places.

- **Bank read-modify-write scheduling.** Lane b's bank address is known as soon as its value
  is computed, the old word it returns is consumed only on the next step, and every lane owns
  its bank. The read-then-write of lane b is therefore deferred by 32 lanes: a prefetch of the
  bank word is issued when lane b is computed, and the read and write execute when lane b+32 is
  processed; the last 32 lanes drain at the end of the step. Operations on distinct banks
  commute, old word included, so every step produces the same ring state.
- **Cell evaluation in algebraic normal form.** The rule-bit masks are Mobius-transformed once
  per epoch; spec.py admits only degree-3 rules, so 15 coefficient masks replace the mux tree.
- **Fill and run as separate loops.** The fill never reads the previous bank word.

The function is unchanged. `spec.py`, `generate.py` and `vectors.txt` are byte-identical to the
published ones. The three lines below are copied from BOUNTY.md, "The frozen function", and
can be checked with `sha256sum -c`:

    5596327c5fc89b4d87eaf64df0b25e8430a9b25247ebae4c3e1037c19cd2f292  spec.py
    20f78b63ff10f7b4fee681355190e91eaaeb527a733d2701d928eb0ac6534dab  generate.py
    d406e2319f21e641dc77fcf79693c88062cc312cd1d75f0c286fa4ba85cf88f1  vectors.txt

License: the contestant additions (`cpu/verify_prefetch32.c`, `private_review/`, this file) are
MIT, see `CONTESTANT-LICENSE.txt`. The upstream `LICENSE` and attribution are unchanged.

## Build (Linux, gcc with OpenMP, AVX2 and BMI2)

    make

builds `cpu/simple`, `cpu/verify_avx2` and `cpu/verify_prefetch32` with the Makefile's
`-O3 -march=native -fopenmp`, regenerating the derived files from `spec.py` first. The direct
equivalent for the contestant alone:

    cc -O3 -march=native -fopenmp -o cpu/verify_prefetch32 cpu/verify_prefetch32.c cpu/sha256.c

## Rule 1: the golden vectors

    cpu/verify_prefetch32 vectors | python3 host/check_vectors.py

prints `PASS: 8/8 vectors bit-exact on every column (digest, fold, state)`. `make prove` holds
`cpu/verify_prefetch32` to the same vectors alongside the shipped implementations, writing its
rows to a file before the check so a failing producer fails the make.

## Fresh epoch seed

In a scratch clone:

    BRAM_EPOCH=<seed> make prove

regenerates every table, vector and kernel for `<seed>` and rebuilds `cpu/verify_prefetch32`
against the regenerated `cpu/tables.h` (the Makefile tracks the seed, so no `make clean` is
needed). Nothing in the contestant depends on the seed being `epoch0`.

## Benchmark entry point (BOUNTY.md, "How I measure")

    OMP_NUM_THREADS=8 taskset -c 0,2,4,6,8,10,12,14 cpu/verify_prefetch32

Read the `CPU 8 cores (verify_prefetch32)` line. The timer covers 800 nonces, each doing the
fill, the run and the full SHA-256 digest of the final state; the one-time table build and the
golden-vector check run before the timer, and the XOR-fold of all 800 digests is printed after
it. The champion for the back-to-back comparison is the unchanged

    OMP_NUM_THREADS=8 taskset -c 0,2,4,6,8,10,12,14 cpu/verify_avx2

On the i7-12700KF the eight P-cores are the even CPUs 0 to 14 (`lscpu -e`).

## Supplementary harness

`private_review/review.py` compiles both implementations into one independent timing wrapper
that performs the full digest for every timed nonce and compares every digest and full state
between the two, alternating execution order. It is evidence tooling, not the entry point above:

    python3 private_review/review.py --out /tmp/bram-smoke --smoke
    python3 private_review/review.py --out /tmp/bram-full --benchmark --count 800 --cpus 0,2,4,6,8,10,12,14

## Evidence

Measurement records from a clean replay of this package on an i7-12700KF are under
`evidence/`: source and binary hashes, compiler identity and flags, CPU topology and affinity,
every timed run's raw output, the seed-switch proof, and the solver transcript for the
bank-ordering lemma.
