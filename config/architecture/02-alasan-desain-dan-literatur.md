# 2. Alasan desain dan dukungan literatur

## 2.1 Apa yang dihitung?

Dokumentasi memakai koleksi terarah 50 referensi yang disaring dalam proyek. Audit asal mencatat 43 PDF primer tersedia dan 7 belum tersedia. Status umumnya pemeriksaan sebagian full text; memiliki PDF tidak berarti seluruh paper telah dibaca lengkap. Paket publik menyediakan metadata, coding dan locator, bukan PDF.

Unit hitung adalah **studi/record yang dikodekan**, bukan jumlah eksperimen independen dan bukan seluruh publikasi NDN. Satu paper dapat memakai beberapa topologi. Beberapa studi memakai dataset atau konfigurasi terkait. Studi fitur dan dataset juga dapat masuk denominator topologi tanpa menjadi implementasi IDS online. Tanggal label katalog adalah 16 Oktober 2026; konsolidasi audit dan dokumentasi dituntaskan 17 Oktober 2026.

Denominator dibedakan karena pertanyaannya berbeda:

| Dimensi | Eligible | Aturan |
|---|---:|---|
| Topologi | 18 studi | Bentuk topologi dapat dikodekan; multilabel |
| Arsitektur deteksi/koordinasi | 15 studi | Keluarga desain dapat dikodekan; satu kategori per record pada audit ini |
| Titik observasi/pengambilan fitur | 17 studi | Tidak otomatis sama dengan lokasi hosting classifier |
| Dapat dikodekan pada topologi dan arsitektur | 14 studi | Irisan dua himpunan eligible di atas |

Seluruh angka dapat dihitung ulang dari [usage-ranking.json](literature/usage-ranking.json) dan [CSV bukti](literature/usage-ranking-evidence.csv), menggunakan `python architecture/scripts/recount_literature.py` dari folder `config/`. Script memeriksa konsistensi ID dan denominator. Ini mereproduksi hasil coding; untuk menilai ulang coding, pembaca harus memeriksa sumber primer pada lokasi yang dicatat.

## 2.2 Berapa studi menggunakan tree?

| Topologi | n/18 | Persentase | ID studi |
|---|---:|---:|---|
| Tree/binary tree | 7/18 | 38.9% | T001,T002,T003,T012,T013,T022,T023 |
| DFN/DFN-like | 5/18 | 27.8% | T001,T002,T003,T017,T043 |
| Rocketfuel ISP | 4/18 | 22.2% | T001,T008,T010,T018 |
| Grid | 3/18 | 16.7% | T004,T014,T021 |
| Small mesh | 2/18 | 11.1% | T019,T020 |

Kategori tambahan adalah chain, random geometric, scale-free dan small/SPOTIFAI yang bentuknya tidak ditegaskan ulang. Persentase tidak dijumlahkan menjadi 100% karena topologi multilabel. Tree merupakan kategori terbanyak dalam subset ini, tetapi 38.9% bukan mayoritas dan tidak menunjukkan tujuh layout identik dengan R1-R10.

Tujuh studi tree berikut menyediakan jejak DOI serta lokasi bukti:

