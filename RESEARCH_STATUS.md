# Research status: monitoring report prioritization

Updated 20 October 2026. The current paper direction evaluates monitoring report delivery under congestion and its effect on frozen IFA detectors. Results concern a controlled simulation study, not a deployed real-time detector or a demonstrated improvement in general IFA robustness.

## Research questions

**RQ1:** How are congestion-induced monitoring report loss and delay associated with the detection performance and latency of machine learning-based Interest Flooding Attack detectors in Named Data Networking?

**RQ2:** To what extent does priority-based monitoring report delivery improve telemetry availability and Interest Flooding Attack detection reliability under congestion, and what trade-offs does it impose on legitimate traffic?

RQ1 evaluates association: congestion changes source measurements as well as report availability. RQ2 evaluates the combined effect of strict priority scheduling and push-out admission. Their individual effects have not been isolated. Plain, Mask and Mask+Age are supporting ablations rather than separate research questions.

## Two distinct experiment campaigns

| Item | FIFO-Priority campaign | Earlier local ML evaluation |
|---|---|---|
| Purpose | Monitoring delivery, frozen detector behavior and service trade-offs | Detector baselines and graph/temporal ablations |
| Development dataset | 17 families; 11/2/4 split reported in source and metadata | 31 families; 19/8/4 split |
| Neural input | Five frames; graph hidden32, GRU hidden64 | Selected sequence20, hidden64 |
| Neural seeds | 11, 23, 37 | Five seeds in the local frozen protocol |
| Threshold | Grouped training OOF calibration | Validation selection |
| Test status | Metadata declares final test unused; full historical lineage audit remains incomplete | One-shot local test completed on 18 October |

These campaigns do not share an interchangeable checkpoint, split or test protocol. See [the earlier local ML pipeline](ML_TOPOLOGY_PIPELINE.md) for that evaluation. Its RF/XGBoost results are not FIFO-Priority stress-test results.

## FIFO-Priority experiment

The topology contains ten routers and seven endpoints, with collector M at R10 and producer P at R4. R8 to R10 is configured at 1Mbps, the reverse direction at 10Mbps. Other links use 10Mbps and 2ms propagation delay. Cache is disabled. Simulation duration is 30s.

Three benign consumers each generate 5 Interests/s during [2,25). A1 generates 50 unsatisfied Interests/s during [5,10); A2 remains inactive. Background traffic runs during [4,15) at 100, 300 or 1500Hz, with three independently drawn schedules per rate. The same schedule is used within each S2/S3 by FIFO/Priority quartet. S2 is background-only and S3 adds IFA. There are 36 primary runs: 18 FIFO and 18 Priority. Model seeds and windows are not independent network realizations.

Agents sample every second for 28 windows, producing 280 expected reports per run. Collector polling starts at w+0.05s with a 1ms stagger per router. Decision cutoff is w+0.25s. Report Interest lifetime is 1s, without retransmission. Only report Data already received by the cutoff enters detector input. Late reports cannot revise earlier decisions. Measurements use LOCF, with optional freshness mask and sample age. A fresh sample has raw age0.25s at the decision cutoff.

Priority is non-preemptive strict priority with stable FIFO order within two classes and a shared100-packet buffer per direction. When full, an arriving monitoring packet can evict the last waiting normal packet. No additional buffer is provided. Classification uses an exact report-name allowlist for Interest/Data, not cryptographic authentication. Both NetDevices on R8-R10 apply the policy. Scheduling and admission are one combined intervention.

## Main reported results

Each rate/policy below aggregates six primary runs: S2/S3 by three matched schedules. This is three independent schedules per rate, not six independent draws.

| Background | FIFO on-time | FIFO late | FIFO never received | Priority on-time |
|---|---:|---:|---:|---:|
|100Hz|1680/1680|0|0|1680/1680|
|300Hz|1284/1680|147|249|1680/1680|
|1500Hz|1248/1680|106|326|1680/1680|

The primary Priority campaign has 5040/5040 on-time reports. FIFO has 575 never-received and 253 late reports. The collaborator's audit links all575 never-received reports to Data tail drops on R8 to R10; the complete primary raw archive has not been transferred for the receiving team's independent trace replay.

