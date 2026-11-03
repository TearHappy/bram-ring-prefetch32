# Evidence

## `replay/`: clean replay of the frozen package on an idle i7-12700KF (run `r3-20261103T085541Z`)

The benchmark ran on an Intel Core i7-12700KF with Ubuntu 24.04 and GCC 13.3. The CPU quota was 19.2 cores out of 20. Host-wide CPU activity measured 0.000 over the five seconds before the timing check. The [timing driver](replay/bench3.py) alternates which executable runs first.

Checks, in order, all retained as raw files:

1. `frozen-check.txt`: `spec.py`, `generate.py`, `vectors.txt` match BOUNTY.md's three SHA-256 lines.
2. `make.log`, `generated-diff.txt`: `make` regenerated `cpu/tables.h`, `vectors.txt` and `fpga/ring.v` from `spec.py`; the regenerated files are byte-identical to the published ones.
3. `gate-summary.txt`: pre-registered host gate (champion under the organizer's literal command must reach 780 H/s). Also records that OpenMP binding changes nothing on an idle host:
   `literal verify_avx2: CPU 8 cores (verify_avx2): 832 hashes/s` / `bound verify_avx2: CPU 8 cores (verify_avx2): 832 hashes/s` and `literal verify_prefetch32: CPU 8 cores (verify_prefetch32): 941 hashes/s` / `bound verify_prefetch32: CPU 8 cores (verify_prefetch32): 940 hashes/s`.
4. `check_vectors-pipe.txt`: `cpu/verify_prefetch32 vectors | python3 host/check_vectors.py` passes.
5. `make-prove-epoch0.log` (exit `0`): `make prove` holds the contestant to the golden vectors beside the shipped implementations.
6. `timed-*-*.stdout`: the benchmark below.
7. `negative-control-*`: a copy of the checkout whose contestant prints valid rows and then exits 1 makes `make prove` fail (exit `2`), while the rows themselves pass the checker (`negative-control-rows-check.txt`).
8. `make-prove-seed.log`, `seed-*`: `BRAM_EPOCH=706cb9b4c05e30cef6f6f0dd73df5e47 make prove` in the same checkout without `make clean` regenerated every derived file, rebuilt both binaries (`seed-switch-summary.txt`), and the contestant's eight rows equal the regenerated vectors on all four columns.
9. `z3-transcript.txt` (Z3 version 4.8.12 - 64 bit): `bank-order.smt2` returns `unsat` for the commutation of read-modify-writes on distinct banks (old words included) and `sat` for the same-bank negative control.

### Benchmark: BOUNTY.md "How I measure", both executables, back to back

Commands, run from the checkout root on CPUs 0,2,4,6,8,10,12,14 (the eight physical P-cores, `cpus.txt`, validated against `lscpu-e.txt`):

    OMP_NUM_THREADS=8 taskset -c 0,2,4,6,8,10,12,14 cpu/verify_avx2
    OMP_NUM_THREADS=8 taskset -c 0,2,4,6,8,10,12,14 cpu/verify_prefetch32

800 nonces per run; the champion's line times `hash_state` only (as shipped), the contestant's line times fill, run and the full SHA-256 digest of every nonce and prints the XOR-fold of the 800 digests afterwards (identical in every run: `1dba7f5670aad7c4...`).

| pair | order | champion H/s | contestant H/s | ratio |
|---|---|---|---|---|
| 0 | champion first | 824 | 941 | 1.1420 |
| 1 | contestant first | 814 | 924 | 1.1351 |
| 2 | champion first | 831 | 931 | 1.1203 |
| 3 | contestant first | 825 | 937 | 1.1358 |
| 4 | champion first | 833 | 935 | 1.1224 |

| | champion | contestant |
|---|---|---|
| arithmetic mean of 5 runs | 825.4 | 933.6 |

Ratio of means, all pairs: **1.1311** (+13.11%). Bar: 1.10. Within-2%-of-bar rule: not triggered.
Sensitivity (decides nothing): every pair is quiet under the rule in `benchmark.json`; median pair ratio 1.1351, minimum 1.1203, maximum 1.1420.

Bindings: contestant source `3ae9a6801ab120d1dae8c6523c30700561593ae252445d175bdd5ef196d281ec`, champion source `cef9169590a4b81201879ce92959b155b3e7c3fbf6ec20372e45e9f98ceed05b`,
binaries `a8abc592390966f1797e39bf5f0b02ec33b79e9b804332f29c219f2674f763d2` (contestant) and `c706a415b82fb4b1140f2dfedea42013c980601a18138c6447318d29042b87e8` (champion),
flags `-O3 -march=native -fopenmp` (`compiler-flags.txt`), topology `lscpu.txt`, microcode `processor.txt`.

## `gated-hosts/`: two hosts below the baseline threshold

Their champion runs measured 594, 636 H/s under the literal command (quota 9.6 cores, co-tenants present); the paired comparison did not run there.

## `replay-loaded-host/`: the full protocol on a loaded 12700KF host (run `r3-20261103T083139Z`)

Same package, same checks 1, 2, 4, 5, 7, 8, 9, all passed (that run predates the gate). Its host was loaded by
co-tenants: champion 497 to 760 H/s over 20 pairs (the 2% rule fired), contestant
572 to 843 H/s, ratio of means 1.1135 with every pair retained. It is kept as a record, not as the measurement.

## `prior/`: measurements of the previous source revision

See `prior/NOTES.md`: the digest-inclusive wrapper comparisons and ablations made before the package was
frozen, bound to the earlier source hash, with the source diff to this package.
