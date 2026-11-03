# BRAM-ring Prefetch32

Prefetch32 computed **933.6 hashes/s** on an Intel Core i7-12700KF. The reference miner computed **825.4 hashes/s** on the same machine. That is **13.11% faster** across five runs per implementation under the [BRAM-ring CPU bounty protocol](BOUNTY.md).

| Implementation | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Mean (H/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Reference | 824 | 814 | 831 | 825 | 833 | 825.4 |
| Prefetch32 | 941 | 924 | 931 | 937 | 935 | 933.6 |

## Why it runs faster

Each lane knows which memory address it needs before it needs the value. Prefetch32 requests that cache line, then finishes the read and write 32 lane positions later. Each lane owns its bank, so the other lanes cannot change the word it is waiting for. The final 32 accesses finish before the next ring step starts.

The implementation also separates the fill and run loops and evaluates the cell rules in algebraic normal form. The timed path computes the full SHA-256 digest for every nonce. [Contestant source](cpu/verify_prefetch32.c) Â· [Implementation and protocol](SUBMISSION.md)

## Reproduce

On Linux with GCC, OpenMP, Python 3, Make, AVX2 and BMI2, run from the repository root:

```bash
set -euo pipefail
make
cpu/verify_prefetch32 vectors | python3 host/check_vectors.py
```

The expected result is `PASS: 8/8 vectors bit-exact on every column (digest, fold, state)`. To reproduce the timing on the reference i7-12700KF with the organizer's eight P-core CPU IDs:

```bash
OMP_NUM_THREADS=8 taskset -c 0,2,4,6,8,10,12,14 cpu/verify_avx2
OMP_NUM_THREADS=8 taskset -c 0,2,4,6,8,10,12,14 cpu/verify_prefetch32
```

Compare the two `CPU 8 cores` lines. The [run logs](evidence/replay/) contain the five pairs above, the fresh-seed check and the build records. On another machine, check its CPU numbering before using the affinity mask.

BRAM-ring was created by Peter Rizun. [Original project](https://git.nodelabs.ca/nexapow/bram-ring) Â· [Upstream README](UPSTREAM.md) Â· [Upstream license](LICENSE) Â· [Contestant license](CONTESTANT-LICENSE.txt)
