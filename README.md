# NDN-IFA Detection

Lab simulasi NDN dengan sepuluh router, pengukuran router, collector terpusat, dan uji Interest Flooding Attack (IFA).

**Mulai dari [Panduan membuat lab](config/LAB_GUIDE.md).** Panduan mencakup Ubuntu/Mint, VM, spesifikasi awal, instalasi, trafik normal dan IFA ringan.

## Ingin langsung menjalankan dua pengujian IFA?

Baca [Quick start IFA](IFA_QUICKSTART.md). Tiga berkas yang dipakai berada di dalam folder `config/architecture/ndnsim/ifa-pilot/`, bukan di root repository:

- [Runner `scripts/run_ifa.sh`](config/architecture/ndnsim/ifa-pilot/scripts/run_ifa.sh)
- [Konfigurasi normal `ifa-base-00000-s1.json`](config/architecture/ndnsim/ifa-pilot/config/ifa-base-00000-s1.json)
- [Konfigurasi IFA ringan `ifa-atk1-00050-s1.json`](config/architecture/ndnsim/ifa-pilot/config/ifa-atk1-00050-s1.json)

Perintah berikut baru benar setelah masuk ke folder `ifa-pilot`:

```bash
cd config/architecture/ndnsim/ifa-pilot
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

Source normal dan IFA sudah tersedia. Belum ada detector/ML atau dataset final. Kenaikan PIT tidak otomatis berarti layanan lumpuh atau report hilang.

- [Source dan konfigurasi IFA](config/architecture/ndnsim/ifa-pilot/README.md)
- [Hasil pilot dan perbaikan scheduler](config/architecture/ndnsim/ifa-pilot/docs/RESULTS.md)
- [Dokumentasi teknis dan literatur](config/architecture/README.md)