Descriptive model averages below combine three input variants by three model seeds and three schedules. They are not population confidence intervals. Recall and F1 come from S3; FPR comes from S2, so these columns do not describe one combined confusion matrix.

| Rate | Policy | Model | Recall S3 | FPR S2 | F1 S3 |
|---|---|---|---:|---:|---:|
|100Hz|FIFO/Priority|GRU|1.0000|0.0000|1.0000|
|100Hz|FIFO/Priority|Graph+GRU|0.9037|0.0000|0.8814|
|300Hz|FIFO|GRU|0.4889|0.0401|0.4101|
|300Hz|Priority|GRU|1.0000|0.0293|0.9775|
|300Hz|FIFO|Graph+GRU|0.9778|0.4182|0.6275|
|300Hz|Priority|Graph+GRU|1.0000|0.4321|0.6329|
|1500Hz|FIFO|GRU|0.0667|0.0463|0.0578|
|1500Hz|Priority|GRU|1.0000|0.1003|0.8949|
|1500Hz|FIFO|Graph+GRU|0.9778|0.4568|0.6126|
|1500Hz|Priority|Graph+GRU|1.0000|0.4676|0.6168|

Telemetry protection restores GRU sensitivity in this workload, but does not guarantee specificity. High graph recall must be interpreted alongside false alarms on the matched congestion-only scenario. Manuscripts should also show results by input variant, seed and independent schedule.

The earliest attack-containing decision is6.25s after onset5s: minimum scheduled causal latency1.25s, not measured neural CPU or alert latency. At1500Hz FIFO, GRU has target alarms in6/27 model-schedule combinations, with21misses; two alarms occur after attack stop. These27 combinations are not27 independent network episodes.

Mean paired relative background payload-goodput costs are0.003045/0.003362 at300Hz S2/S3 and0.004047/0.004054 at1500Hz S2/S3, approximately0.30-0.41%. This is relative change, not percentage points. Completion and fairness effects are mixed; small aggregate cost does not establish noninferiority for every legitimate consumer.

## What has been independently checked after transfer?

- Four additional archives were extracted without changing the originals. Two evaluation ZIPs contain787 byte-identical payloads and are not separate experiments.
- 54 collector snapshots reconstruct bit-identical causal tensors.
- All18 frozen models were replayed from weights using the reviewed NumPy implementation. Across23328 predictions, no decisions changed; maximum score difference was7.152557373046875e-7.
- Complete raw traces for eight pilot runs support queue, serialization and report-payload replay. All116 missing pilot reports match Data drops. These are separate from the575 primary-campaign missing reports.
- 1607 outer payload manifest entries and736 internal raw manifest entries match.

The transferred build-provenance package contains reported hashes and environment/git records, but not the actual binary or build logs. Original OOF/train-prediction/history/fold-plan files referenced by the18 COMPLETE records are not in the trimmed inference bundles. The complete17-family split manifest and training lineage remain audit gaps. Successful inference replay does not prove historical training independence or source-to-binary provenance.

## Public artifacts and next steps

The repository includes the original benign/IFA simulator package and, from commit3499c7a, an offline replay module plus one GraphSAGE+GRU Mask+Age seed11 bundle under `config/architecture/ndnsim/monitoring/`. The three core artifact hashes match its COMPLETE record and the corresponding transferred campaign bundle. This single model is not the locally selected v3+v4 model, nor the full18-model evaluation package. Its presence does not establish real-time deployment or complete training reproducibility.

The full FIFO-Priority scenario/configurations, raw stress traces, training dataset and all18 checkpoints are not distributed by this documentation update. Existing smoke-test commands do not reproduce the primary FIFO-Priority campaign.

Continue manuscript preparation and internal review. Obtain relevant raw subsets or the full primary archive where needed for claim verification; narrow claims if evidence is unavailable. Additional Mint simulation, retraining, threshold tuning and sealed-test access are not automatic next steps. The paper has not yet been declared ready for submission.

Direct QoS and priority-delivery prior art still needs comparison before final novelty wording. INT-Partition supports fault-tolerant telemetry motivation; WEASEL and Multi-Indicator VNDN constrain temporal/distributed-monitoring novelty. None alone proves the proposed combination is new.
