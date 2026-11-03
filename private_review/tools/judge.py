#!/usr/bin/env python3
"""Independent Linux acceptance and evidence harness. Does not modify reference."""
import argparse, hashlib, json, os, pathlib, platform, re, secrets, shutil, statistics, subprocess, sys, time
FROZEN={'spec.py':'5596327c5fc89b4d87eaf64df0b25e8430a9b25247ebae4c3e1037c19cd2f292','generate.py':'20f78b63ff10f7b4fee681355190e91eaaeb527a733d2701d928eb0ac6534dab','vectors.txt':'d406e2319f21e641dc77fcf79693c88062cc312cd1d75f0c286fa4ba85cf88f1'}
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def rows(text,full=True):
    out={}
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'): continue
        v=line.split()
        lens=[16,64,8,3840] if full else [16,64]
        if len(v)!=len(lens) or any(not re.fullmatch('[0-9a-f]{%d}'%n,x) for n,x in zip(lens,v)): raise ValueError('malformed row')
        if v[0] in out: raise ValueError('duplicate nonce')
        out[v[0]]=v
    if not out: raise ValueError('empty rows')
    return out
def exact(actual,expected):
    if actual!=expected: raise ValueError('row membership or content mismatch')
def controls():
    good={'0000000000000000':['0000000000000000','a'*64,'12345678','b'*3840]}
    text=' '.join(next(iter(good.values())))
    exact(rows(text),good)
    mutants=['',text+'\n'+text,text.replace('a'*64,'c'*64),text.replace('12345678','87654321'),text.replace('b'*3840,'c'*3840),text.replace('0000000000000000','0000000000000001')]
    for m in mutants:
        try: exact(rows(m),good)
        except ValueError: continue
        raise RuntimeError('negative control admitted')
    return len(mutants)
