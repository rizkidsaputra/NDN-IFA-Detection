"""Compare replay workload separately from signed local management traffic."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('first',type=Path); p.add_argument('second',type=Path)
p.add_argument('--output',required=True,type=Path); a=p.parse_args()
checks={}
for name in ['scenario.cpp','validator.py','config.json','nodes.csv','links.csv','cache-limits.csv','pit-probe.csv','queue-drops.csv']:
    checks[name]=(a.first/name).read_bytes()==(a.second/name).read_bytes()
for file in sorted(a.first.glob('*.csv')):
    if file.name=='audit-packets.csv': continue
    checks[file.name]=(a.second/file.name).exists() and file.read_bytes()==(a.second/file.name).read_bytes()
def workload(file):
    h=hashlib.sha256(); count=0
    with file.open(newline='') as fp:
        for x in csv.DictReader(fp):
            if x['name'].startswith(('/benign/','/ifa/','/report/')):
                h.update(json.dumps(x,sort_keys=True,separators=(',',':')).encode()); h.update(b'\n'); count+=1
    return {'rows':count,'sha256':h.hexdigest()}
first=workload(a.first/'audit-packets.csv'); second=workload(a.second/'audit-packets.csv')
checks['workload_packet_audit']=first==second
result={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'workload_first':first,'workload_second':second,
        'scope':'identical-input replay, not statistically independent runs; other signed management traffic excluded'}
a.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
