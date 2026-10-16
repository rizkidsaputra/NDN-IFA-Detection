# 4. Kontrak detektor yang direncanakan

**Status: rancangan penelitian, belum kode model yang dapat dijalankan.** Dokumen ini menjaga agar teman dan AI memakai definisi yang sama ketika melanjutkan tahap ML. Pilot sekarang hanya mengukur dan mengirim report; tidak ada training, checkpoint, inference atau alarm.

## 4.1 Tugas utama dan alasan model

Tugas utama yang diusulkan adalah skor biner graf/episode IFA, untuk dibandingkan dengan arah supervised attack detection GNN4IFA. Lokalisasi attacker/prefix merupakan tugas tambahan dengan label dan metrik tersendiri. Skor graf tidak boleh dibandingkan langsung dengan angka node-wise tanpa penyesuaian definisi tugas. [GNN4IFA](https://doi.org/10.1109/EuroSP57164.2023.00043), [cloud-edge GAT](https://doi.org/10.1016/j.comnet.2026.112693).

GraphSAGE menjadi kandidat untuk agregasi tetangga router; GRU menjadi kandidat untuk history kausal. Alasan ilmiah yang perlu diuji adalah apakah hubungan spasial dan perubahan temporal menambah informasi dibanding model lebih sederhana, terutama ketika input di pusat tidak lengkap. Ini hipotesis, bukan kesimpulan dari pilot. [GraphSAGE](https://proceedings.neurips.cc/paper_files/paper/2017/hash/5dd9db5e033da9c6fb5ba83c7a7ebea9-Abstract.html), [GRU](https://doi.org/10.3115/v1/D14-1179).

## 4.2 Input yang tersedia dan yang belum diputuskan

Graf fisik ML memiliki node R1-R10 dan sembilan edge router. Node C/A/P/M tidak masuk graf model. Source pilot menyediakan sepuluh delta counter per window dan satu PIT snapshot per router:

1. Incoming Interest dan outgoing Interest.
2. Incoming Data dan outgoing Data.
3. Incoming NACK dan outgoing NACK.
4. Satisfied Interest dan unsatisfied Interest menurut counter NFD.
5. CS hit dan CS miss.
6. PIT entry count pada akhir window, sebagai snapshot.

Sepuluh delta merupakan jumlah kejadian pada interval, bukan sepuluh fitur per-interface GNN4IFA. Satisfied/unsatisfied dihitung pada event pipeline NFD, sehingga tidak selalu sama dengan jumlah request aplikasi dalam window yang sama. Counter mencakup telemetry dan manajemen startup. Jangan menghapus komponen tersebut tanpa menyatakan perubahan feature contract serta mengaudit dampaknya.

Dimensi input final belum dibekukan: perlu diputuskan fitur terpakai, normalisasi/rate transform, cakupan trafik, warm-up, dan representasi missing. Belum ada dasar mengklaim replikasi exact input GNN4IFA. Paper tersebut mencatat fitur per-interface dan tambahan per-router. [GNN4IFA, Tabel 1 dan bagian 5.1](https://doi.org/10.1109/EuroSP57164.2023.00043).

## 4.3 State kausal pada waktu keputusan

Untuk akhir window `t_k`, waktu keputusan yang diusulkan adalah `d_k = t_k + B_report`. `B_report` pada pilot adalah 250 ms, tetapi belum budget final. Pada `d_k`, hanya Data dengan arrival tidak melewati `d_k` yang boleh digunakan.

| Keadaan | Perlakuan rancangan |
|---|---|
| Report window k tiba sebelum/saat deadline | Gunakan sample window k; mask target=1 |
| Belum ada report window k pada deadline | Mask target=0; pengisian mengikuti varian baseline yang sama |
| Ada sample lama yang pernah diterima | Age dihitung dari `d_k - sample_end` terakhir yang sah |
| Belum pernah ada sample | Penanda no-history eksplisit dan initial fill yang dinyatakan |
| Report lama tiba setelah deadline | Tidak merevisi keputusan historis; update state berikutnya hanya jika sequence/sample time lebih baru dari state saat itu |
| Report duplikat/out-of-order | Jangan menggandakan feature atau menimpa sample yang lebih baru |

Node fisik tetap hadir ketika report missing. Mask bukan label router/link rusak. Age bukan waktu sejak polling dan bukan nomor sequence. Batas age/clipping, warm-up, imputasi dan update late report perlu dibekukan sebelum final test.

Pseudocode rancangan berikut belum diimplementasikan:

```text
on report Data arrival:
    validate run_id, router, sequence and sample_end
    retain the actual arrival timestamp
    keep only a causally newer observation as latest state

at decision deadline d_k:
    build target-window availability from arrivals <= d_k
    construct features using the selected common imputation rule
    build age and no-history indicators when that variant uses them
    preserve the ten physical router nodes and their adjacency
    compute graph/episode score using only causal history
    apply threshold and alarm confirmation fixed on validation data
    record decision, inference_complete and alert times separately
```

Dalam sistem riil, validasi keaslian Data memerlukan trust/security contract tersendiri. Signature sintetis simulator tidak membuktikan autentikasi report.

## 4.4 Bentuk model kandidat dan parameter yang masih terbuka

Spesifikasi kandidat awal dapat berbentuk GraphSAGE pada setiap window, readout graf, lalu GRU atas urutan readout dan head biner. Alternatifnya adalah state GRU per node sebelum readout. **Urutan readout/GRU belum dipilih sebagai arsitektur final** dan tidak boleh dianggap sudah diuji. Pilihan harus ditetapkan pada training/validation serta ditulis eksplisit dalam implementasi berikutnya.

Aggregator, jumlah layer, hidden dimension, panjang history, dropout, optimizer, learning rate, batch size, epoch, class weighting dan alarm rule belum dibekukan. Tidak ada nilai default yang boleh dipromosikan menjadi hasil atau standar paper. Menambah attention/decay/metode lain memerlukan pembanding dan alasan yang menguji fungsi tambahannya.

Varian minimum yang diusulkan:

| Varian | Input missing yang dibedakan | Tujuan ablation |
|---|---|---|
| Plain/LOCF | Pengisian kausal yang dinyatakan, tanpa mask/age tambahan | Acuan sederhana |
| Mask | Aturan pengisian sama, ditambah availability window target | Nilai informasi missing |
| Mask+Age | Aturan pengisian sama, mask dan age | Nilai umur sample terakhir |

No-history harus ditangani konsisten, termasuk ketika variant tidak diberi age. Learned decay opsional dan bukan bagian yang wajib. GRU-D telah membahas mask, interval waktu dan decay; temporal GNN juga membahas irregular data. [GRU-D](https://doi.org/10.1038/s41598-018-24271-9), [TGNN irregular data](https://doi.org/10.48550/arXiv.2302.08415).

## 4.5 Pembanding yang diperlukan

| Pembanding | Pertanyaan |
|---|---|
| GNN4IFA-SAD dilatih ulang dengan adaptasi diungkapkan | Manfaat terhadap model graf snapshot |
| GraphSAGE tanpa temporal component | Apakah GRU menambah informasi? |
| GRU/non-graf pada input sebanding | Apakah adjacency diperlukan pada tree kecil? |
| Threshold/statistik atau classifier ringan dekat R4 | Apakah titik agregasi dekat producer sudah memadai dengan biaya lebih rendah? |
| Central GAT dengan sliding window T043, bila dapat direproduksi | Perbandingan dengan prior art temporal-context terdekat |

Samakan report yang tersedia, split run, cadence dan false-alarm budget pada perbandingan utama. Pembanding producer-adjacent memakai lebih sedikit observasi dan biaya, sehingga perbedaan input harus diungkapkan. Jangan menyalin akurasi dari tabel paper lain sebagai baseline eksperimen lokal.

## 4.6 Protokol evaluasi dan pencegahan leakage

Pisahkan run menjadi training/validation/test sebelum membentuk sequence temporal. Fit normalisasi pada training saja. Pilih threshold, history, age clipping dan alarm confirmation pada validation, lalu bekukan. Replay seed sama bukan tambahan sampel independen. Posisi/rate yang ditahan untuk test harus sesuai dengan cakupan generalisasi yang diklaim.

Gunakan benign biasa, benign burst dan IFA, masing-masing dengan telemetry sehat dan terganggu bila eksperimen itu sudah diizinkan dan diimplementasikan. Pola missing tidak boleh identik dengan label serangan. Gangguan report independen mengukur robustness observasi; ia tidak membuktikan serangan menyebabkan gangguan.

Ukuran utama yang diusulkan adalah proporsi episode terdeteksi sebelum horizon `H` sejak onset pada false alarm yang sebanding. Laporkan miss dan episode tidak terdeteksi sampai akhir observasi, bukan TTD hanya pada deteksi sukses. Tambahkan false alarm per jam, availability/age, overhead dan dampak layanan. Angka horizon operasional, target detection rate dan budget false alarm belum final.

Empat hal berbeda: budget menunggu report, panjang history model, horizon sejak onset, dan delay pengiriman alert. Waktu inference tidak boleh diasumsikan nol untuk mengklaim waktu deteksi sistem online. Onset serangan harus berasal dari aktivitas serangan/ground truth yang independen, bukan threshold fitur yang juga menjadi input model.

## 4.7 Kriteria selesai tahap ML kelak

Sebelum menyebut detektor tervalidasi, diperlukan source yang dapat dijalankan, kontrak fitur/arrival yang diuji, ground truth terpisah, split per run, baseline sebanding, metrik episode dan bukti waktu komputasi. Paket saat ini belum memenuhi tahap itu dan tidak membuat klaim performa model.
