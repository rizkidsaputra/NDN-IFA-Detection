# Arsitektur dan reproduksi penelitian

Folder ini berisi dokumentasi metode, implementasi pilot, dan bukti agar kolaborator dapat membangun ulang tahap yang sudah diuji. Baca [konteks proyek](../PROJECT_CONTEXT.md) terlebih dahulu.

## Urutan baca

1. [01: Arsitektur](01-arsitektur.md), mencakup jaringan fisik, peran aplikasi dan alur pengukuran.
2. [02: Alasan desain dan literatur](02-alasan-desain-dan-literatur.md), mencakup alternatif, DOI dan hitungan studi.
3. [03: Reproduksi](03-reproduksi.md), dari clone, dependency terpin, smoke test, pilot, hingga replay.
4. [04: Kontrak detektor](04-kontrak-detektor.md), rancangan penelitian berikutnya yang belum menjadi source ML.
5. [05: Validasi dan batasan](05-validasi-dan-batasan.md), hasil acuan dan interpretasi kegagalan debugging.

## Isi folder

```text
architecture/
  01-arsitektur.md ... 05-validasi-dan-batasan.md
  diagrams/             diagram editable dan preview
  literature/           metadata 50 referensi, coding dan DOI
  scripts/              audit paket, recount studi, analisis graf
  ndnsim/
    config/              parameter pilot yang dibaca source
    scenarios/           aplikasi/agent/collector dan tree
    scripts/             bootstrap, run dan validator
    docs/                versi dependency dan patch
  evidence/
    reference-run/       raw CSV pilot penerimaan, bukan dataset final
    replay-*.json        ringkasan replay dan perbedaan audit
    package-sha256.json  manifest distribusi
```

`ndnsim/deps/` dan `ndnsim/runs/` dibuat di komputer pengguna dan tidak dilacak Git. Bukti acuan di `evidence/` diperlakukan sebagai read-only. Pemeriksaan reference-run memakai direktori sementara.

## Status implementasi

| Komponen | Status |
|---|---|
| Tree dan forwarding NDN | Diimplementasikan, divalidasi |
| Traffic consumer dan producer benign | Diimplementasikan, divalidasi |
| Agent seluruh router dan collector pull | Diimplementasikan, divalidasi |
| Audit jalur, cadence, timestamp dan counter | Diimplementasikan, divalidasi |
| GraphSAGE+GRU, mask/age, state keputusan kausal | Rancangan, belum diimplementasikan |
| Flooding dan gangguan report | Belum dijalankan |
| Dataset final dan evaluasi ML | Belum tersedia |

Paket publik tidak menyertakan PDF berhak cipta, salinan dependency/build, kredensial atau informasi akses mesin penulis. [Bibliografi](literature/REFERENCES.md) mengarahkan pembaca ke DOI dan sumber primer. Lisensi dependency mengikuti upstream masing-masing; lisensi menyeluruh untuk karya asli proyek belum ditetapkan.
