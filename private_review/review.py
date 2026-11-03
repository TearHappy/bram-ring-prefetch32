#!/usr/bin/env python3
"""Private clean-copy review: official vectors plus digest-inclusive paired measurements."""
import argparse,hashlib,json,os,pathlib,re,shutil,statistics,subprocess,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import judge

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--seed',default='epoch0');p.add_argument('--benchmark',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--cpus',default='0,2,4,6,8,10,12,14');p.add_argument('--count',type=int,default=800);a=p.parse_args()
 if a.smoke and a.benchmark:raise ValueError('smoke and benchmark are separate modes')
 if a.count<800:raise ValueError('benchmark count must be at least800')
 out=a.out.resolve()
 if out.exists() or out==ROOT or ROOT.parent in out.parents:raise ValueError('use a new output directory outside release-draft')
 manifest=json.loads((ROOT/'MANIFEST.json').read_text())
 for name,expected in manifest.items():
  if judge.sha(ROOT/name)!=expected:raise ValueError('package hash mismatch: '+name)
 out.mkdir(parents=True);summary={'status':'RUNNING','seed':a.seed,'official_award_decision':False}
 def run(cmd,label,cwd=None,env=None):
  r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,text=True,capture_output=True)
  (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
  (out/(label+'.command.json')).write_text(json.dumps({'argv':list(map(str,cmd)),'cwd':str(cwd),'returncode':r.returncode},indent=2))
  if r.returncode:raise RuntimeError(label+' failed')
  return r
 try:
  ref=out/'reference';shutil.copytree(ROOT.parent,ref)
  for n,h in judge.FROZEN.items():
   if judge.sha(ref/n)!=h:raise ValueError('frozen mismatch '+n)
  env=os.environ.copy();env.update(BRAM_EPOCH=a.seed,OMP_NUM_THREADS='1' if a.smoke or not a.benchmark else '8',OMP_DYNAMIC='FALSE',OMP_PLACES='cores',OMP_PROC_BIND='TRUE')
  if a.seed!='epoch0':run([sys.executable,'generate.py'],'seed-generation',ref,env)
  expected=judge.rows((ref/'vectors.txt').read_text())
  if len(expected)!=8:raise ValueError('eight official nonce rows required')
  src=ROOT.parent/'cpu/verify_prefetch32.c'
  run(['gcc','--version'],'compiler')
  run(['gcc','-O3','-march=native','-fopenmp','-I',ref/'cpu',src,ref/'cpu/sha256.c','-o',out/'candidate-native'],'build-native')
  actual=run([out/'candidate-native','vectors'],'candidate-vectors',ref,env).stdout
  judge.exact(judge.rows(actual),expected)
  run([sys.executable,ref/'host/check_vectors.py',out/'candidate-vectors.stdout',ref/'vectors.txt'],'official-checker',ref,env)
  summary['official_vectors']='PASS: exact eight-row membership, digest, fold and full state; official checker passed'
  bins=[]
  for name,source in [('baseline',ref/'cpu/verify_avx2.c'),('candidate',src)]:
   build=out/name;build.mkdir();shutil.copyfile(source,build/'submission.c')
   for f in ['tables.h','sha256.h','sha256.c']:shutil.copyfile(ref/'cpu'/f,build/f)
   shutil.copyfile(ROOT/'tools/wrapper.c',build/'wrapper.c')
   run(['gcc','-O3','-march=native','-fopenmp',build/'wrapper.c',build/'sha256.c','-o',build/'runner'],'build-'+name)
   bins.append(build/'runner')
  cpus=[int(v) for v in a.cpus.split(',')]
  if a.benchmark and (len(cpus)!=8 or len(set(cpus))!=8):raise ValueError('benchmark requires eight distinct P-core CPU IDs')
  count=a.count if a.benchmark else 1;rates=[[],[]]
  run(['lscpu','-J'],'lscpu')
  trials=5 if a.benchmark else 1;i=0
  while i<trials:
   pair={}
   for j in ([0,1] if i%2==0 else [1,0]):
    cmd=[bins[j],format(0x123456789000+i*count,'x'),count,'1']
    if a.benchmark:cmd=['taskset','-c',a.cpus]+cmd
    res=run(cmd,'timed-%d-%d'%(i,j),env=env)
    got=judge.rows(res.stdout)
    if set(got)!={format(0x123456789000+i*count+k,'016x') for k in range(count)}:raise ValueError('timed inventory mismatch')
    sec=re.findall(r'^JUDGE_SECONDS ([0-9.]+)$',res.stderr,re.M)
    if len(sec)!=1 or float(sec[0])<=0:raise ValueError('timing absent or invalid')
    pair[j]=got;rates[j].append(count/float(sec[0]))
   judge.exact(pair[0],pair[1]);i+=1
   if i==5 and a.benchmark:
    ratio=statistics.mean(rates[1])/statistics.mean(rates[0])
    if abs(ratio-1.10)<=1.10*.02:trials=20
  summary.update(status='PASS',mode='paired benchmark' if a.benchmark else 'one-thread clean-copy smoke',count=count,rates=rates,means=list(map(statistics.mean,rates)),ratio=statistics.mean(rates[1])/statistics.mean(rates[0]),source_candidate_sha256=judge.sha(src),fresh_seed_timing_is_official=False if a.seed!='epoch0' else None)
 except BaseException as e:
  summary.update(status='FAILED',error=str(e));raise
 finally:(out/'report.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
