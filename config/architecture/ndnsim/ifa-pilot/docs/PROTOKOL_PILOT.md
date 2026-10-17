# Konfigurasi pilot yang dipakai

Ini kontrak pilot v1 untuk memeriksa mekanisme dan pengukuran. Belum protokol dataset final atau evaluasi ML. Semua konfigurasi yang disertakan telah selesai pada stack Mint terpin dengan patch single-wakeup.

| Komponen | Konfigurasi |
|---|---|
| Topologi | 10 router dan 7 endpoint; tree yang sama dengan pilot normal |
| Link | 10 Mbps, delay 2 ms, antrean 100 paket per arah |
| Durasi | 30 detik simulasi |
| Consumer normal | C1-C3, masing-masing 5 Interest/s pada [2,25), 345 request/run |
| Konten normal | Nama unik, payload 512 byte, CS=0, freshness 1000 ms |
| Pengukuran router | 10 delta counter agregat NFD dan satu PIT snapshot, setiap 1 s |
| Collector | 28 window, 280 poll; offset 50 ms + stagger 1 ms/router |
| Deadline report | Akhir window +250 ms; input hanya payload report yang tiba |
| InterestLifetime | 1 s, tanpa retransmission aplikasi; satu ablation IFA memakai 4 s |
| IFA | A1 di R1, prefix berute ke silent service P, nama unik, [5,10) |
| Laju IFA | 50/500/2000/5000/12000 Interest/s; tambahan 500/s lifetime 4 s |
| Burst sah | B1 di C1, dijawab P, 500/2000/3000/5000 Interest/s pada [5,10) |
| Diagnosis burst pendek | 5000 Interest/s pada [5,5.5), bukan pasangan durasi setara |
| RNG | Seed 1/run 1, stream aplikasi eksplisit; CBR, pengacakan hanya nonce |

## Data yang disimpan

- `client-C*.csv` dan `flow-*.csv`: waktu request, Data, NACK dan timeout aplikasi.
- `sink.csv` dan `producer.csv`: bukti Interest mencapai aplikasi P dan Data normal dibuat.
- `agent-R*.csv`: sample router dan balasan report, untuk audit.
- `collector-received.csv`: request, arrival, status on-time/late dan payload yang benar-benar diterima.
- `audit-packets.csv`, `nodes.csv`, `links.csv`, `fib.txt`: paket, jalur, parameter efektif dan route.
- `pit-probe.csv`: snapshot 100 ms untuk audit, bukan input collector atau detector.
- `queue-drops.csv`: Drop antrean aktual; tidak otomatis mengidentifikasi paket report tertentu.
- Snapshot source/config/validator/patch, checksum, waktu mesin dan penggunaan proses.

Aktivitas IFA ditentukan dari jadwal dan log pengirim, sedangkan dampak diukur terpisah dari delivery/timeout/RTT/resource. Kenaikan PIT tidak menjadi definisi label serangan. Prefix, run ID, jadwal dan tracer tidak boleh menjadi jalan pintas fitur ML. Counter report masih agregat, termasuk trafik telemetry/manajemen; belum sama dengan fitur per-interface GNN4IFA.

Deskripsi role endpoint pada konfigurasi mewarisi baseline; aktivasi aplikasi yang sebenarnya ditentukan oleh `attackers_active` dan `extra_flows`, lalu diperiksa dari log request dan receipt sink. Jangan memakai teks role pada `nodes.csv` sebagai ground truth aktivitas serangan.

Tidak ada batas admission PIT atau biaya CPU router riil yang dimodelkan. Patch scheduler menghilangkan wakeup berulang, bukan menambahkan kapasitas kecil atau mengubah trafik agar terjadi loss. Semua run tetap menyimpan seed/config dan input yang benar-benar dipakai.

## Sebelum dataset final

Perlu menyelesaikan definisi fitur pembanding dan label waktu, variasi workload independen, pembagian train/validation/test per run, serta skenario report sehat/terganggu. Pola CBR satu seed di sini dan replay bukan replikasi statistik independen. Gangguan report buatan belum diimplementasikan dan kelak harus disebut fault injection terpisah. Jangan menganggap IFA telah menyebabkan report hilang hanya karena PIT meningkat atau layanan terganggu.
