"""Post-run audit. Never supplies features or reports to the collector."""
import argparse
import collections
import csv
import hashlib
import json
import math
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--config', type=Path, required=True)
p.add_argument('--run', type=Path, required=True)
a = p.parse_args()
c = json.loads(a.config.read_text())
run = a.run
checks, details = {}, {}

def rows(name):
    with (run/name).open(newline='') as f:
        return list(csv.DictReader(f))

def check(name, condition, detail=None):
    checks[name] = 'PASS' if condition else 'FAIL'
    if detail is not None:
        details[name] = detail

def close(x, y):
    return abs(float(x)-float(y)) < 1e-8

nodes = rows('nodes.csv')
links = rows('links.csv')
adj = {n['name']: [] for n in nodes}
peer = {}
for x in links:
    adj[x['a']].append(x['b'])
    adj[x['b']].append(x['a'])
    peer[x['a'], x['a_face']] = x['b']
    peer[x['b'], x['b_face']] = x['a']
expected_links = {frozenset(x) for x in c['links']}

def path(start, end):
    todo = [(start, [start])]
    seen = set()
    while todo:
        n, pp = todo.pop(0)
        if n == end:
            return pp
        seen.add(n)
        todo.extend((v, pp+[v]) for v in adj[n] if v not in seen)
    return []

check('topology', len(nodes) == 17 and len(links) == 16 and
      {frozenset((x['a'], x['b'])) for x in links} == expected_links and
      all(path('M', n) for n in adj) and
      {x['name'] for x in nodes if x['role'] == 'router'} == set(c['routers']))
def numeric_unit(value, units):
    m = re.fullmatch(r'([0-9.]+)([A-Za-z]+)',value)
    return float(m[1])*units[m[2]]
expected_bps = numeric_unit(c['bandwidth'],{'bps':1,'Kbps':1e3,'Mbps':1e6,'Gbps':1e9})
expected_delay = numeric_unit(c['delay'],{'s':1,'ms':1e-3,'us':1e-6})
check('effective_link_parameters', all(float(x['a_bps']) == expected_bps and float(x['b_bps']) == expected_bps
      and close(x['delay_s'],expected_delay) and x['a_queue'] == c['queue'] and x['b_queue'] == c['queue'] for x in links))
cache_limits = rows('cache-limits.csv')
check('effective_cache_disabled',len(cache_limits) == 17 and all(int(x['packet_limit']) == 0 for x in cache_limits))
packets = rows('audit-packets.csv')
byname = collections.defaultdict(list)
for x in packets:
    byname[x['name']].append(x)

def route_ok(name, start, end):
    pp = path(start, end)
    expected_i = list(zip(pp, pp[1:]))
    expected_d = [(y, x) for x, y in reversed(expected_i)]
    trace = byname[name]
    def network_events(event):
        return [(x['node'], peer[x['node'], x['face']]) for x in trace
                if x['event'] == event and (x['node'], x['face']) in peer]
    # Outgoing trace follows packet traversal order. Incoming checks prove reception.
    return (network_events('outI') == expected_i and
            network_events('inI') == [(y, x) for x, y in expected_i] and
            network_events('outD') == expected_d and
            network_events('inD') == [(y, x) for x, y in expected_d])

consumer_details, benign_route_checks = {}, []
producer = rows('producer.csv')
producer_names = collections.Counter(x['name'] for x in producer if x['event'] == 'reply')
duration = c['consumer_stop_s']-c['consumer_start_s']
expected_count = int(math.ceil(duration*c['consumer_frequency_hz']-1e-8))
for node in ['C1', 'C2', 'C3']:
    events = rows(f'client-{node}.csv')
    counts = collections.Counter(x['event'] for x in events)
    req = [x for x in events if x['event'] == 'request']
    dat = [x for x in events if x['event'] == 'data']
    names = [x['name'] for x in req]
    check(f'benign_{node}', counts == {'request': expected_count, 'data': expected_count}
          and collections.Counter(names) == collections.Counter(x['name'] for x in dat)
          and all(producer_names[n] == 1 for n in names))
    cadence = all(close(float(x['time']), c['consumer_start_s']+i/c['consumer_frequency_hz']) for i, x in enumerate(req))
    check(f'consumer_cadence_{node}', cadence)
    benign_route_checks.extend(route_ok(n, node, 'P') for n in names)
    consumer_details[node] = {'events': dict(counts), 'rate_per_active_second': len(req)/duration,
                              'delivered_payload_bytes': sum(int(x['detail']) for x in dat)}
check('benign_packet_paths_to_and_from_P', all(benign_route_checks) and len(benign_route_checks) == 3*expected_count)
check('producer_reply_count', sum(producer_names.values()) == 3*expected_count)

