"""Offline integrity, reference evidence, literature and portability checks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote

from analyze_topology import analyze
from recount_literature import recount

ROOT=Path(__file__).resolve().parents[2]
ARCH=ROOT/'architecture'
MANIFEST=ARCH/'evidence/package-sha256.json'
RECEIPT=ARCH/'evidence/package-validation.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def files():
    result=[]
    for f in ROOT.rglob('*'):
        if not f.is_file() or f in [MANIFEST,RECEIPT]: continue
        rel=f.relative_to(ROOT)
        if any(part in ['__pycache__','.git'] for part in rel.parts): continue
        if any(str(rel).replace('\\','/').startswith(p) for p in
               ['architecture/ndnsim/deps/','architecture/ndnsim/runs/',
                'architecture/ndnsim/ifa-pilot/runs/','architecture/generated/']): continue
        if rel.suffix=='.pyc': continue
        if str(rel).replace('\\','/').startswith('architecture/ndnsim/docs/') and (rel.suffix=='.log' or ('resources' in rel.name and rel.suffix=='.txt')): continue
        if str(rel).replace('\\','/').startswith('architecture/ndnsim/ifa-pilot/docs/') and rel.suffix=='.log': continue
        result.append(f)
    return sorted(result)

def verify(write_manifest=False):
    published=files()
    if write_manifest:
        MANIFEST.write_text(json.dumps({p.relative_to(ROOT).as_posix():digest(p) for p in published},indent=2)+'\n',encoding='utf-8',newline='\n')
    expected=json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert set(expected)=={p.relative_to(ROOT).as_posix() for p in published}, 'Manifest membership differs'
    assert all(digest(ROOT/name)==value for name,value in expected.items()), 'Package checksum mismatch'
    local_links=0
    for f in published:
        if f.suffix=='.json': json.loads(f.read_text(encoding='utf-8-sig'))
        if f.suffix!='.md': continue
        text=f.read_text(encoding='utf-8')
        assert '\u2014' not in text, f'Unexpected em dash in prose: {f.name}'
        for match in re.finditer(r'!?\[[^\]]+\]\(([^)]+)\)',text):
            target=match[1].strip().strip('<>')
            if target.startswith(('https://','http://','mailto:','#')): continue
            target=unquote(target.split('#',1)[0])
            path=(f.parent/target).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), f'Broken/nonportable local link: {f.name}: {target}'
            local_links+=1
    risky=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
           r'\bgh[pousr]_[A-Za-z0-9]{20,}\b',
           r'\b(?:192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b',
           r'(?i)(?:[a-z]:[\\/](?:Users|MBC)[\\/]|/h[o]me/[^/\s]+/)']
    for f in published:
        # Checksum binary model payloads above; do not decode them as UTF-8 prose.
        if f.suffix in {'.png','.pt','.joblib'}: continue
        text=f.read_text(encoding='utf-8-sig')
        assert not any(re.search(pattern,text) for pattern in risky), f'Private access/path pattern: {f.name}'
    literature=recount(); graph=analyze()
    assert json.loads((ARCH/'evidence/literature-counts.json').read_text(encoding='utf-8'))==literature
    assert json.loads((ARCH/'evidence/graph-analysis.json').read_text(encoding='utf-8'))==graph
    provenance=json.loads((ARCH/'evidence/provenance.json').read_text(encoding='utf-8'))
    for name,sha in provenance['reference_input_sha256'].items():
        assert digest(ROOT/name)==sha, f'Reference source/config changed: {name}'
    lock=json.loads((ARCH/'ndnsim/docs/stack-lock.json').read_text(encoding='utf-8'))
    bootstrap=(ARCH/'ndnsim/scripts/bootstrap_mint.sh').read_text(encoding='utf-8')
    assert all(lock['repositories'][r]['commit'] in bootstrap for r in ['ns-3','ndnSIM'])
    assert digest(ARCH/'ndnsim'/lock['functional_patch'])==lock['functional_patch_sha256']
    assert 'apply_scheduler_fix.sh' in bootstrap
    ref=ARCH/'evidence/reference-run'
    original={f.name:digest(f) for f in ref.iterdir() if f.is_file()}
    with tempfile.TemporaryDirectory(prefix='ndn-ifa-reference-') as temporary:
        temp=Path(temporary).resolve(); run=temp/'reference-run'
        assert run.resolve().is_relative_to(temp)
        shutil.copytree(ref,run)
        proc=subprocess.run([sys.executable,str(ARCH/'ndnsim/scripts/validate_run.py'),
                             '--config',str(run/'config.json'),'--run',str(run)],capture_output=True,text=True)
        assert proc.returncode==0, proc.stderr or proc.stdout
        validation=json.loads(proc.stdout)
        assert validation==json.loads((ref/'validation.json').read_text(encoding='utf-8'))
    assert original=={f.name:digest(f) for f in ref.iterdir() if f.is_file()}, 'Reference evidence modified'
    replay=json.loads((ARCH/'evidence/replay-validation.json').read_text(encoding='utf-8'))
    assert replay['status']=='PASS' and replay['workload_packet_trace_identical']
    ifa_script=ARCH/'ndnsim/ifa-pilot/scripts/verify_reference.py'
    ifa_process=subprocess.run([sys.executable,str(ifa_script)],capture_output=True,text=True)
    assert ifa_process.returncode==0,ifa_process.stderr or ifa_process.stdout
    ifa_validation=json.loads(ifa_process.stdout)
    return {'status':'PASS','date':'2026-10-20','manifest_files':len(expected),'portable_local_links':local_links,
            'private_access_pattern_scan':'PASS','reference_input_hashes':'PASS','reference_evidence_unchanged':True,
            'reference_runtime_checks_recomputed':len(validation['checks']),
            'consumer_data_counts':{r:v['events']['data'] for r,v in validation['consumers'].items()},
            'report_status':validation['collector_status_counts'],
            'topology_nodes':graph['nodes'],'topology_links':graph['links'],
            'literature_tree':'7/18','literature_central_graph':'2/15','joint_coded_studies':['T001'],
            'clean_second_stack_build_performed':False,
            'ifa_reference':ifa_validation,
            'note':'Offline distribution checks; does not claim a new simulation, ML evaluation or successful fresh installation on another OS.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--write-manifest',action='store_true'); p.add_argument('--record',action='store_true'); args=p.parse_args()
    result=verify(args.write_manifest)
    if args.record: RECEIPT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))
