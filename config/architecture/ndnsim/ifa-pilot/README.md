# Pilot IFA tanpa detector

Ikuti [panduan utama](../../../LAB_GUIDE.md) untuk memasang lab. Folder ini menggunakan dependency di `../deps/ns-3`; tidak memerlukan simulator kedua.

## Mulai dengan beban ringan

Dari folder ini. Jika posisi terminal masih di root repository, masuk dahulu dengan `cd config/architecture/ndnsim/ifa-pilot`:

```bash
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

Tautan langsung berkas:

- [`scripts/run_ifa.sh`](scripts/run_ifa.sh)
- [`config/ifa-base-00000-s1.json`](config/ifa-base-00000-s1.json)
- [`config/ifa-atk1-00050-s1.json`](config/ifa-atk1-00050-s1.json)

Lihat juga [quick start dari root repository](https://github.com/rizkidsaputra/NDN-IFA-Detection/blob/main/IFA_QUICKSTART.md).

Keduanya diharapkan PASS, dengan 345/345 Data normal dan 280/280 report tepat waktu. Pada IFA ringan, 250 Interest unik mencapai aplikasi silent di P tanpa memperoleh Data. Detektor/ML belum dipasang.

## Konfigurasi dan data

- [Protokol pilot](docs/PROTOKOL_PILOT.md): parameter yang dipakai dan data yang dicatat.
- [Hasil dan perbaikan scheduler](docs/RESULTS.md): hasil aktual, batas klaim, dan kontrol burst panjang.
- `config/`: baseline, enam kondisi IFA, empat burst sah panjang dan satu burst sah pendek; semuanya telah diuji pada stack Mint dengan patch scheduler.
- `evidence/reference-run/`: raw evidence IFA ringan yang dapat diaudit offline; bukan dataset final.

Hasil baru disimpan di `runs/` dan tidak masuk Git. Untuk mengulang input yang sama tanpa menimpa hasil:

```bash
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json latihan-kedua
```

Runner menerapkan patch scheduler secara idempotent hanya pada commit ndn-cxx yang sesuai. Default build satu pekerjaan dan batas waktu mesin 180 detik. `BUILD_JOBS` dan `RUN_TIMEOUT_S` dapat diubah secara eksplisit; nilainya disimpan pada `run-settings.json`. Jangan menyamakan timeout proses dengan report loss.

Pemeriksaan scheduler opsional setelah stack terpasang:

```bash
bash scripts/run_scheduler_check.sh
```

Semua kasus harus PASS. Pemeriksaan itu tidak mengirim serangan ke jaringan nyata.
