"""Audit the small public IFA reference on a temporary copy, without ndnSIM."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
ref=root/'evidence/reference-run'
def digest(file): return hashlib.sha256(file.read_bytes()).hexdigest()
manifest=json.loads((ref/'reference-sha256.json').read_text())
assert set(manifest)|{'reference-sha256.json'}=={f.name for f in ref.iterdir() if f.is_file()}
assert all(digest(ref/name)==sha for name,sha in manifest.items())
assert (root/'scenarios/ifa-tree.cpp').read_bytes()==(ref/'scenario.cpp').read_bytes()
assert (root/'scripts/validate_ifa.py').read_bytes()==(ref/'validator.py').read_bytes()
assert json.loads((root/'config/ifa-atk1-00050-s1.json').read_text())==json.loads((ref/'config.json').read_text())
assert (root/'docs/ndn-cxx-scheduler-single-wakeup.patch').read_bytes()==(ref/'scheduler.patch').read_bytes()
before={f.name:digest(f) for f in ref.iterdir() if f.is_file()}
expected=json.loads((ref/'validation.json').read_text())
with tempfile.TemporaryDirectory(prefix='ndn-ifa-audit-') as temporary:
    target=Path(temporary)/'reference'; shutil.copytree(ref,target)
    result=subprocess.run([sys.executable,str(target/'validator.py'),'--config',str(target/'config.json'),
                           '--run',str(target)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr or result.stdout
    actual=json.loads((target/'validation.json').read_text())
    assert actual==expected
assert before=={f.name:digest(f) for f in ref.iterdir() if f.is_file()}
proof=json.loads((root/'evidence/scheduler-fix-validation.json').read_text())
assert proof['status']=='PASS' and len(proof['accepted_conditions'])==12
assert proof['regression_before']['status']=='FAIL' and proof['regression_after']['status']=='PASS'
assert all(c['callbacks_and_timing_ok'] for c in proof['regression_before']['cases']+proof['regression_after']['cases'])
assert proof['scheduler_patch_sha256']==digest(root/'docs/ndn-cxx-scheduler-single-wakeup.patch')
assert len(proof['conformance'])==10 and all(v['status']=='PASS' for v in proof['conformance'].values())
print(json.dumps({'status':'PASS','reference_files':len(manifest),'ifa_reference_checks':len(actual['checks']),
    'attack_sink_received':actual['metrics']['attack_sink_received'],
    'report_on_time':actual['metrics']['report_status_counts']['on_time'],
    'reference_unchanged':True,'scheduler_summary_conditions':12,
    'scope':'Offline audit of included raw IFA reference; high-load summaries are not independent reruns.'},indent=2))
