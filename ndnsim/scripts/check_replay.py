"""Compare two benign validation runs; replay is not an independent experiment."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('first',type=Path)
p.add_argument('replay',type=Path)
p.add_argument('--output',type=Path,required=True)
a = p.parse_args()

def sha(f):
    return hashlib.sha256(f.read_bytes()).hexdigest()

files = sorted(x.name for x in a.first.glob('*.csv'))
identical = {name:sha(a.first/name)==sha(a.replay/name) for name in files}

def workload(f):
    with f.open(newline='') as stream:
        return [x for x in csv.DictReader(stream)
                if x['name'].startswith(('/benign/','/report/'))]

workload_same = workload(a.first/'audit-packets.csv') == workload(a.replay/'audit-packets.csv')
inputs_same = all(sha(a.first/name)==sha(a.replay/name) for name in ['config.json','scenario.cpp','validator.py'])
validations_pass = all(json.loads((path/'validation.json').read_text())['status']=='PASS' for path in [a.first,a.replay])
passed = inputs_same and validations_pass and workload_same and all(same for name,same in identical.items() if name != 'audit-packets.csv')
result = {'status':'PASS' if passed else 'FAIL', 'same_inputs':inputs_same,'both_runs_pass':validations_pass,
          'workload_packet_trace_identical':workload_same,'raw_csv_identical':identical,
          'first':a.first.name,'replay':a.replay.name,
          'scope':'same configuration and RNG replay; not an independent statistical run',
          'note':'Raw audit may additionally contain local signed management commands; compare their identity separately from workload packets.'}
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if passed else 1)
