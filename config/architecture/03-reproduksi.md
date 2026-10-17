# 3. Panduan reproduksi untuk kolaborator

Bagian ini mencatat pilot benign awal. Untuk langkah lab dan IFA terbaru, baca [panduan utama](../LAB_GUIDE.md) serta [hasil IFA dan scheduler](ndnsim/ifa-pilot/docs/RESULTS.md).

## 3.1 Apa yang akan direproduksi?

Targetnya adalah tree benign dan transport report dasar yang telah diuji, bukan keseluruhan penelitian ML. Keberhasilan berarti konfigurasi berjalan, tiga consumer menerima Data, setiap router melapor melalui jaringan, dan validator mengonfirmasi count, jalur, cadence, timestamp serta delta counter. Model deteksi tidak perlu diinstal pada tahap ini.

Lingkungan acuan adalah Linux Mint 22.2 (Ubuntu noble), GCC 13.3.0, Python 3.12.3, Boost 1.83, OpenSSL 3.0.13 dan SQLite 3.45.1. Mesin acuan memiliki i5-7300U, 2 core/4 thread, RAM sekitar 16 GB. Spesifikasi ini catatan lingkungan yang berhasil, bukan hasil studi minimum resource. Komputer Linux lain mungkin dapat dipakai, tetapi harus mencatat versi dan memvalidasi ulang. Windows dapat menjalankan audit Python, sedangkan simulator pada paket ini diuji di Mint.

Siapkan koneksi Internet untuk source/dependency dan hak sudo untuk paket sistem. Gunakan lokasi kerja tanpa spasi untuk command wrapper waf. Tidak diperlukan alamat SSH, username atau filesystem pribadi penulis. Semua path berikut relatif terhadap clone Anda.

## 3.2 Clone dan pemeriksaan paket

```bash
git clone https://github.com/rizkidsaputra/NDN-IFA-Detection.git
cd NDN-IFA-Detection/config
python3 architecture/scripts/verify_package.py
python3 architecture/scripts/recount_literature.py
python3 architecture/scripts/analyze_topology.py
```

Simpan commit repository yang dipakai dengan `git rev-parse HEAD`. `verify_package.py` memeriksa hash distribusi dan menilai ulang bukti reference-run dalam direktori sementara, sehingga bukti acuan tidak ditimpa. Pemeriksaan ini memakai standard library Python; tidak membutuhkan ndnSIM, PyTorch, Excel atau PDF paper.

## 3.3 Build stack terpin dan smoke test

```bash
cd architecture/ndnsim
bash scripts/bootstrap_mint.sh
```

Script melakukan langkah berikut secara berurutan:

1. Memasang compiler, Git, pkg-config, Python, GNU time, Boost, OpenSSL dan SQLite development headers.
2. Clone ns-3 khusus ndnSIM dan checkout commit pada lock file.
3. Clone ndnSIM, checkout commit terpin, lalu mengambil submodule NFD/ndn-cxx/websocketpp yang ditentukan parent commit.
4. Menerapkan dua patch kompatibilitas berupa include header saja.
5. Configure optimized, menonaktifkan Python bindings, mengaktifkan contoh, dan membangun target `ndn-simple` dengan dua pekerjaan paralel.
6. Menjalankan contoh upstream `ndn-simple`.

Script menolak menimpa `deps/ns-3` yang sudah ada. Jika terhenti, periksa log dan checkout yang telah dibuat sebelum melanjutkan manual; jangan menghapus pekerjaan lain atau mengulang dengan force. Contoh upstream yang selesai exit 0 adalah smoke test. Jumlah Data aplikasi pada contoh itu tidak diaudit oleh paket; audit trafik terperinci dilakukan pada pilot berikutnya.

| Komponen | Commit acuan |
|---|---|
| ns-3.35 khusus ndnSIM | `1b3bab9b6dba5f1e616c0b286eb889e9ce3d5d59` |
| ndnSIM, tag ndnSIM-2.9-NFD-22.02 | `90d50396654dabad54b6979f2dc8fa929ade544c` |
| NFD | `361b381b9b552ff3341aa160858bea1d470d2122` |
| ndn-cxx | `2b51e5796415b5d41fe268b35250b9453f16d3d6` |
| websocketpp | `ac4e021333675fc80b96eb7be45d218581c897e2` |

