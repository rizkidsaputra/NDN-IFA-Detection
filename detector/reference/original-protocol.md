# Semua model pada cohort simulasi 24 Oktober — protokol perluasan

24 Oktober 2026. Pengguna meminta mencoba semua model yang pernah digunakan. Dataset adalah cohort `confirmation-20261024` yang sama: 384 run, 32/16/48 keluarga train/validation/test, 12 keluarga test per rate100/200/300/1500 dan matched S2/S3 × FIFO/Priority. **Test cohort ini sudah pernah diamati. Perluasan ini eksploratori pada cohort yang sama, bukan test independen baru.** Tidak ada simulasi/dataset jaringan baru atau perubahan source/data/model frozen sebelumnya. Paper menunggu approval pengguna.

## Cakupan

Sepuluh keluarga yang telah dipakai: Logistic Regression (LR), Random Forest (RF), GRU, GraphSAGE+GRU, Gradient Boosting Decision Trees (GBDT), AdaBoost, XGBoost, LightGBM, CatBoost, HistGradientBoosting (HistGB). Seluruh keluarga akan dikembangkan pada train/validation baru. Tiga pipeline native-missing tambahan: HistGB, XGBoost dan LightGBM dengan current-NaN. Konfigurasi tetap yang dipakai sebelumnya, termasuk HistGB-E LOCF dan HistGB awal/NaN, ikut dilatih sebagai anchor konfigurasi.

Tiga panel terpisah: (1) konfigurasi dipilih dari validation baru; (2) konfigurasi lama dilatih pada train baru dan threshold dikalibrasi pada validation baru; (3) checkpoint lama frozen ditransfer ke test baru tanpa fitting atau mengganti threshold/scaler. Panel ketiga bukan perbandingan algoritma dengan data latih/kesempatan tuning sama. Konfigurasi/model duplikat memakai satu fit dan diberi alias, bukan dianggap bukti independen.

## Input dan split

Input causal LOCF + mask/age, lima frame × sepuluh router ×13kanal. Data training dan validation hanya dibaca pada fitting, dengan hash mengacu ke FREEZE konfirmasi. Scaler log1p+standardisasi fit dari train saja dan harus cocok dengan scaler frozen konfirmasi. Metadata bukan fitur. Tabular flatten650nilai; neural memakai struktur temporal/router yang sama. Frame historis tidak diperbaiki retrospektif. Tidak memakai source reports yang tidak tiba untuk fit.

Current-NaN dibuat sesudah transform: raw11 menjadi NaN pada frame/router mask0; mask/age tetap finite. Ini membuang nilai stale dan mengubah representasi sekaligus memakai missing routing, bukan isolasi kemampuan routing. No-history dicatat; bila tidak ada no-history pada split yang diuji, varian itu identik LOCF dan tidak di-fit sebagai bukti tambahan. Coverage dilaporkan per split dengan denominator frame yang dapat berulang antar-sequence.

## Pencarian validation yang ditetapkan sebelum fit tambahan

Setiap pipeline mendapat8kandidat seed11, kemudian konfigurasi terpilih diulang seed23/37 tanpa memilih seed terbaik. RF/HistGB full memakai kembali seluruh8kandidat dan checkpoint pilihan yang sudah frozen pada konfirmasi, dengan hash/validation score diverifikasi; tidak menambah tuning pada keduanya.

| Pipeline | Delapan kandidat |
|---|---|
| LR | C =0.001/0.003/0.01/0.03/0.1/1/10/100; L2, lbfgs, balanced, maxiter2000 |
| RF | trees200/400 × minleaf1/2/5/10; balanced; reuse frozen search |
| HistGB LOCF dan current-NaN | iter200/400 × minleaf10/20/40/80; LR.05, leaves15,L2=1,noearlystop |
| GBDT | iter200/400 × minleaf5/10/20/40; depth3, maxleaves15, LR.05, subsample1 |
| AdaBoost | iter200/400 × stump-minleaf1/5/20/40; depth1, LR.05 |
| XGBoost LOCF dan current-NaN | iter200/400 × maxleaves7/15/31/63; hist/lossguide, depth0, minchildweight1, LR.05,L2=1,maxbin255, subsample/colsample1 |
| LightGBM LOCF dan current-NaN | iter200/400 × minchildsamples5/10/20/40; leaves15, depthunlimited, LR.05,L2=1,maxbin255, deterministic/forcecolwise, subsample/colsample1 |
| CatBoost | iter200/400 × depth3/4/5/6; LR.05,L2=1,border255,bootstrapNo,Plain,noearlystop |
| GRU dan GraphSAGE+GRU | LR0.0003/0.001 × dropout0/.15 × GRUhidden32/64; densehead32, graphhidden32 |

Jumlah kandidat sama, tetapi FLOPs, kapasitas, optimizer dan peluang pemilihan epoch tidak identik. Ini bounded search per keluarga, bukan bukti algoritma telah dioptimalkan sama baik. Bobot kelas balanced dari train. LR/RF memakai class_weight; boosting sample_weight; neural BCE pos_weight.

Neural: batch128, AdamW weightdecay.0001, clipnorm5, maksimal80epoch, minimum20epoch, patience12, cap120detik/fit; pilih checkpoint berdasar mean AP validation (positive versus busy S2) per rate/policy. Stop pada patience atau cap setelahminimum20. Pemilihan8kandidat kemudian menggunakan threshold/quality yang sama dengan keluarga lain. Cap/epoch aktual disimpan; tidak menambah budget untuk model yang hasilnya kurang baik. Graph memakai mean-neighbor operator dan adjacency tetap yang sama dengan implementasi aktif terdahulu, bukan GNN4IFA asli.

