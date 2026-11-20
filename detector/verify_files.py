from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent
for x in json.loads((r/'MANIFEST.json').read_text())['files']:
 p=r/x['path'];assert p.stat().st_size==x['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
print('PACKAGE_FILES_PASS')
