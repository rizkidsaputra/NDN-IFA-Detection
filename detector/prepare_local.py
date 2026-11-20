"""Build a new, predeclared experiment; never write to old experiment files."""
from pathlib import Path
import json, hashlib, random, shutil, zipfile
R=Path(__file__).resolve().parent
OLD=R.parent/'online-20261024'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):
    with p.open('x',encoding='utf-8') as f: json.dump(x,f,indent=2,allow_nan=False)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['detector.py','verify.py','extra_audit.py','rq1-online-tree.cc','registry.json']:
    text=(OLD/name).read_text(encoding='utf-8')
    if name=='extra_audit.py': text=text.replace("len(receipt['completed'])==80","len(receipt['completed'])==len(read(R/'plan.json'))")
    (R/name).write_text(text,encoding='utf-8')
text=(OLD/'runner.py').read_text(encoding='utf-8')
text=text.replace("items=[next(x for x in plan if x['kind']=='histgb' and x['rate']==1500 and x['scenario']=='s3' and x['policy']=='priority')] if mode=='smoke' else plan", "items=[next(x for x in plan if x['stage']=='diagnostic' and not x['burst_enabled'] and x['kind']=='histgb' and x['scenario']=='s3' and x['policy']=='priority'),next(x for x in plan if x['stage']=='fresh' and x['rate']==200 and x['kind']=='rf' and x['scenario']=='s2' and x['policy']=='fifo')] if mode=='smoke' else plan")
(R/'runner.py').write_text(text,encoding='utf-8')
registry=read(R/'registry.json');kinds=[x['kind'] for x in registry['models']]
base=read(R.parent/'confirmation-20261024/reference/template.json')
(R/'config').mkdir()
plan=[];families=[];contracts=[]
def add(meta,configs):
    families.append(meta)
    for scenario in ['s2','s3']:
        for policy in ['fifo','priority']:
            c=configs(scenario,policy);case=meta['family']+'-'+scenario+'-'+policy
            save(R/'config'/(case+'.json'),c)
            order=kinds.copy();random.Random(meta['seed']+len(plan)).shuffle(order)
            for kind in order:plan.append(dict(meta,case=case,label=case+'-'+kind,kind=kind,scenario=scenario,policy=policy))
original=next(x for x in read(OLD/'families.json') if x['rate']==1500)
for enabled in [True,False]:
    meta=dict(original,stage='diagnostic',burst_enabled=enabled,family='diag261024-b'+str(int(enabled)))
    def config(scenario,policy,meta=meta):
        c=read(OLD/'config'/(original['family']+'-'+scenario+'-'+policy+'.json'))
        if not meta['burst_enabled']:c['extra_flows']=[x for x in c['extra_flows'] if x['id']!='B1']
        return c
    add(meta,config)
for scenario in ['s2','s3']:
    for policy in ['fifo','priority']:
        a=read(R/'config'/('diag261024-b1-'+scenario+'-'+policy+'.json'));b=read(R/'config'/('diag261024-b0-'+scenario+'-'+policy+'.json'))
        a['extra_flows']=[x for x in a['extra_flows'] if x['id']!='B1'];assert a==b
        contracts.append(dict(scenario=scenario,policy=policy,only_burst_flow_diff=True))
index=0
for ri,rate in enumerate([100,200,300,1500],1):
    flags=[True,True,False,False];random.Random(103249000+ri).shuffle(flags)
    for draw in range(1,5):
        index+=1;seed=103240000+index;rng=random.Random(seed)
        onset=rng.randint(8,16);stop=onset+rng.choice([3,5,7]);arate=rng.choice([25,50,100]);node=rng.choice(['A1','A2'])
        bs=rng.randint(3,7);be=bs+rng.randint(14,18);burst=rng.randint(8,18);end=burst+rng.choice([2,4]);br=rng.choice([20,50,100]);bn=rng.choice(['C1','C3'])
        times=[t/1e9 for t in sorted(random.Random(seed+4000000).sample(range(bs*10**9,be*10**9),(be-bs)*rate))]
        meta=dict(stage='fresh',family=f'oc261024-l{ri:02d}-d{draw:02d}',rate=rate,seed=seed,draw=draw,attack_start=onset,attack_stop=stop,attack_rate=arate,attacker=node,background_start=bs,background_stop=be,burst_start=burst,burst_stop=end,burst_rate=br,burst_node=bn,burst_enabled=flags[draw-1])
        def config(scenario,policy,meta=meta,times=times):
            c=json.loads(json.dumps(base));m=meta
            c.update(runId=m['family'],monitor_transport=policy,attackers_active=scenario=='s3',status='fresh online bounded confirmation; frozen detector; no tuning',evaluation_attack_start_s=m['attack_start'],evaluation_attack_stop_s=m['attack_stop'])
            c['extra_flows']=[dict(id='BG1',node='P',kind='background',server_node='R8',frequency_hz=m['rate'],start_s=m['background_start'],stop_s=m['background_stop'],lifetime_s=1,rng_stream=30,background_request_times_s=times)]
            if m['burst_enabled']:c['extra_flows'].append(dict(id='B1',node=m['burst_node'],kind='burst',frequency_hz=m['burst_rate'],start_s=m['burst_start'],stop_s=m['burst_stop'],lifetime_s=1,rng_stream=40))
            if scenario=='s3':c['extra_flows'].append(dict(id='AT',node=m['attacker'],kind='attack',frequency_hz=m['attack_rate'],start_s=m['attack_start'],stop_s=m['attack_stop'],lifetime_s=1,rng_stream=20))
            return c
        add(meta,config)
ordered=[]
for stage in ['diagnostic','fresh']:
    cases=sorted({x['case'] for x in plan if x['stage']==stage});random.Random(103249900+len(ordered)).shuffle(cases)
    for case in cases:ordered.extend(x for x in plan if x['case']==case)
assert len(ordered)==720 and len({x['label'] for x in ordered})==720
save(R/'plan.json',ordered);save(R/'families.json',families)
save(R/'preparation.json',dict(status='PASS',runs=720,decisions=17280,diagnostic_pairs=contracts,config_hashes={p.name:sha(p) for p in (R/'config').glob('*.json')},inherited_hashes={n:sha(OLD/n) for n in ['detector.py','verify.py','runner.py','extra_audit.py','rq1-online-tree.cc','registry.json']},protocol_sha256=sha(R/'PROTOKOL.md')))
print('PREPARED720')