def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=pathlib.Path,required=True);p.add_argument('--candidate',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--cpus',default='0,2,4,6,8,10,12,14');p.add_argument('--smoke',action='store_true');p.add_argument('--seed',help='optional fresh seed; full generator is slow');p.add_argument('--batch',action='store_true',help='candidate exposes batch8 API');p.add_argument('--cc',default='gcc');a=p.parse_args()
    a.reference=a.reference.resolve();a.candidate=a.candidate.resolve();a.out=a.out.resolve()
    if a.out.exists(): raise ValueError('output must not already exist')
    if a.reference==a.out or a.reference in a.out.parents: raise ValueError('output must be outside reference')
    a.out.mkdir(parents=True)
    report={'status':'RUNNING','official_judgement':False,'unsupported':[],'negative_controls':controls(),'frozen':{},'source_candidate_sha256':sha(a.candidate),'candidate_interface':'batch8' if a.batch else 'hash_state'}
    def run(cmd,label,cwd=None,env=None):
        result=subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,text=True,capture_output=True)
        (a.out/(label+'.stdout')).write_text(result.stdout);(a.out/(label+'.stderr')).write_text(result.stderr)
        (a.out/(label+'.command.json')).write_text(json.dumps({'argv':[str(x) for x in cmd],'returncode':result.returncode,'cwd':str(cwd)},indent=2))
        if result.returncode: raise RuntimeError(label+' failed; see raw evidence')
        return result
    try:
        for name,h in FROZEN.items():
            report['frozen'][name]=sha(a.reference/name)
            if report['frozen'][name]!=h: raise ValueError('frozen hash mismatch: '+name)
        expected=rows((a.reference/'vectors.txt').read_text())
        if len(expected)!=8: raise ValueError('official inventory must contain exactly eight distinct rows')
        if platform.system()!='Linux': raise RuntimeError('Linux required for timed run and affinity')
        cpus=[int(x) for x in a.cpus.split(',')]
        if len(cpus)!=8 or len(set(cpus))!=8: raise ValueError('exactly eight distinct CPUs required')
        topology=run(['lscpu','-J'],'lscpu').stdout
        report['environment']={'platform':platform.platform(),'lscpu':json.loads(topology),'cpus':cpus,'compiler':run([a.cc,'--version'],'compiler').stdout}
        report['unsupported'].append('P-core identity and isolation require manual verification of recorded lscpu topology; eight logical CPU IDs alone do not establish eight P-cores.')
        env=os.environ.copy();env.update(OMP_NUM_THREADS='8',OMP_DYNAMIC='FALSE',OMP_PROC_BIND='TRUE',OMP_PLACES='cores')
        def build(root,src,label,corrupt=False,batch=False):
            d=a.out/label;d.mkdir();shutil.copyfile(src,d/'submission.c')
            for f in ('tables.h','sha256.h','sha256.c'): shutil.copyfile(root/'cpu'/f,d/f)
            shutil.copyfile(pathlib.Path(__file__).with_name('wrapper_batch.c' if batch else 'wrapper.c'),d/'wrapper.c')
            if batch: shutil.copyfile(src.with_name('batch8.h'),d/'batch8.h')
            run([a.cc,'-O3','-march=native','-fopenmp']+(['-DJUDGE_CORRUPT_CELL'] if corrupt else [])+['-o',d/'runner',d/'wrapper.c',d/'sha256.c'],label+'-build')
            report.setdefault('build_inputs',{})[label]={f.name:sha(f) for f in d.iterdir() if f.is_file()}
            return d/'runner'
        def execute(binary,start,count,full,label):
            if not (0<=start<=2**64-1 and count>=1 and start+count-1<=2**64-1): raise ValueError('nonce range exceeds uint64')
            result=run(['taskset','-c',a.cpus,binary,format(start,'x'),count,int(full)],label,env=env)
            data=rows(result.stdout,full);wanted={format(start+i,'016x') for i in range(count)}
            if set(data)!=wanted: raise ValueError('executed nonce inventory mismatch')
            matches=re.findall(r'^JUDGE_SECONDS ([0-9.]+)$',result.stderr,re.M)
            if len(matches)!=1 or float(matches[0])<=0: raise ValueError('missing or invalid timing')
            return data,float(matches[0])
        def checks(root,expect,prefix):
            bins=[build(root,a.reference/'cpu/verify_avx2.c',prefix+'baseline'),build(root,a.candidate,prefix+'candidate',batch=a.batch)]
            for j,b in enumerate(bins):
                observed={}
                for i,n in enumerate(expect): observed.update(execute(b,int(n,16),1,True,prefix+str(j)+'-vector'+str(i))[0])
                exact(observed,expect)
            unseen=secrets.randbits(64)-8
            if unseen<0: unseen=123456789
            x=execute(bins[0],unseen,2,True,prefix+'unseen-baseline')[0];y=execute(bins[1],unseen,2,True,prefix+'unseen-candidate')[0];exact(y,x)
            if a.batch:
                for start,count in ((0,7),(0xfffffffd,9),(0x8000000000000000,15),(0xfffffffffffffff8,8)):
                    x=execute(bins[0],start,count,True,prefix+'boundary-baseline-'+str(start))[0]
                    y=execute(bins[1],start,count,True,prefix+'boundary-candidate-'+str(start))[0]
                    exact(y,x)
            return bins
        mutant=build(a.reference,a.reference/'cpu/verify_avx2.c','corrupt-cell-negative-control',True)
        first=next(iter(expected))
        bad=execute(mutant,int(first,16),1,True,'corrupt-cell-execution')[0]
        try: exact(bad,{first:expected[first]})
        except ValueError: report['compiled_negative_control']='PASS: corrupt cell rejected by official vector oracle'
        else: raise RuntimeError('compiled corrupt-cell negative control admitted')
        bins=checks(a.reference,expected,'epoch0-')
        report['correctness']='eight official rows and two fresh random nonces matched; random comparison uses baseline as oracle'
        count=8 if a.smoke else 800; rates=[[],[]];runs=1 if a.smoke else 5
        for i in range(runs):
            pair=[]
            for j in range(2):
                data,seconds=execute(bins[j],1000000,count,True,'timed-%d-%d'%(i,j));pair.append(data);rates[j].append(count/seconds)
            exact(pair[1],pair[0])
        means=list(map(statistics.mean,rates));report.update(rates=rates,means=means,ratio=means[1]/means[0],timed_nonce_count=count)
        if not a.smoke and abs(means[1]/means[0]-1.10)<=1.10*.02:
            for i in range(5,20):
                pair=[]
                for j in range(2):
                    data,seconds=execute(bins[j],1000000,count,True,'timed-%d-%d'%(i,j));pair.append(data);rates[j].append(count/seconds)
                exact(pair[1],pair[0])
            means=list(map(statistics.mean,rates));report.update(means=means,ratio=means[1]/means[0])
        if a.seed:
            scratch=a.out/'fresh-seed';shutil.copytree(a.reference,scratch)
            seedenv=env.copy();seedenv['BRAM_EPOCH']=a.seed
            run([sys.executable,'generate.py'],'seed-generation',cwd=scratch,env=seedenv)
            fresh=rows((scratch/'vectors.txt').read_text())
            if len(fresh)!=8: raise ValueError('fresh-seed inventory incomplete')
            checks(scratch,fresh,'fresh-');report['seed_test']={'seed':a.seed,'status':'PASS'}
        else: report['unsupported'].append('Fresh-seed portability untested; rerun with --seed and an unpredictable seed.')
        report['status']='SMOKE_PASS' if a.smoke else 'LOCAL_PROTOCOL_COMPLETE'
        if a.smoke: report['unsupported'].append('Smoke timing is not the official 800-nonce five-run protocol.')
        report['unsupported'].append('Organizer judgement, current champion, reference-machine equivalence, price evidence, and award eligibility are not established by this harness.')
    except BaseException as error:
        report['status']='FAILED';report['error']=str(error)
        raise
    finally:
        (a.out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
