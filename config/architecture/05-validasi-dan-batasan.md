# 5. Bukti validasi dan batas klaim

## 5.1 Status penerimaan

Pilot `benign-tree-s1-r3` pada Mint tanggal 16 Oktober 2026 lulus **39 pemeriksaan**. Replay dengan seed, RNG run, source dan config sama juga lulus. Audit ulang di Windows tanggal 17 Oktober mengonfirmasi hasil yang sama. Paket ini menyertakan raw evidence satu run penerimaan serta ringkasan replay; ia bukan dataset final.

| Pemeriksaan | Hasil acuan |
|---|---|
| Jaringan runtime | 17 node, 16 link, connected tanpa siklus |
| Parameter efektif | Seluruh link 10 Mbps, delay 2 ms, queue 100p; cache 0 pada 17 node |
| C1 | 50 request, 50 Data, 25,600 byte payload |
| C2 | 50 request, 50 Data, 25,600 byte payload |
| C3 | 50 request, 50 Data, 25,600 byte payload |
| Laju aktual | Masing-masing 5 Interest/detik pada interval aktif 10 detik |
| Producer | 150 balasan P dengan nama cocok dan jalur paket lengkap |
| Agent | 13 sample/router, interval tetap 1 detik |
| Collector | 130 request dan 130 Data report, tanpa duplikasi input |
| Status report | 130 on_time, 0 late |
| NACK/timeout aplikasi | 0 pada consumer dan collector |
| Counter paket | Keenam delta Interest/Data/NACK masuk/keluar cocok dengan trace independen |
| Attacker | Tidak ada aplikasi aktif atau paket workload dari A1/A2 |

Sumber angka adalah [validation.json](evidence/reference-run/validation.json), [collector-received.csv](evidence/reference-run/collector-received.csv), log aplikasi dan [audit-packets.csv](evidence/reference-run/audit-packets.csv). Source aktif C++ dan validator disertakan terpisah dalam `ndnsim/`. Checksum menghubungkan salinan paket dengan source/config run penerimaan.

RTT report maksimum 16.5312 ms; selisih akhir window ke arrival maksimum 69.5312 ms. Seluruhnya memenuhi budget akhir window +250 ms untuk beban pilot ini. Total byte transmisi report, dijumlahkan pada setiap hop pada lapisan NDN, adalah 54,861 byte. Itu bukan payload unik atau ukuran framing link.

Command simulator melalui wrapper waf pada mesin acuan sekitar 0.55 detik dengan maksimum RSS proses terlapor 42,912 KiB. Ini berbeda dari 15 detik simulasi, bukan total RAM mesin, dan bukan benchmark training/inference. Resource tiap komputer teman dicatat pada run sendiri.

## 5.2 Apa yang sebenarnya diperiksa validator?

Validator memeriksa daftar node/link runtime terhadap config, parameter efektif, cache, count dan cadence consumer, balasan P serta jalur setiap Interest/Data. Untuk report, validator mencocokkan setiap sequence dengan sample immutable agent, menelusuri jalur ke M, memeriksa urutan waktu dan status deadline, lalu membandingkan enam delta counter paket dengan signal NFD dalam batas window yang sama.

Collector sendiri tidak membaca file-file ini. Pembandingan agent/trace dilakukan setelah simulasi selesai. Satisfied/unsatisfied, CS counters dan PIT tetap mengikuti definisi stack; tidak semua field memiliki ground truth independen yang sama dengan keenam counter paket. Cadence/transport yang lolos belum membuktikan validitas seluruh fitur untuk model ML.

Pemeriksaan paket pada distribusi publik mengulang validator terhadap salinan sementara reference-run. Dengan demikian, file asli tidak ditulis ulang dan checksum evidence tetap terjaga. Cara ini menguji artefak yang didistribusikan, bukan mensimulasikan ulang jaringan.

## 5.3 Replay dan nondeterminisme control plane

Hasil [replay-validation.json](evidence/replay-validation.json) mencatat input identik dan trace workload identik. Semua CSV selain audit mentah identik. Kedua audit memiliki 8,484 baris; 644 baris berbeda pada nama command manajemen lokal bertanda tangan dan 244 dari baris itu juga berbeda pada panjang encoding. Seluruh perbedaan berada di luar prefix benign/report. [Rincian perbedaan](evidence/replay-audit-differences.json).

Maka klaim yang didukung adalah reproduksibilitas workload, counter, payload dan arrival pada replay konfigurasi ini. Tidak ada klaim bahwa setiap byte control plane atau waktu mesin harus identik. Replay tidak menambah jumlah run independen statistik.

## 5.4 Kegagalan sebelumnya dan diagnosis

Run diagnosis r1 menghasilkan timeout meskipun Interest mencapai service dan Data dibuat. Penyebabnya adalah FreshnessPeriod=0 bersama MustBeFresh=true pada implementasi `Interest::matchesData` commit ini. Perbaikan aplikasi adalah freshness 1000 ms; tidak ada pengurangan kapasitas atau penambahan beban untuk mengatur loss. Source run penerimaan memuat perbaikan tersebut.

Run r2 sudah mengirim 150 Data benign dan 130 report, tetapi audit window pertama belum cocok karena counter NFD mencakup command manajemen internal yang tidak diterbitkan tracer L3Protocol biasa. R3 mengaudit seluruh face NFD termasuk face aplikasi baru. Counter tidak dikurangi dan window tidak dibuang. Kegagalan itu adalah pelajaran instrumentasi, bukan hasil serangan atau pembuktian congestion.

Log diagnosis lengkap tetap berada dalam proyek pengembangan; distribusi publik menyertakan run penerimaan dan uraian masalah agar paket ringkas. Jangan menggabungkan r1/r2/r3 menjadi dataset serangan atau menyebutnya tiga pengulangan statistik independen.

## 5.5 Yang belum dibuktikan

- IFA benar-benar mencapai target dan menghasilkan tekanan PIT/dampak layanan.
- Serangan menyebabkan report terlambat/hilang, atau koridor tertentu menjadi bottleneck.
- Ketahanan GraphSAGE+GRU, manfaat mask/age, atau keunggulan terhadap baseline.
- Generalisasi ke topologi lain, banyak producer, beban riil, trust model riil atau jaringan nyata.
- Biaya sampling/inference/admin alert dalam sistem online.

Pilot menggunakan cache nonaktif, payload tetap dan nama unik; ia tidak merepresentasikan seluruh perilaku cache/dynamic content pada studi pembanding. Signature sintetis merupakan mekanisme simulator, bukan evaluasi autentikasi. Karena itu keberhasilan plumbing tidak dipromosikan menjadi hasil keamanan atau novelty.

## 5.6 Cara melaporkan reproduce dari komputer teman

Simpan commit repository, versi OS/toolchain, commit dependency, config/source hash, seed/RNG run, command, exit code dan seluruh log run. Nyatakan apakah build dilakukan dari checkout bersih atau memakai dependency yang sudah ada. Bandingkan indikator penerimaan, lalu jelaskan perbedaan yang ditemukan. Jangan mengganti nilai reference-run atau mengubah parameter hanya agar angka tampak identik.

Jika memakai AI, sertakan konteks portabel dan instruksikan AI memisahkan verified result, planned method dan unresolved issue. Setiap hasil baru masuk sebagai catatan run baru beserta bukti, bukan penggantian diam-diam terhadap sejarah validasi.
