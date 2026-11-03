Supplementary evidence harness for the CPU speed award submission. The award entry point,
build, vector check and fresh-seed commands are in `../SUBMISSION.md`.

`review.py` compiles the unchanged champion `cpu/verify_avx2.c` and the contestant
`cpu/verify_prefetch32.c` into one independent timing wrapper (`tools/wrapper.c`) that performs
the full SHA-256 digest for every timed nonce, retains every digest and full ring state,
compares them between the two implementations, and alternates execution order between pairs.
`MANIFEST.json` binds every file of the checkout and is verified before any run.

From the checkout root on Linux, with a new output directory for each run:

    python3 private_review/review.py --out /tmp/bram-smoke --smoke
    python3 private_review/review.py --out /tmp/bram-full --benchmark --count 800 --cpus 0,2,4,6,8,10,12,14

For a fresh epoch, append `--seed <seed>`. Match the CPU IDs to the eight P-cores of the host.
