"""Offline integrity audit and descriptive impact measures, never a detector.

PASS means the experiment/logs obey their contract. Delivery degradation is a
measurement, not an audit failure. All packet paths are checked, including losses.
"""
import argparse
import collections as co
import csv
import hashlib
import json
import math
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--config',required=True,type=Path)
p.add_argument('--run',required=True,type=Path)
a=p.parse_args(); run=a.run; c=json.loads(a.config.read_text())
checks={}; details={}
def check(key,value,detail=None):
    checks[key]='PASS' if value else 'FAIL'
    if detail is not None: details[key]=detail
def rows(file):
    with (run/file).open(newline='') as f: return list(csv.DictReader(f))
def close(x,y,tol=2e-7): return abs(float(x)-float(y))<tol
nodes=rows('nodes.csv'); links=rows('links.csv'); adj=co.defaultdict(list); peer={}
for x in links:
    adj[x['a']].append(x['b']); adj[x['b']].append(x['a'])
    peer[x['a'],x['a_face']]=x['b']; peer[x['b'],x['b_face']]=x['a']
def path(start,end):
    todo=[(start,[start])]; seen={start}
    for n,pp in todo:
        if n==end: return pp
        for v in adj[n]:
            if v not in seen: seen.add(v); todo.append((v,pp+[v]))
    return []
check('topology_17_nodes_16_links_tree',len(nodes)==17 and len(links)==16 and
      {frozenset((x['a'],x['b'])) for x in links}=={frozenset(x) for x in c['links']} and
      all(path('M',n) for n in adj) and {x['name'] for x in nodes if x['role']=='router'}==set(c['routers']))
check('link_parameters_unchanged',c['bandwidth']=='10Mbps' and c['delay']=='2ms' and c['queue']=='100p' and
      all(int(x['a_bps'])==int(x['b_bps'])==10000000 and close(x['delay_s'],.002) and
          x['a_queue']==x['b_queue']=='100p' for x in links))
check('cache_disabled',c['cs_packets']==0 and len(rows('cache-limits.csv'))==17 and
      all(int(x['packet_limit'])==0 for x in rows('cache-limits.csv')))
events=['outI','inI','outD','inD']; ei={k:i for i,k in enumerate(events)}
records={}; flow_metrics={}; paths={}; no_route=co.Counter(); nack_reasons=co.Counter()
def add_client(file,start,end,kind,begin,stop,rate,lifetime):
    logs=rows(file); req=[x for x in logs if x['event']=='request']
    names=[x['name'] for x in req]
    expected=int(math.ceil((stop-begin)*rate-1e-7))
    check(file+'_requests',len(req)==expected and len(set(names))==len(names) and
          all(close(x['time'],begin+i/rate) for i,x in enumerate(req)))
    pp=path(start,end); edges=list(zip(pp,pp[1:])); reverse=[(b,a) for a,b in reversed(edges)]
    paths[start,end]=[edges,[(b,a) for a,b in edges],reverse,[(b,a) for a,b in reverse]]
    for x in req:
        records[x['name']]={'kind':kind,'pair':(start,end),'request':float(x['time']),
            'counts':[0,0,0,0],'data':None,'terminal':None,'lifetime':lifetime}
    valid=True
    for x in logs:
        if x['event']=='request': continue
        r=records.get(x['name'])
        if r is None: valid=False; continue
        if x['event'] not in ('data','timeout','nack') or r['terminal'] is not None: valid=False; continue
        r['terminal']=x['event']
        if x['event']=='data': r['data']=float(x['time'])
        if x['event']=='timeout' and not close(x['time'],r['request']+lifetime): valid=False
    check(file+'_terminal_events',valid and all(records[n]['terminal'] is not None for n in names))
    counts=co.Counter(x['event'] for x in logs)
    rtts=[records[n]['data']-records[n]['request'] for n in names if records[n]['data'] is not None]
    phases={}
    for phase,low,high in [('before',2,5),('during',5,10),('after',10,25)]:
        subset=[records[n] for n in names if low<=records[n]['request']<high]
        prtts=[r['data']-r['request'] for r in subset if r['data'] is not None]
        phases[phase]={'requests':len(subset),'data':sum(r['data'] is not None for r in subset),
                       'rtt_max_s':max(prtts,default=None)}
    flow_metrics[file]={'events':dict(counts),'actual_rate_hz':len(req)/(stop-begin),
        'rtt_max_s':max(rtts,default=None),'by_request_phase':phases}
    return names

benign_names=[]
for node in ['C1','C2','C3']:
    benign_names+=add_client(f'client-{node}.csv',node,'P','benign',c['consumer_start_s'],
                            c['consumer_stop_s'],c['consumer_frequency_hz'],c['interest_lifetime_s'])
for f in c['extra_flows']:
    add_client('flow-'+f['id']+'.csv',f['node'],'P',f['kind'],f['start_s'],f['stop_s'],f['frequency_hz'],f['lifetime_s'])
