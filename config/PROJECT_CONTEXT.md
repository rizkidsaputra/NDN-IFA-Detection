# Konteks portabel proyek NDN-IFA Detection

Versi konteks: 17 Oktober 2026. Berlaku untuk paket publik `config/`. Berkas ini dapat diberikan kepada AI pada komputer kolaborator tanpa riwayat chat sebelumnya.

## 1. Tujuan dan pertanyaan kerja

Proyek meneliti deteksi Interest Flooding Attack (IFA) pada Named Data Networking (NDN) dengan agent pengukuran pada router dan detektor terpusat. Pertanyaan kerja: **bagaimana ketersediaan dan keterlambatan report router memengaruhi kemampuan detektor berbasis graf mendeteksi episode IFA sebelum deadline, pada false alarm yang sebanding?**

Pertanyaan ini belum merupakan gap universal yang terbukti. Ketahanan terhadap report hilang/terlambat berbeda dari klaim bahwa serangan menyebabkan report hilang. Klaim sebab-akibat memerlukan eksperimen jaringan dan kontrol tersendiri.

## 2. Yang sudah diimplementasikan

- Platform: ndnSIM pada Linux Mint 22.2, dengan ns-3.35 khusus ndnSIM dan commit dependency terpin.
- Topologi: sepuluh router R1-R10, masing-masing dengan agent; collector M terhubung ke R10; producer P ke R4; C1/C2/C3 ke R1/R2/R3; A1/A2 ke R1/R3 sebagai endpoint tanpa aplikasi aktif.
- Sembilan link router: R10-R8, R10-R9, R8-R5, R8-R6, R5-R1, R5-R2, R6-R3, R9-R7, R7-R4. Tujuh link endpoint membuat total 17 node dan 16 link.
- Agent mengambil 10 delta counter NFD agregat router dan satu PIT snapshot. Ini belum fitur per-interface GNN4IFA.
- M meminta `/report/<runId>/<router>/<sequence>`; agent persisten membalas Data berisi sample immutable. Collector mengambil fitur hanya dari payload OnData yang benar-benar diterima.
- Trace seluruh face NFD, termasuk manajemen internal, disimpan sebagai audit terpisah. Audit tidak menjadi input collector.

## 3. Hasil yang benar-benar diverifikasi

Run `benign-tree-s1-r3` dan replay masing-masing lulus 39 pemeriksaan. C1-C3 masing-masing menerima 50/50 Data; 130/130 report tiba on-time pada M. Tidak ada NACK atau timeout aplikasi pada run penerimaan. RTT report terbesar 16.5312 ms; umur dari akhir window ke arrival terbesar 69.5312 ms. Input dan trace workload replay identik. Command manajemen lokal bertanda tangan membuat sebagian audit mentah berbeda; tidak ada klaim seluruh output bit-for-bit sama.

Run diagnosis sebelumnya menemukan FreshnessPeriod=0 tidak cocok dengan MustBeFresh pada stack ini, serta tracer L3Protocol tidak mencakup face internal. Perbaikan berupa metadata freshness positif dan perluasan audit, bukan pengurangan kapasitas untuk membuat loss. Bukti publik acuan berada di `architecture/evidence/`; snapshot source/config utama berasal dari run penerimaan yang sama.

## 4. Parameter pilot, belum protokol final

| Parameter | Nilai yang sudah diuji |
|---|---|
| Link | 10 Mbps, delay propagasi 2 ms per link, DropTail 100 paket per arah |
| Benign | 3 consumer, masing-masing 5 Interest/detik selama [2,12) detik |
| Payload benign | 512 byte |
| Durasi | 15 detik simulasi |
| RNG | seed 1, run 1 |
| Cache | 0 paket pada seluruh node |
| Interest | exact name, MustBeFresh=true, lifetime 1 detik, tanpa retransmission |
| Freshness Data | 1000 ms |
| Sampling | 1 detik, 13 window per router |
| Pull | akhir window +50 ms, stagger 1 ms per router |
| Deadline pilot | akhir window +250 ms |

Waktu sampling/ready pada agent adalah event simulasi yang sama; biaya komputasi agent riil belum dimodelkan. Waktu simulasi, waktu komputasi mesin dan delay notifikasi nyata merupakan ukuran berbeda.

