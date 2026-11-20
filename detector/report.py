"""Predeclared descriptive analysis. Never modifies models or excludes weak results."""
from pathlib import Path
from collections import defaultdict
import csv,json,statistics,hashlib
import numpy as np
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def table(p,rows):
 with p.open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def ratio(a,b):return a/b if b else None
def metrics(rows):
 tp=sum(int(x['actual']) and int(x['prediction']) for x in rows);fp=sum(not int(x['actual']) and int(x['prediction']) for x in rows);fn=sum(int(x['actual']) and not int(x['prediction']) for x in rows);tn=len(rows)-tp-fp-fn
 neg=[x for x in rows if x['scenario']=='s2'];busy=[x for x in neg if int(x['busy'])]
 return dict(tp=tp,fp=fp,fn=fn,tn=tn,f1=ratio(2*tp,2*tp+fp+fn) or 0,precision=ratio(tp,tp+fp) or 0,recall=ratio(tp,tp+fn),s2_fpr=ratio(sum(int(x['prediction']) for x in neg),len(neg)),busy_s2_fpr=ratio(sum(int(x['prediction']) for x in busy),len(busy)))
def main():
 receipt=read(R/'campaign-receipt.json');audit=read(R/'campaign-audit.json');extra=read(R/'extra-audit.json')
 assert receipt['status']==audit['status']==extra['status']=='PASS' and len(receipt['completed'])==720 and audit['decision_count']==17280
 plan=read(R/'plan.json');byrun={x['label']:x for x in plan};bycase={};kinds=[x['kind'] for x in read(R/'registry.json')['models']]
 with (R/'campaign-decisions.csv').open() as f:rows=list(csv.DictReader(f))
 rr=defaultdict(list);groups=defaultdict(list)
 for row in rows:
  p=byrun[row['run']];row.update(stage=p['stage'],family=p['family'],burst_enabled=int(p['burst_enabled']));rr[row['run']].append(row);groups[p['family'],p['policy'],p['kind']].append(row)
 table(R/'decisions-with-metadata.csv',rows)
 episodes=[];service=[];timing=[]
 for p in plan:
  z=rr[p['label']];root=R/'runs'/p['label'];d=read(root/'detector-result.json');ex=read(root/'execution.json');q=read(root/'priority-validation.json')['metrics']
  hits=[x for x in z if int(x['actual']) and int(x['prediction']) and float(x['output_at_s'])<p['attack_stop']]
  late=[x for x in z if int(x['actual']) and int(x['prediction']) and float(x['output_at_s'])>=p['attack_stop']]
  episodes.append(dict(run=p['label'],stage=p['stage'],family=p['family'],rate=p['rate'],burst_enabled=p['burst_enabled'],kind=p['kind'],policy=p['policy'],scenario=p['scenario'],timely=bool(hits) if p['scenario']=='s3' else None,late_only=bool(late) and not hits if p['scenario']=='s3' else None,first_timely_alarm_s=min((float(x['output_at_s']) for x in hits),default=None),pre_onset_fp=sum(int(x['prediction']) and float(x['output_at_s'])<p['attack_start'] for x in z),post_attack_fp=sum(int(x['prediction']) and not int(x['actual']) and float(x['output_at_s'])>=p['attack_stop'] for x in z),all_fp=sum(int(x['prediction']) and not int(x['actual']) for x in z)))
  timing.append(dict(run=p['label'],kind=p['kind'],stage=p['stage'],rate=p['rate'],policy=p['policy'],deadline_misses=sum(not int(x['deadline_hit']) for x in z),lag_over100ms=sum(float(x['simulator_lag_ms'])>100 for x in z),inference_p95_ms=float(np.percentile([float(x['inference_ms']) for x in z],95)),total_p95_ms=float(np.percentile([float(x['total_after_cutoff_ms']) for x in z],95)),total_max_ms=max(float(x['total_after_cutoff_ms']) for x in z),peak_rss_mib=d['peak_rss_kib']/1024,detector_startup_s=ex['detector_startup_seconds'],run_wall_s=ex['wall_seconds']))
  # Network service has no detector feedback; do not count ten copies as independent observations.
  if p['case'] not in bycase:
   bycase[p['case']]=p
   flowkey=next((k for k,v in q.items() if isinstance(v,list) and v and isinstance(v[0],dict) and 'file' in v[0]),None)
   flows=q[flowkey] if flowkey else []
   save(root/'service-analysis.json',dict(case=p['case'],report_by_router=q['report_by_router'],flows=flows))
   ontime=sum(x['on_time'] for x in q['report_by_router']);latecount=sum(x['late'] for x in q['report_by_router']);missing=sum(x['missing'] for x in q['report_by_router'])
   assert ontime+latecount+missing==280
   for flow in flows:
    service.append(dict(case=p['case'],stage=p['stage'],family=p['family'],rate=p['rate'],burst_enabled=p['burst_enabled'],scenario=p['scenario'],policy=p['policy'],reports_on_time=ontime,reports_late=latecount,reports_missing=missing,flow=flow['file'],requests=flow['requests'],data=flow['data'],completion_fraction=flow['completion_fraction'],rtt_p95_s=flow.get('rtt_p95_s'),phase_goodput_json=json.dumps(flow.get('by_arrival_phase',{}),sort_keys=True)))
 family=[]
 for (fam,pol,kind),z in groups.items():
  p=byrun[z[0]['run']];ep=next(x for x in episodes if x['family']==fam and x['policy']==pol and x['kind']==kind and x['scenario']=='s3')
  family.append(dict(stage=p['stage'],family=fam,rate=p['rate'],burst_enabled=p['burst_enabled'],policy=pol,kind=kind,**metrics(z),timely=ep['timely'],pre_onset_fp=ep['pre_onset_fp'],post_attack_fp=ep['post_attack_fp']))
 summaries=[];pooled=[]
 for kind in kinds:
  for rate in [100,200,300,1500]:
   for pol in ['fifo','priority']:
    z=[x for x in family if x['stage']=='fresh' and x['kind']==kind and x['rate']==rate and x['policy']==pol];assert len(z)==4
    out=dict(kind=kind,rate=rate,policy=pol,families=4)
    for field in ['f1','recall','precision','s2_fpr','busy_s2_fpr']:
     v=[float(x[field]) for x in z if x[field] is not None];out.update({field+'_mean':statistics.mean(v),field+'_min':min(v),field+'_max':max(v)})
    out['timely_episodes']=sum(x['timely'] for x in z);summaries.append(out)
    zz=[x for x in rows if x['stage']=='fresh' and x['kind']==kind and int(x['rate'])==rate and x['policy']==pol];pooled.append(dict(kind=kind,rate=rate,policy=pol,**metrics(zz)))
 pairs=[]
 for kind in kinds:
  for pol in ['fifo','priority']:
   a=next(x for x in family if x['stage']=='diagnostic' and x['burst_enabled'] and x['kind']==kind and x['policy']==pol);b=next(x for x in family if x['stage']=='diagnostic' and not x['burst_enabled'] and x['kind']==kind and x['policy']==pol)
   aa={(x['scenario'],int(x['window'])):x for x in rows if x['stage']=='diagnostic' and int(x['burst_enabled']) and x['kind']==kind and x['policy']==pol};bb={(x['scenario'],int(x['window'])):x for x in rows if x['stage']=='diagnostic' and not int(x['burst_enabled']) and x['kind']==kind and x['policy']==pol}
   delta=[dict(scenario=k[0],window=k[1],on_score=float(aa[k]['score']),off_score=float(bb[k]['score']),on_pred=int(aa[k]['prediction']),off_pred=int(bb[k]['prediction'])) for k in aa if aa[k]['prediction']!=bb[k]['prediction']]
   pairs.append(dict(kind=kind,policy=pol,burst_on_f1=a['f1'],burst_off_f1=b['f1'],burst_on_fp=a['fp'],burst_off_fp=b['fp'],fp_delta_on_minus_off=a['fp']-b['fp'],burst_on_fn=a['fn'],burst_off_fn=b['fn'],changed_decisions=len(delta),differences_json=json.dumps(delta)))
 table(R/'metrics-per-family.csv',family);table(R/'metrics-fresh-macro.csv',summaries);table(R/'metrics-fresh-pooled.csv',pooled);table(R/'burst-pairs.csv',pairs);table(R/'episode-metrics.csv',episodes);table(R/'timing-per-run.csv',timing)
 assert service,'Network flow metrics not found: inspect validator schema, do not silently omit service'
 table(R/'service-per-case-flow.csv',service)
 summary=dict(status='PASS',runs=720,decisions=17280,fresh_families=16,fresh_families_per_rate=4,diagnostic_independent_workload=1,models=10,checkpoint_seed=11,deadline_misses=sum(x['deadline_misses'] for x in timing),lag_over100ms=sum(x['lag_over100ms'] for x in timing),maximum_total_ms=max(x['total_max_ms'] for x in timing),all_trajectories_identical_between_models=audit['all_trajectories_identical'],live_outputs_all_before_end=all(x['live_output_before_simulation_end'] for x in extra['checks']),review_status='automated descriptive report; manual review pending')
 save(R/'summary.json',summary)
 lines=['# Hasil sementara otomatis: perluasan online dan diagnosis burst','', 'Integritas input dan keputusan telah diaudit; interpretasi akhir masih perlu dibaca dan ditinjau. Tidak ada training/tuning atau perubahan paper.','',f"720 run /17280 keputusan. Deadline misses: {summary['deadline_misses']}; lag>100ms: {summary['lag_over100ms']}. Maksimum total: {summary['maximum_total_ms']:.3f}ms.",'','## Workload baru','', 'F1 rata-rata empat family independen per beban; rentang bukan confidence interval. Satu checkpoint seed11 per model.','', '|Model|Beban|FIFO F1 mean [min,max]|Priority F1 mean [min,max]|Timely FIFO/Priority|','|---|---:|---|---|---|']
 for kind in kinds:
  for rate in [100,200,300,1500]:
   z={x['policy']:x for x in summaries if x['kind']==kind and x['rate']==rate}
   cells=[f"{z[p]['f1_mean']*100:.2f}% [{z[p]['f1_min']*100:.2f},{z[p]['f1_max']*100:.2f}]" for p in ['fifo','priority']]
   lines.append('|'+kind+'|'+str(rate)+'|'+'|'.join(cells)+f"|{z['fifo']['timely_episodes']}/4; {z['priority']['timely_episodes']}/4|")
 lines+=['','## Diagnosis berpasangan pada workload pilot1500','', 'Ini diagnosis post-hoc pada satu workload, bukan konfirmasi generalisasi. Burst on/off dijalankan ulang pada sesi ini.','', '|Model|Policy|FP burst-on|FP burst-off|FN on/off|Perubahan keputusan|','|---|---|---:|---:|---|---:|']
 for p in pairs:lines.append(f"|{p['kind']}|{p['policy']}|{p['burst_on_fp']}|{p['burst_off_fp']}|{p['burst_on_fn']}/{p['burst_off_fn']}|{p['changed_decisions']}|")
 lines+=['','## Batas dan bukti','', 'Workload antar-beban berbeda sehingga bukan isolasi kausal rate. Empat family/rate dan satu seed model belum cukup untuk ranking universal. Burst intervention mengukur efek total pada jaringan/input, bukan kontribusi satu fitur. Priority mencakup scheduling dan push-out. Belum ada jaringan fisik, mitigasi, topologi lain, atau hard realtime. Tidak menggabungkan hasil dengan cohort lama.','', 'metrics-per-family.csv, metrics-fresh-macro.csv, metrics-fresh-pooled.csv, burst-pairs.csv, episode-metrics.csv, timing-per-run.csv, service-per-case-flow.csv; campaign/extra audit dan raw logs disimpan.','']
 (R/'HASIL-OTOMATIS.md').write_text('\n'.join(lines),encoding='utf-8')
 print('REPORT_PASS',flush=True)
if __name__=='__main__':main()
