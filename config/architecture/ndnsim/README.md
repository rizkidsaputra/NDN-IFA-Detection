# Implementasi pilot ndnSIM

Source `scenarios/benign-tree.cpp`, konfigurasi `config/benign-pilot.json` dan validator berasal dari run penerimaan yang disertakan. Tidak ada source model ML atau generator serangan aktif pada paket ini.

Panduan lengkap: [reproduksi](../03-reproduksi.md). Setelah dependency tersedia, jalankan dari folder ini:

```bash
bash scripts/run_pilot.sh config/benign-pilot.json
```

Dependency dibangun dalam `deps/`, hasil baru dalam `runs/`, dan log build dalam `docs/`. Ketiganya tidak disertakan dalam commit. `docs/stack-lock.json` mencatat versi acuan dan patch pada checkout bersih. Script bootstrap paket menambahkan dependensi eksplisit Python dan GNU time; selain itu mengikuti langkah build yang sudah diverifikasi. Script tidak boleh dijalankan pada direktori `deps/ns-3` yang sudah berisi pekerjaan lain.