Patch ns-3 menambahkan `<cstdint>` pada tiga header. Patch ndn-cxx menambahkan `<optional>` pada scheduler. Tidak ada patch algoritme forwarding. Mengambil ns-3 generik terbaru atau NFD sistem terbaru tidak setara dengan mengambil kombinasi di atas. Dokumentasi upstream menjelaskan kebutuhan branch khusus serta submodule: [ndnSIM Getting Started](https://ndnsim.net/current/getting-started.html).

## 3.4 Jalankan pilot

Masih dari folder `config/architecture/ndnsim`:

```bash
bash scripts/run_pilot.sh config/benign-pilot.json
```

Script menyalin source proyek ke scratch dengan ekstensi `.cc` yang dikenali ns-3.35, membangun target `benign-tree`, membuat direktori run baru, menyimpan source/config/validator dan hash input, menjalankan simulasi, lalu melakukan validasi. Ia menolak menimpa direktori run yang sudah ada.

Output pertama berada di `runs/benign-tree-s1-r3/`. Pilihan run ID mempertahankan nama run penerimaan agar paket dapat dibandingkan dengan acuan. Run baru di komputer teman tetap harus dicatat sebagai eksekusi baru; waktu mesin dan detail manajemen lokal tidak harus identik dengan mesin acuan.

```bash
cat runs/benign-tree-s1-r3/exit-code.txt
cat runs/benign-tree-s1-r3/validation.json
```

Target acuan: exit 0, 39 pemeriksaan PASS, C1-C3 masing-masing 50 request/50 Data, 130 report on-time. Berkas `links.csv` dan `cache-limits.csv` merekam nilai efektif dari simulator, bukan hanya argumen JSON. Jika hasil berbeda, simpan semua output dan diagnosis sebelum mengubah parameter.

## 3.5 Replay dan run independen

Untuk input dan nama paket sama dengan direktori hasil berbeda:

```bash
bash scripts/run_pilot.sh config/benign-pilot.json benign-tree-s1-r3-replay
python3 scripts/check_replay.py runs/benign-tree-s1-r3 runs/benign-tree-s1-r3-replay --output runs/replay-comparison.json
```

Replay menguji reproduksibilitas workload; ia bukan replikasi independen statistik. Counter/report dan trace prefix workload acuan identik, sedangkan beberapa nama dan panjang command manajemen lokal bertanda tangan berbeda. Jangan menetapkan raw audit byte-for-byte sebagai satu-satunya kriteria ketika perbedaannya berasal dari control plane lokal.

Untuk run independen di tahap eksperimen berikutnya, salin JSON, ganti runId dan RNG run/seed secara eksplisit sesuai rancangan. Jangan mengubah seed sambil tetap menyebutnya replay. Jangan menjalankan serangan hanya karena konfigurasi memiliki node A1/A2; paket saat ini menolak `attackers_active=true`.

## 3.6 Berkas hasil dan cara membacanya

| Berkas | Isi |
|---|---|
| `config.json`, `scenario.cpp`, `validator.py` | Snapshot input yang benar-benar dijalankan |
| `input-sha256.txt`, `sha256.json` | Hash input dan hasil run |
| `nodes.csv`, `links.csv`, `fib.txt` | Node, face/link dan route setelah service siap |
| `client-C*.csv`, `producer.csv` | Request, Data, NACK, timeout dan balasan P |
| `agent-R*.csv` | Sample lokal dan balasan service report, khusus audit |
| `client-M.csv`, `collector-received.csv` | Request collector dan report yang benar-benar diterima |
| `audit-packets.csv` | Signal seluruh face NFD; bukan input collector |
| `validation.json` | PASS/FAIL setiap pemeriksaan dan ringkasan metrik |
| `resources.txt`, `wall-start/end.txt` | Resource/waktu mesin, berbeda dari timestamp simulasi |

Timestamp CSV memakai detik simulasi. `sampleBoundary` merupakan penanda urutan audit, bukan paket. Counter delta berunit jumlah paket per window; PIT adalah jumlah entry pada akhir window. Jangan menyebut keduanya rate yang sama atau menganggap PIT pressure sama dengan queue congestion.

## 3.7 Troubleshooting yang sudah memiliki bukti

| Gejala | Pemeriksaan/perbaikan |
|---|---|
| `uint8_t` atau `std::optional` tidak dikenali pada stack | Pastikan commit benar dan kedua patch diterapkan tepat satu kali |
| Target `benign-tree` tidak ditemukan | Scratch memakai `.cc`; gunakan script paket, bukan menyalin `.cpp` langsung |
| Interest mencapai service, Data dibuat tetapi tidak kembali | Periksa MustBeFresh dan FreshnessPeriod; stack ini menolak fresh-request terhadap freshness 0 |
| Counter window awal tidak cocok dengan tracer | Periksa cakupan face internal NFD; source paket mengaudit seluruh face, bukan hanya L3Protocol |
| NACK NoRoute | Audit FIB, prefix dan face; jangan menyimpulkannya sebagai congestion |
| Report belum ready | Bandingkan cadence, sequence, window_end dan waktu request |
| Run berhenti/terputus | Simpan sebagai interrupted dan ulangi dengan label baru; resume belum tersedia |
| RAM/CPU build terlalu tinggi | Pertahankan batas dua pekerjaan atau turunkan; jangan mengubah link agar masalah mesin tampak sebagai hasil jaringan |

## 3.8 Batas verifikasi portabilitas

Build asli dan pilot telah berjalan di Mint acuan. Paket publik diperiksa untuk kelengkapan path, checksum source yang sama, sintaks shell, hitungan literatur, analisis graf dan audit ulang raw evidence tanpa simulator. Paket tidak mengklaim bahwa script bootstrap baru telah dibangun ulang dari checkout kedua pada setiap OS atau komputer teman. Hasil reproduce milik kolaborator harus disertai versi dan lognya sendiri.