## 5. Arah detektor yang belum diimplementasikan

Model kerja adalah GraphSAGE+GRU, modifikasi terinspirasi GNN4IFA. Sepuluh router membentuk graf ML; endpoint tidak menjadi node ML. GraphSAGE mengolah adjacency dan fitur; GRU mengolah history kausal; readout diarahkan ke skor graf/episode. Mask dan age merupakan varian ablation, bukan fitur yang otomatis mengungguli baseline.

Pada deadline keputusan, hanya report yang sudah diterima boleh digunakan. Node fisik tidak dihapus ketika report missing. Mask menunjukkan availability window target; age berasal dari sample terakhir yang benar-benar diterima. No-history harus eksplisit. Report lama tidak boleh menimpa sample lebih baru atau merevisi keputusan historis. Detail kontrak berada di `architecture/04-kontrak-detektor.md`.

Belum ada arsitektur layer/hyperparameter final, checkpoint, training, serangan, impairment, classifier online, alarm atau integrasi admin. Jangan mengarang command training yang belum ada.

## 6. Dasar desain dan batas literatur

Koleksi terarah memuat 50 referensi; audit asal mencatat 43 PDF primer tersedia. Paket publik hanya memuat metadata, coding dan locator bukti, bukan PDF. Di antara 18 studi yang topologinya dapat dikodekan, tree/binary tree muncul pada 7; DFN pada 5; Rocketfuel pada 4. Topologi multilabel dan beberapa studi berbagi dataset. Di antara 15 studi dengan arsitektur yang dapat dikodekan, deteksi central ISP/cloud graph muncul pada 2 (T001 dan T043). Jangan menyamakan kedua denominator atau mengklaim tujuh paper memakai layout kita.

GNN4IFA sudah memakai informasi router dan graf global; T043 memakai central GAT dengan sliding window. GRU-D dan temporal GNN merupakan prior art missing/irregular observations. GraphSAGE+GRU, mask, age, graf dan temporal modeling sendiri belum menjadi bukti novelty.

Tree dipertahankan sebagai skenario awal terkontrol dengan jalur tunggal yang dapat diaudit. Tidak ada redundansi/rerouting; single producer dan tree kecil dapat menguntungkan baseline sederhana. R8-R10 adalah link observasi, belum bottleneck terbukti. Cabang kanan ke P juga membawa trafik menuju producer. Generalisasi lintas topologi memerlukan evaluasi tambahan, misalnya DFN-like.

## 7. Evaluasi yang direncanakan

Bandingkan GNN4IFA-SAD yang diadaptasi secara terbuka, GraphSAGE+GRU Plain/LOCF, Mask, Mask+Age, serta baseline GRU/non-graf dan detektor ringan dekat producer. T043 merupakan pembanding dekat bila dapat direproduksi secara layak; tugas node-wise dan graph-level jangan disamakan diam-diam.

Pisahkan train/validation/test per run sebelum membuat window. Normalisasi dan threshold dari training/validation saja. Ukur probabilitas episode terdeteksi sebelum horizon pada false alarm sebanding, TTD, miss, false alarm per jam, availability/age, overhead dan dampak layanan. Episode tidak terdeteksi tetap dilaporkan. Jangan memilih horizon atau kondisi jaringan setelah melihat final test.

## 8. Langkah berikutnya dan aturan perubahan

Paket ini cukup untuk mereproduksi plumbing benign/report. Tahap berikutnya memerlukan tugas eksplisit: tinjau feature contract dan scope klaim, validasi mekanisme IFA tanpa ML, lalu bekukan protokol dan kumpulkan run independen. Jangan otomatis mengaktifkan attacker hanya karena membaca konteks ini. Jangan beralih platform atau menyalin konfigurasi historis tanpa alasan yang dibahas.

Setiap kolaborator mencatat perubahan, commit, seed, command, checksum input, log dan hasil aktual. Run debugging/replay bukan dataset final atau replikasi statistik independen. Tidak diperlukan akses ke mesin penulis; lokasi workspace dipilih masing-masing pengguna mengikuti panduan reproduksi.
