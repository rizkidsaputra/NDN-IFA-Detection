# NDN-IFA Detection: paket konteks dan reproduksi

Paket ini membangun ulang **pilot ndnSIM benign dan pengiriman report router** yang telah divalidasi. Tree berisi 10 router, 7 endpoint terpisah, dan 16 link. Collector menerima report sebagai Data NDN melalui jaringan simulasi. Model GraphSAGE+GRU adalah arah penelitian berikutnya dan **belum diimplementasikan dalam paket ini**.

Dokumentasi disusun 17 Oktober 2026. Validasi simulator acuan dilakukan 16 Oktober dan audit mirror dituntaskan 17 Oktober 2026. Semua panduan dapat dibaca tanpa berkas di luar folder `config/`.

## Mulai dari sini

| Kebutuhan | Berkas |
|---|---|
| Memberi konteks yang sama ke AI | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) dan [AGENTS.md](AGENTS.md) |
| Memahami keseluruhan paket | [architecture/README.md](architecture/README.md) |
| Topologi, komponen, dan alur report | [Arsitektur](architecture/01-arsitektur.md) |
| Alasan tree, collector, dan model; jumlah studi serta DOI | [Dasar desain dan literatur](architecture/02-alasan-desain-dan-literatur.md) |
| Memasang dan menjalankan ulang | [Panduan reproduksi](architecture/03-reproduksi.md) |
| Rancangan detektor yang belum diimplementasikan | [Kontrak detektor](architecture/04-kontrak-detektor.md) |
| Hasil acuan dan batas klaim | [Validasi](architecture/05-validasi-dan-batasan.md) |
| Daftar pustaka dengan locator bukti | [Bibliografi](architecture/literature/REFERENCES.md) |

## Pemeriksaan cepat tanpa simulator

Setelah clone repository, jalankan dari folder `config/` dengan Python 3.10 atau lebih baru:

```bash
python architecture/scripts/verify_package.py
python architecture/scripts/recount_literature.py
python architecture/scripts/analyze_topology.py
```

Pemeriksaan pertama mencocokkan checksum, menilai ulang bukti acuan dalam direktori sementara, dan memeriksa agar dokumentasi tidak bergantung pada berkas pribadi di luar paket. Pemeriksaan tersebut tidak menggantikan build dan run ndnSIM pada komputer Anda.

## Hasil acuan

- Pilot dan replay masing-masing lulus 39 pemeriksaan.
- C1, C2, C3 masing-masing menerima 50 Data dari 50 request.
- M menerima 130 dari 130 report, semuanya sebelum deadline pilot.
- Tidak ada NACK atau timeout aplikasi pada run penerimaan.

Hasil tersebut berlaku untuk pilot yang disertakan. Belum ada hasil flooding, gangguan report, training ML atau dataset final. Angka pemakai tree pada literatur merupakan hitungan subset yang dikodekan, bukan pembuktian bahwa tree merupakan arsitektur terbaik.

## Untuk kolaborator dan AI

Baca konteks sebelum mengubah source. Bedakan hasil yang sudah diuji, keputusan desain, usulan berikutnya, dan hal yang belum diketahui. Jangan mengubah kapasitas atau beban untuk memaksakan hilangnya report. Simpan setiap run baru dengan ID berbeda dan catat perubahan parameter. Gunakan folder ini sebagai bahan GitHub; dependency build, hasil run baru dan kredensial berada di luar berkas yang dilacak.