# Collector poll schedule uses one request per router per window, so audit separately.
collector=rows('client-M.csv'); req=[x for x in collector if x['event']=='request']
expected_report={f"/report/{c['runId']}/R{r}/{s}":(r,s) for s in range(1,c['report_windows']+1) for r in range(1,11)}
check('collector_request_names_and_cadence',len(req)==len(expected_report) and {x['name'] for x in req}==set(expected_report) and
      all(close(x['time'],expected_report[x['name']][1]*c['report_interval_s']+c['report_poll_offset_s']+
                (expected_report[x['name']][0]-1)*.001) for x in req))
for x in req:
    router=x['name'].split('/')[-2]; pp=path('M',router); edges=list(zip(pp,pp[1:])); reverse=[(b,a) for a,b in reversed(edges)]
    paths['M',router]=[edges,[(b,a) for a,b in edges],reverse,[(b,a) for a,b in reverse]]
    records[x['name']]={'kind':'report','pair':('M',router),'request':float(x['time']),
        'counts':[0,0,0,0],'data':None,'terminal':None,'lifetime':c['interest_lifetime_s']}
valid=True
for x in collector:
    if x['event']=='request': continue
    r=records.get(x['name'])
    if r is None or x['event'] not in ('data','timeout','nack') or r['terminal'] is not None: valid=False; continue
    r['terminal']=x['event']
    if x['event']=='data': r['data']=float(x['time'])
    if x['event']=='timeout' and not close(x['time'],r['request']+r['lifetime']): valid=False
check('collector_terminal_events',valid and all(records[n]['terminal'] is not None for n in expected_report))
samples={}; boundary_index=co.Counter(); observed={}; composition=[]; counter_valid=True; boundary_valid=True
agent_reply_counts={}
for router in c['routers']:
    logs=rows('agent-'+router+'.csv'); ss=[x for x in logs if x['event']=='sample']
    check('agent_'+router+'_cadence',len(ss)==c['report_windows'] and all(close(x['time'],(i+1)*c['report_interval_s']) for i,x in enumerate(ss)))
    agent_reply_counts[router]=sum(x['event']=='reply' for x in logs)
    for x in ss: samples[x['name']]=x['detail']
route_errors=[]; unknown_workload=0; all_packet_counts=co.Counter(); wire=co.Counter()
sink_receipts=co.Counter(x['name'] for x in rows('sink.csv') if x['event']=='receive')
producer_receipts=co.Counter(x['name'] for x in rows('producer.csv') if x['event']=='reply')
with (run/'audit-packets.csv').open(newline='') as fp:
    for x in csv.DictReader(fp):
        node=x['node']; event=x['event']; name=x['name']
        family='attack' if name.startswith('/ifa/') else 'benign' if name.startswith('/benign/') else 'report' if name.startswith('/report/') else 'other'
        if event=='sampleBoundary':
            if node in observed:
                sample=samples.get(name)
                if sample is None: boundary_valid=False
                else:
                    v=sample.split(';'); counts=observed[node]
                    if not all(int(v[5+i])==sum(counts[k,f] for f in ['attack','benign','report','other']) for i,k in enumerate(['inI','outI','inD','outD','inN','outN'])):
                        counter_valid=False
                    composition.append({'router':node,'window':boundary_index[node],
                        'counts':{f:{k:counts[k,f] for k in ['inI','outI','inD','outD','inN','outN']} for f in ['attack','benign','report','other']}})
            observed[node]=co.Counter(); boundary_index[node]+=1
            continue
        if node in observed: observed[node][event,family]+=1
        if event in ('inN','outN') and family!='other':
            nack_reasons[family,x['reason']]+=1
            if x['reason']=='150': no_route[family]+=1
        if family=='other': continue
        if name not in records: unknown_workload+=1; continue
        if (node,x['face']) not in peer: continue
        all_packet_counts[family,event]+=1
        if event in ('outI','outD'): wire[family]+=int(x['ndn_wire_bytes'])
        if event not in ei: continue
        r=records[name]; index=ei[event]; expected=paths[r['pair']][index]; pos=r['counts'][index]
        if pos>=len(expected) or expected[pos]!=(node,peer[node,x['face']]):
            if len(route_errors)<20: route_errors.append([name,event,node,peer[node,x['face']],pos])
        r['counts'][index]+=1
check('all_workload_names_known',unknown_workload==0,unknown_workload)
check('packet_paths_valid_order_and_faces',not route_errors,route_errors)
check('no_NoRoute_on_routed_workload',not no_route,dict(no_route))
check('six_counter_deltas_match_full_face_audit',counter_valid)
check('audit_sampling_boundaries',boundary_valid and all(boundary_index[r]==c['report_windows']+1 for r in c['routers']))
check('no_cache_hits',all(int(v.split(';')[13])==0 for v in samples.values()))
delivery_consistent=True; sink_consistent=True; no_attack_response=True
for name,r in records.items():
    n=len(paths[r['pair']][0]); oi,ii,od,id_=r['counts']
    if not (0<=ii<=oi<=n and 0<=id_<=od<=n): delivery_consistent=False
    if r['data'] is not None and r['counts']!=[n,n,n,n]: delivery_consistent=False
    if r['kind']=='attack':
        if sink_receipts[name]!=(1 if ii==n else 0): sink_consistent=False
        if od or id_ or r['data'] is not None: no_attack_response=False
    elif r['kind'] in ('benign','burst'):
        if producer_receipts[name]!=(1 if ii==n else 0): delivery_consistent=False
