"""The organizer's measurement, literally: OMP_NUM_THREADS=8 taskset -c <P-cores> <binary>,
champion and contestant back to back, five pairs with alternating order (twenty when the
five-pair ratio lands within 2% of the 1.10 bar), arithmetic means. Every pair is retained
in the primary result; sensitivity views are reported separately and decide nothing."""
import json, os, re, statistics, subprocess, sys, time, hashlib
cpus, E = sys.argv[1], sys.argv[2]
bins = ['cpu/verify_avx2', 'cpu/verify_prefetch32']
env = {**os.environ, 'OMP_NUM_THREADS': '8'}
pat = re.compile(r'^CPU 8 cores \((verify_avx2|verify_prefetch32)\): ([0-9.]+) hashes/s', re.M)
fold = re.compile(r'^  digest xor-fold over 800 timed nonces: ([0-9a-f]{64})$', re.M)
rates = [[], []]; runs = []; folds = set()

def one(i, j, order):
    cmd = ['taskset', '-c', cpus, bins[j]]
    t = time.time()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    open(f'{E}/timed-{i}-{j}.stdout', 'w').write(p.stdout)
    open(f'{E}/timed-{i}-{j}.stderr', 'w').write(p.stderr)
    assert p.returncode == 0, (i, j, p.returncode)
    assert '8/8 golden vectors bit-exact' in p.stdout, (i, j)
    m = pat.search(p.stdout)
    assert m and m.group(1) == ('verify_avx2', 'verify_prefetch32')[j], (i, j, p.stdout[-300:])
    r = float(m.group(2))
    if j == 1:
        f = fold.search(p.stdout); assert f, p.stdout[-300:]; folds.add(f.group(1))
    rates[j].append(r)
    runs.append(dict(pair=i, binary=bins[j], order=order, command='OMP_NUM_THREADS=8 ' + ' '.join(cmd),
                     rate_hashes_per_s=r, wall_seconds=round(time.time() - t, 3), started_utc=t))

trials = 5; i = 0
while i < trials:
    order = 'champion-first' if i % 2 == 0 else 'contestant-first'
    for j in ([0, 1] if i % 2 == 0 else [1, 0]): one(i, j, order)
    i += 1
    if i == 5:
        ratio5 = statistics.mean(rates[1]) / statistics.mean(rates[0])
        if abs(ratio5 - 1.10) <= 1.10 * 0.02: trials = 20

means = [statistics.mean(r) for r in rates]
pair_ratios = [c / b for b, c in zip(rates[0], rates[1])]
# Sensitivity views, stated in advance, reported separately: they decide nothing.
quiet = [k for k in range(len(rates[0])) if rates[0][k] >= 0.95 * max(rates[0]) and rates[1][k] >= 0.95 * max(rates[1])]
sens = {
    'rule': 'a pair is quiet when both rates are within 5% of their column maximum; the quiet-pairs ratio is shown beside the all-pairs ratio and decides nothing',
    'quiet_pairs': quiet,
    'quiet_pairs_ratio': (statistics.mean(rates[1][k] for k in quiet) / statistics.mean(rates[0][k] for k in quiet)) if quiet else None,
    'median_pair_ratio': statistics.median(pair_ratios),
    'min_pair_ratio': min(pair_ratios), 'max_pair_ratio': max(pair_ratios),
}
doc = dict(
    protocol='BOUNTY.md How I measure: OMP_NUM_THREADS=8 taskset -c <eight P-cores> <binary>; CPU 8 cores line; 800 nonces per run; five runs each, arithmetic mean; twenty runs when within 2% of the bar; alternating order',
    cpus=cpus, pairs=trials, rates=dict(champion=rates[0], contestant=rates[1]), means=dict(champion=means[0], contestant=means[1]),
    ratio_all_pairs=means[1] / means[0], gain_percent_all_pairs=100 * (means[1] / means[0] - 1),
    bar_ratio=1.10, clears_bar_all_pairs=means[1] / means[0] >= 1.10,
    pair_ratios=pair_ratios, sensitivity=sens, runs=runs,
    contestant_digest_xor_fold_800_nonces=sorted(folds), contestant_fold_constant_across_runs=len(folds) == 1,
    binary_sha256={b: hashlib.sha256(open(b, 'rb').read()).hexdigest() for b in bins},
)
json.dump(doc, open(f'{E}/benchmark.json', 'w'), indent=2)
print(json.dumps({k: doc[k] for k in ('means', 'ratio_all_pairs', 'gain_percent_all_pairs', 'pairs', 'sensitivity', 'contestant_fold_constant_across_runs')}, indent=1))