| ID dan studi | DOI | Bukti yang dikodekan dan batasnya |
|---|---|---|
| T001 GNN4IFA (2023) | [10.1109/EuroSP57164.2023.00043](https://doi.org/10.1109/EuroSP57164.2023.00043) | Bagian 5.2 dan Fig.1 memakai small binary tree, DFN, Rocketfuel; small 18 node termasuk user dan producer, bukan tree 17 node kita |
| T002 Fast Detection and Traceback-Based Mitigation (2025) | [10.1007/s42979-024-03648-w](https://doi.org/10.1007/s42979-024-03648-w) | Fig.4 PDF p.7, tree/DFN; deteksi router/interface lokal, bukan collector graf yang sama |
| T003 ML-Based IFA Detection in Vehicular NDN (2023) | [10.3390/electronics12183870](https://doi.org/10.3390/electronics12183870) | Bagian 3.1, Figs.3-4 PDF pp.7-8; konteks VNDN dan peran koordinasi berbeda |
| T012 Detection of CIFA using SMOTEBoost and LSTM (2025) | [10.1016/j.cose.2024.104251](https://doi.org/10.1016/j.cose.2024.104251) | Bagian 3.2/Fig.3 PDF pp.3-4, binary tree; model collusive attack tidak identik dengan threat model kerja kita |
| T013 Collaborative Federated Learning (2026) | [10.1016/j.comnet.2025.111926](https://doi.org/10.1016/j.comnet.2025.111926) | Bagian 3.2-3.5 PDF pp.3-5, tree dan edge clients; agregasi parameter bukan raw-report collector identik |
| T022 Performance Evaluation of Significant Feature (2025) | [10.28991/esj-2025-09-05-07](https://doi.org/10.28991/esj-2025-09-05-07) | Metode/dataset dan Fig.3; studi fitur, bukan bukti IDS online dengan transport report yang sama |
| T023 EWMA-Based Mitigation Scheme (2024) | [10.1007/978-981-97-5606-3_14](https://doi.org/10.1007/978-981-97-5606-3_14) | Bagian 3-4, Fig.4 PDF bab p.7; bab buku, bukan satu buku penuh sebagai satu paper empiris |

T043 memakai label small/SPOTIFAI dan DFN pada bagian yang diperiksa. Bentuk small tersebut tidak dikodekan sebagai binary tree tanpa penegasan bentuk. Karena itu T043 tidak ditambahkan diam-diam ke tujuh studi tree.

## 2.3 Berapa studi menggunakan pendeteksi terpusat?

| Keluarga arsitektur | n/15 | ID |
|---|---:|---|
| Lokal router/node, termasuk kerja sama dan cascade | 8/15 | T002,T004,T011,T012,T018,T019,T021,T023 |
| Koordinasi peran RSU/gateway/controller | 3/15 | T003,T014,T017 |
| Central ISP/cloud graph detection | 2/15 | T001,T043 |
| Federated collaborative learning | 2/15 | T013,T016 |

Kategori ini merupakan ringkasan coding proyek, bukan taksonomi universal; beberapa istilah melibatkan koordinasi training sekaligus lokasi inference. Central graph bukan kategori terbanyak. Keberadaan controller juga tidak selalu berarti seluruh fitur mentah diolah sebagai graf terpusat.

T001 memusatkan informasi router untuk GNN, sedangkan T043 menempatkan GAT dan konteks sliding window di cloud. Keduanya mendukung bahwa desain graf terpusat memiliki preseden, sekaligus menjadi pembanding yang harus dihadapi, bukan bukti bahwa rancangan kita baru. [GNN4IFA](https://doi.org/10.1109/EuroSP57164.2023.00043), [cloud-edge GAT](https://doi.org/10.1016/j.comnet.2026.112693).

**Irisan eksplisit tree dan central graph pada coding saat ini adalah satu studi, T001, dari 14 studi yang eligible pada kedua dimensi.** Angka itu bukan pencarian lengkap atas semua kombinasi di literatur. Belum ada record yang kita verifikasi memakai persis layout sepuluh router ini beserta GraphSAGE+GRU dan kontrak pull/deadline yang sama. Tidak terverifikasi bukan berarti tidak pernah ada.

## 2.4 Mengapa mempertahankan tree?

Tree dipilih sebagai skenario terkontrol awal. Jalur tunggal memudahkan penelusuran Interest menuju producer, Data kembali melalui PIT, dan report menuju M. Ketika sebuah permintaan gagal, jalurnya dapat diaudit tanpa terlebih dahulu memisahkan perubahan rute. Ini alasan desain eksperimen, bukan hasil bahwa tree lebih akurat untuk deteksi.

Tree juga memberi kontinuitas terbatas dengan benchmark GNN4IFA dan beberapa studi pada tabel di atas. Namun, layout kita asimetris, memiliki producer pada endpoint P di R4, dan memakai beban pilot ringan. Ia bukan replikasi small topology SPOTIFAI atau threat model seluruh studi tersebut. [GNN4IFA, bagian 5.2](https://doi.org/10.1109/EuroSP57164.2023.00043).

Untuk pertanyaan report availability, tree membuat hubungan koridor observasi jelas: enam report melewati R8-R10. Gangguan pada koridor tersebut berpotensi menghasilkan pola observasi berkelompok. Ini hipotesis yang harus diuji; belum ada gangguan pada pilot. Putus link fisik juga memutus layanan consumer kiri menuju P, sehingga tidak dapat disebut gangguan report saja.

Kelemahannya adalah tidak ada redundansi/rerouting, variasi struktur terbatas, dan semua consumer menuju satu producer. Baseline sederhana dekat producer mungkin sudah cukup. Bila klaim diperluas ke generalisasi lintas topologi, tambahkan evaluasi DFN/DFN-like atau topologi lain yang direncanakan; tujuh studi pemakai tree tidak menghapus kebutuhan tersebut.

## 2.5 Mengapa agent router dan detektor pusat?

Agent memberi pengamatan lokal yang terkait dengan node graf, sementara pusat menggabungkan korelasi antarlokasi dan waktu. GNN4IFA memberi preseden informasi router untuk deteksi global; T043 memberi preseden cloud GAT dengan data router dan sliding window. Ini dasar yang sesuai untuk pertanyaan korelasi spasial, tetapi manfaat pengumpulan seluruh router harus dibandingkan dengan biaya dan baseline non-graf. [GNN4IFA](https://doi.org/10.1109/EuroSP57164.2023.00043), [cloud-edge GAT](https://doi.org/10.1016/j.comnet.2026.112693).

Lokasi M di R10 adalah kompromi hop terjauh pada tree aktual: maksimum 4 hop termasuk link akses M. R8 memberi total hop lebih rendah tetapi maksimum 5. Belum ada optimisasi delay berbasis antrean. CBIDM membahas penempatan controller untuk tujuan minimum total delay; tujuan itu tidak otomatis sama dengan minimum maksimum hop kita. [CBIDM](https://doi.org/10.1007/s42979-024-03350-x).

Observasi producer-adjacent pada T008 dan T020 menjadi alasan untuk menguji detektor ringan di dekat R4. Ia menggunakan cakupan/input lebih sempit dan harus dilaporkan sebagai pembanding berbiaya berbeda, bukan perbandingan feature-matched. [MF-RF](https://doi.org/10.1049/ise2.12100), [RBF/CIFA](https://doi.org/10.1145/3663408.3665819).

## 2.6 Mengapa pull Interest/Data?

Pull mempertahankan transport asli NDN: client mengirim Interest ke agent, lalu menerima hasil pengukuran sebagai Data. NDN Measurement Framework memberikan preseden interaksi ini, tetapi merupakan poster/framework awal, bukan bukti ketahanan IFA atau keunggulan pull. Pilot kita memilih sampling periodik terlebih dahulu dan immutable result per sequence; detail itu adalah keputusan implementasi proyek. [NMF, bagian 2.1 dan 2.3](https://doi.org/10.1145/3125719.3132113).

CBIDM berbeda: status router dibawa dalam Interest dan balasan Data berisi instruksi controller. Maka paper tersebut tidak boleh disebut implementasi raw-feature pull yang identik. T001/T043 mendukung pemusatan analisis, tetapi bagian yang diperiksa tidak menetapkan protokol wire pull yang kita gunakan. [CBIDM](https://doi.org/10.1007/s42979-024-03350-x).

Sampling 1 detik memiliki preseden pada T001/T043; T011 memakai window 500 ms. Tidak ada dasar menyebut 1 detik sebagai standar universal. Offset poll 50 ms, stagger 1 ms dan deadline 250 ms adalah asumsi pilot; ketiganya harus dianalisis sensitivitasnya sebelum evaluasi final. [T001](https://doi.org/10.1109/EuroSP57164.2023.00043), [T043](https://doi.org/10.1016/j.comnet.2026.112693), [T011](https://doi.org/10.1016/j.cose.2024.104124).

## 2.7 Mengapa GraphSAGE+GRU dan mask/age?

GraphSAGE mengagregasi fitur lingkungan node, sehingga sesuai sebagai kandidat untuk ketergantungan antartetangga pada graf router. GRU menyediakan state sekuensial untuk history. Kesesuaian konseptual ini belum membuktikan manfaat pada IFA, dan tidak membenarkan hyperparameter tertentu tanpa validation. GraphSAGE asli tidak dievaluasi sebagai detektor IFA, sedangkan GRU berasal dari konteks pemodelan sekuens yang berbeda. [GraphSAGE, publikasi primer](https://proceedings.neurips.cc/paper_files/paper/2017/hash/5dd9db5e033da9c6fb5ba83c7a7ebea9-Abstract.html), [GRU](https://doi.org/10.3115/v1/D14-1179).

Mask membedakan fitur yang benar-benar teramati dari imputasi; age menyatakan seberapa lama sample terakhir. GRU-D sudah menggunakan mask, interval waktu dan decay untuk missing values, dan temporal GNN juga membahas pengamatan irregular. Maka kombinasi istilah ini bukan klaim pertama. Varian Plain/LOCF, Mask dan Mask+Age harus dibandingkan dengan preprocessing serta report availability yang sama. [GRU-D](https://doi.org/10.1038/s41598-018-24271-9), [Temporal Graph Neural Networks for Irregular Data](https://doi.org/10.48550/arXiv.2302.08415).

Pertanyaan tersulit untuk rancangan ini adalah: **apakah adjacency dan age benar-benar menambah kemampuan deteksi tepat waktu dibanding GRU atau threshold sederhana pada input yang sebanding?** Itulah yang harus dijawab eksperimen, bukan diputuskan dari jumlah paper pendukung.

## 2.8 Batas narasi penelitian

Narasi yang dapat dipertahankan saat ini: tree dipakai untuk studi awal yang dapat ditelusuri, transport report aktual sudah bekerja, dan evaluasi berikutnya akan menilai keputusan ketika observasi yang tiba tidak lengkap/terlambat. Belum ada bukti metode lebih akurat, lebih cepat, lebih robust, atau bahwa IFA menyebabkan report loss. Ablation arrival/deadline belum ditemukan pada bagian T001/T043 yang diperiksa, tetapi screening ini tidak membuktikan gap universal.

Lihat [bibliografi lengkap beserta locator](literature/REFERENCES.md). File tersebut membedakan dukungan topologi, dukungan desain analisis, transport pengukuran, dan pembanding dekat, agar paper tidak hanya dikumpulkan sebagai daftar dukungan umum.