check('delivered_packets_match_full_paths_and_P_replies',delivery_consistent)
check('attack_sink_receipts_match_full_Interest_path',sink_consistent)
check('attack_unique_names_no_Data',no_attack_response and not any(x['event']=='reply' for x in rows('sink.csv')))
check('attacker_activation_matches_config',c['attackers_active']==any(r['kind']=='attack' for r in records.values()))
received=rows('collector-received.csv'); report_valid=True
for x in received:
    v=x['payload'].split(';'); r=records.get(x['name']); arrival=float(x['arrival']); end=float(v[3])
    if r is None or x['payload']!=samples.get(x['name']) or r['data'] is None or not close(r['data'],arrival): report_valid=False; continue
    if not (end<=float(v[4])<=float(x['request'])<=arrival and close(x['request'],r['request'])): report_valid=False
    if x['status']!=('on_time' if arrival<=end+c['report_deadline_s'] else 'late'): report_valid=False
    if not x['name'].endswith('/'+v[0]+'/'+v[1]): report_valid=False
check('report_payload_and_arrival_only_contract',report_valid and len(received)==len({x['name'] for x in received}) and
      len(received)==sum(r['kind']=='report' and r['data'] is not None for r in records.values()))
pit=rows('pit-probe.csv'); pit_by_node={}
for node in c['routers']+['P']:
    pp=[x for x in pit if x['node']==node]
    check('PIT_probe_'+node+'_cadence',len(pp)==295 and all(close(x['time'],(i+1)*.1) for i,x in enumerate(pp)))
    pit_by_node[node]={'peak_entries':max(int(x['entries']) for x in pp),'final_entries':int(pp[-1]['entries']),
        'peak_during_attack_window':max(int(x['entries']) for x in pp if 5<=float(x['time'])<10)}
drops=rows('queue-drops.csv')
check('queue_drop_records_valid',all(x['from'] in adj and x['to'] in adj[x['from']] and 0<=float(x['time'])<c['duration_s'] and int(x['bytes'])>0 for x in drops))
benign=[records[n] for n in benign_names]; report_records=[r for r in records.values() if r['kind']=='report']
attack=[r for r in records.values() if r['kind']=='attack']
metrics={'benign_requests':len(benign),'benign_data':sum(r['data'] is not None for r in benign),
 'benign_timeouts':sum(r['terminal']=='timeout' for r in benign),
 'benign_rtt_max_s':max((r['data']-r['request'] for r in benign if r['data'] is not None),default=None),
 'report_requests':len(report_records),'report_received':len(received),
 'report_status_counts':dict(co.Counter(x['status'] for x in received)),
 'report_missing':sum(r['data'] is None for r in report_records),
 'report_timeouts':sum(r['terminal']=='timeout' for r in report_records),
 'report_window_to_arrival_max_s':max((float(x['arrival'])-float(x['payload'].split(';')[3]) for x in received),default=None),
 'attack_requests':len(attack),'attack_sink_received':sum(sink_receipts.values()),
 'attack_timeouts':sum(r['terminal']=='timeout' for r in attack),'queue_drops':len(drops),
 'queue_drops_by_direction':dict(co.Counter(x['from']+'->'+x['to'] for x in drops)),
 'pit_by_node':pit_by_node,'network_transmission_bytes_ndn':dict(wire),
 'nack_trace_counts_by_family_reason':{f'{k[0]}:{k[1]}':v for k,v in nack_reasons.items()}}
summary={'status':'PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL','run_id':c['runId'],
 'checks':checks,'details':details,'metrics':metrics,'flows':flow_metrics,
 'scope':'controlled mechanism pilot, no detector/ML; PASS validates integrity, not absence of service impact',
 'limitations':['PIT has no configured finite admission capacity; no CPU/processing bottleneck model.',
 'PIT probe is an offline audit snapshot every 100 ms, not detector input.',
 'Sampling/agent processing instant at simulator event; fixed CBR requests; seeds only change nonces.',
 'Queue trace records actual packet drops, not application-specific loss attribution.',
 'Late/missing report is descriptive; no impairment or mitigation injected.']}
(run/'traffic-composition.json').write_text(json.dumps(composition,indent=2)+'\n')
(run/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
manifest={str(f.relative_to(run)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(run.iterdir())
          if f.is_file() and f.name not in ('sha256.json','validation-stdout.txt')}
(run/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(0 if summary['status']=='PASS' else 1)
