"""Recount the published coding, not the prevalence of all NDN literature."""
import argparse
import csv
import json
from pathlib import Path

ARCH = Path(__file__).resolve().parents[1]

def recount():
    data = json.loads((ARCH/'literature/usage-ranking.json').read_text(encoding='utf-8-sig'))
    catalog = json.loads((ARCH/'literature/catalogue-public.json').read_text(encoding='utf-8-sig'))
    with (ARCH/'literature/usage-ranking-evidence.csv').open(encoding='utf-8-sig',newline='') as stream:
        evidence = list(csv.DictReader(stream))
    known = {r['id'] for r in catalog}
    assert len(known) == len(catalog) == 50, 'Unexpected catalog membership'
    result = {'status':'PASS','scope':data['scope'],'catalog_references':len(catalog),
              'screening_label_date':data['as_of'],'consolidation_date':'2026-10-17'}
    for key, dimension in [('topology','Topology'),('architecture','Architecture')]:
        eligible = set(data[key+'_ids'])
        denominator = data[key+'_denominator']
        assert len(eligible) == denominator and eligible <= known
        categories = {}
        all_ids = []
        for category, ids in data[key].items():
            assert len(ids) == len(set(ids)) and set(ids) <= eligible
            coded = {r['Paper ID'] for r in evidence if r['Dimension']==dimension and r['Category']==category}
            assert coded == set(ids), f'Evidence mismatch: {key}/{category}'
            categories[category] = {'count':len(ids),'denominator':denominator,
                                    'percent':round(100*len(ids)/denominator,1),'ids':ids}
            all_ids.extend(ids)
        assert set(all_ids) == eligible
        if key == 'architecture':
            assert len(all_ids) == len(set(all_ids)), 'Architecture coding is expected to be exclusive'
        result[key] = categories
    common = set(data['topology_ids']) & set(data['architecture_ids'])
    joint = set(data['topology']['Tree/binary tree']) & set(data['architecture']['Central ISP/cloud graph detection'])
    assert len(common)==14 and joint=={'T001'}
    assert len(data['topology']['Tree/binary tree'])==7 and data['topology_denominator']==18
    assert len(data['architecture']['Central ISP/cloud graph detection'])==2 and data['architecture_denominator']==15
    result['joint_tree_and_central_graph']={'count':len(joint),'joint_eligible_denominator':len(common),
                                           'ids':sorted(joint),'exact_project_layout_count':'not established'}
    result['note']='Categories and eligibility reproduce the supplied partial-text coding; independent recoding requires checking the cited primary papers.'
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path); a=p.parse_args()
    value=recount(); rendered=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(rendered,encoding='utf-8',newline='\n')
    print(rendered,end='')
