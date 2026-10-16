"""Unweighted physical graph analysis. Does not run a simulator or attack."""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

ARCH=Path(__file__).resolve().parents[1]

def analyze():
    filename=ARCH/'ndnsim/config/benign-pilot.json'
    c=json.loads(filename.read_text(encoding='utf-8'))
    nodes=c['routers']+list(c['endpoints'])
    assert len(nodes)==len(set(nodes))==17
    adj={n:[] for n in nodes}
    edges={frozenset(e) for e in c['links']}
    assert len(edges)==len(c['links'])==16
    for x,y in c['links']:
        assert x!=y
        adj[x].append(y); adj[y].append(x)
    def path(start,end):
        queue=deque([[start]]); seen={start}
        while queue:
            pp=queue.popleft()
            if pp[-1]==end: return pp
            for n in adj[pp[-1]]:
                if n not in seen:
                    seen.add(n); queue.append(pp+[n])
        raise AssertionError(f'Disconnected graph: {start}/{end}')
    assert all(path('M',n) for n in nodes)
    assert frozenset(['R5','R6']) not in edges
    placements={}
    for location in c['routers']:
        hops={r:len(path(r,location)) for r in c['routers']} # one collector access edge
        placements[location]={'sum_hops':sum(hops.values()),'mean_hops':sum(hops.values())/10,
                              'max_hops':max(hops.values()),'per_router_hops':hops}
    paths={r:path(r,'M') for r in c['routers']}
    shared=[r for r,pp in paths.items() if ('R8','R10') in list(zip(pp,pp[1:]))]
    min_sum=min(v['sum_hops'] for v in placements.values())
    min_max=min(v['max_hops'] for v in placements.values())
    result={'status':'PASS','evidence_type':'static equal-hop graph analysis, not simulation',
            'config_sha256':hashlib.sha256(filename.read_bytes()).hexdigest(),
            'nodes':len(nodes),'links':len(edges),'connected':True,'acyclic':True,
            'router_diameter_edges':max(len(path(x,y))-1 for x in c['routers'] for y in c['routers']),
            'collector_placement_candidates':placements,
            'minimum_sum_hop_placements':[r for r,v in placements.items() if v['sum_hops']==min_sum],
            'minimum_max_hop_placements':[r for r,v in placements.items() if v['max_hops']==min_max],
            'report_data_paths':paths,'report_data_crossing_R8_to_R10':shared,
            'hypothetical_attack_interest_paths_if_target_P':{r:path(r,'P') for r in ['A1','A2']},
            'note':'A1/A2 applications are inactive. No queue, traffic, congestion, PIT or inference model is used here.'}
    assert result['minimum_max_hop_placements']==['R10']
    assert result['minimum_sum_hop_placements']==['R8'] and len(shared)==6
    assert placements['R10']['mean_hops']==3 and placements['R10']['max_hops']==4
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path); a=p.parse_args()
    text=json.dumps(analyze(),indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(text,encoding='utf-8',newline='\n')
    print(text,end='')