collector = rows('client-M.csv')
received = rows('collector-received.csv')
collector_counts = collections.Counter(x['event'] for x in collector)
total = 10*c['report_windows']
expected_names = {f"/report/{c['runId']}/R{r}/{s}" for r in range(1,11) for s in range(1,c['report_windows']+1)}
check('all_reports_received_once', len(received) == total and
      {x['name'] for x in received} == expected_names and
      collector_counts == {'request': total, 'data': total}, dict(collector_counts))
check('report_packet_paths', all(route_ok(n,'M',n.split('/')[-2]) for n in expected_names))
report_details, all_samples, integrity, temporal, counter_match = {}, {}, [], [], []
fields = ['in_interests', 'out_interests', 'in_data', 'out_data', 'in_nacks', 'out_nacks',
          'satisfied_interests', 'unsatisfied_interests', 'cs_hits', 'cs_misses']
event_fields = ['inI','outI','inD','outD','inN','outN']
for r in range(1,11):
    router = f'R{r}'
    agent = rows(f'agent-{router}.csv')
    samples = [x for x in agent if x['event'] == 'sample']
    replies = [x for x in agent if x['event'] == 'reply']
    check(f'agent_cadence_{router}', len(samples) == c['report_windows'] and
          all(close(x['time'], (i+1)*c['report_interval_s']) for i,x in enumerate(samples)) and
          len(replies) == c['report_windows'] and len(agent) == 2*c['report_windows'])
    boundaries = [i for i,x in enumerate(packets) if x['node'] == router and x['event'] == 'sampleBoundary']
    check(f'audit_boundaries_{router}', len(boundaries) == c['report_windows']+1)
    for index, sample in enumerate(samples):
        all_samples[sample['name']] = sample['detail']
        v = sample['detail'].split(';')
        observed = collections.Counter(x['event'] for x in packets[boundaries[index]+1:boundaries[index+1]]
                                       if x['node'] == router)
        # Boundary markers preserve event ordering even for equal timestamps.
        counter_match.append(all(int(v[5+i]) == observed[k] for i,k in enumerate(event_fields)))
    entries = [x for x in received if x['name'].split('/')[-2] == router]
    rtts = [float(x['arrival'])-float(x['request']) for x in entries]
    ages = [float(x['arrival'])-float(x['payload'].split(';')[3]) for x in entries]
    report_details[router] = {'received':len(entries), 'sample_cadence_s':c['report_interval_s'],
                              'rtt_min_s':min(rtts) if rtts else None, 'rtt_max_s':max(rtts) if rtts else None,
                              'window_end_to_arrival_max_s':max(ages) if ages else None}
for x in received:
    v = x['payload'].split(';')
    integrity.append(x['payload'] == all_samples.get(x['name']) and x['name'].endswith('/'+v[0]+'/'+v[1]))
    request, arrival, end, ready = float(x['request']), float(x['arrival']), float(v[3]), float(v[4])
    expected_status = 'on_time' if arrival <= end+c['report_deadline_s'] else 'late'
    temporal.append(end <= ready <= request <= arrival and x['status'] == expected_status)
check('received_payload_matches_immutable_sample', len(integrity) == total and all(integrity))
check('report_timestamp_order_and_status', len(temporal) == total and all(temporal))
check('counter_deltas_match_independent_packet_trace', len(counter_match) == total and all(counter_match))
check('cache_hits_zero', all(int(v.split(';')[13]) == 0 for v in all_samples.values()) and c['cs_packets'] == 0)
check('attackers_inactive', not any(x['node'] in ['A1','A2'] and
      (x['name'].startswith('/benign/') or x['name'].startswith('/report/')) for x in packets))
check('no_workload_nacks', not any(x['event'] in ['inN','outN'] and
      x['name'].startswith(('/benign/','/report/')) for x in packets))
summary = {'status':'PASS' if all(x == 'PASS' for x in checks.values()) else 'FAIL',
           'run_id':c['runId'], 'checks':checks,'details':details,'consumers':consumer_details,
           'collector_status_counts':dict(collections.Counter(x['status'] for x in received)),
           'reports':report_details,'report_counter_fields_in_order':fields,
           'report_network_transmission_bytes_ndn_layer':sum(int(x['ndn_wire_bytes']) for x in packets
               if x['event'] in ['outI','outD'] and x['name'].startswith('/report/') and (x['node'],x['face']) in peer),
           'pit_field':'final payload field; instantaneous entries at window end, not a rate',
           'scope':'benign pilot only; no flooding, report impairment, final dataset or ML'}
(run/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
manifest = {str(f.relative_to(run)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(run.iterdir()) if f.is_file() and f.name != 'sha256.json'}
(run/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(0 if summary['status'] == 'PASS' else 1)