Threshold global per checkpoint menggunakan validation saja: maksimum mean recall lintas rate/policy, dengan pooled FPR all-S2 dan busy-S2 ≤5% pada setiap rate/policy. Tie: worst busy FPR lebih kecil, mean all-S2 FPR lebih kecil, lalu threshold lebih tinggi. Konfigurasi dipilih dengan tiga quality pertama; tie urutan grid, tidak membandingkan threshold numerik antar-model. Model no-alarm dan hasil buruk dipertahankan.

## Anchor konfigurasi lama

LR C1; RF300trees/minleaf2; HistGB200iter/minleaf20; GBDT200/depth3/minleaf20; AdaBoost200/stump1/minleaf20; XGB200/leaves15; LGB200/minchild20/leaves15; Cat200/depth4; GRU/GraphLR.001/dropout.15/hidden64. Semua parameter lain sesuai grid. HistGB-E200/minleaf40; HistGB current-NaN200/minleaf20; LGB/XGB current-NaN konfigurasi baseline. Tiga seed11/23/37. Jika persis sama dengan kandidat/grid fit yang sudah ada, reuse fit beserta threshold validation; alias dicatat.

Transfer frozen lama meliputi9checkpoint inti, lima boosting tambahan×3seed, HistGB-currentNaN3, HistGB-E3, LightGBM-currentNaN3, XGBoost-currentNaN3 (36checkpoint). Skor validation lama terlebih dahulu harus mereproduksi skor frozen dengan toleransi1e-6 dan zero decision mismatch. Scaler/threshold tetap dari source masing-masing. Tidak menjalankan archived code.

## Freeze, evaluasi, analisis

Simpan semua kandidat, hasil per-epoch, parameter, versi, checksum input/helper/code/protocol, alias dan failure attempt. Freeze sebelum membuka kembali test untuk scoring tambahan satu kali. Tidak ada retuning/reselection setelah scoring tambahan. Freeze konfirmasi awal tidak diubah.

Seluruh checkpoint pilihan dan anchor (termasuk transfer) dinilai dengan actual-arrival dan complete-source pada trajectory test yang sama; complete-source hanya diagnosis offline, tidak digunakan train/tune. Semua model dibanding pada workload/split/label yang sama. Skor RF/HistGB full yang direuse wajib cocok dengan prediksi frozen konfirmasi sebelumnya.

Endpoint per keluarga dan seed: positive F1/precision/recall, accuracy/specificity/balancedaccuracy/MCC/AP/AUC, busy/all-S2 FPR, pre/post-S3 FPR, episode timely/late-only/miss, pre-alarm dan S2 run-level false alert. F1 menggunakan seluruh48keputusan S2/S3 berpasangan. Busy denominator mengikuti interval background per keluarga. Laporkan mean perdraw dan pooled FPR secara terpisah; constraint validation adalah pooled, bukan mean perdraw. Timely memerlukan keputusan positif pada window attack sebelum stop; belum sistem alarm online atau aturan hysteresis.

Rata-rata seed di dalam keluarga dahulu; seed/window bukan replikasi jaringan. Paired Priority−FIFO, complete−actual, strata burst/attacker, rentang perseed/perdraw dan jumlah pasangan membaik/sama/memburuk disimpan. Bootstrap95% deskriptif pada12keluarga per rate,10.000resample, seed1024; bukan konfirmasi populasi atau koreksi multiple comparisons. Ranking test hanya deskriptif. Rekomendasi validation untuk10keluarga LOCF dicatat, tanpa mengganti pilihan frozen lama. Semua hasil sempurna, buruk, zero-recall, error dan alias dilaporkan.

Biaya layanan dan delivery tetap berasal dari384run konfirmasi, tidak dihitung ulang sebagai replikasi jaringan baru. Pengukuran inference hanya batch offline di CPU laptop ini; bukan latency alarm deployment. Single topology, source timing, attacker locations yang terlihat di development dan cohort test yang telah diamati tetap batas.

## Resource dan keluaran

CPU dua thread/fit, fitting sequential, tidak bersamaan simulator. Driver maksimumdua jam; error/timeout menghasilkan status incomplete dengan artefak tersimpan, bukan membuang kandidat. Hasil di folder baru `all-models-20261024/`. Transfer lokal utamakan report, prediksi, checkpoint dan provenance, bukan menyalin ulang raw jaringan8GB. Tidak menulis kredensial. Paper/ZIPLaTeX belum direvisi.

### Catatan preflight sebelum fitting penelitian

Percobaan preflight-v1 gagal pada fixture HistGB dengan11kolom yang seluruh nilai latihnyaNaN: scikit-learn1.9.1/NumPy2.5.4 melaporkan `window shape cannot be larger than input array shape` pada binning. Tidak ada model penelitian yang dilatih pada percobaan itu. Source/protokol/log/receipt percobaan dipertahankan di `attempts/preflight-v1/`. Preflight-v2 menguji campuran finite/NaN dan mencatat kasus all-NaN sebagai batas runtime yang diketahui; sebelum fitting aktual wajib memverifikasi nol kolom latih all-NaN pada representasi current-NaN. Tidak menambal library, mengubah data, mengganti kandidat atau memakai hasil test untuk perbaikan ini.
