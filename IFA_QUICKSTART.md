# Quick Start: Menjalankan Baseline dan IFA Ringan

Dokumen ini dapat langsung disalin ke Outline. Tujuannya menjelaskan lokasi berkas dan dua perintah pengujian tanpa mengharuskan pembaca menelusuri seluruh repository.

Dokumen ini khusus untuk **smoke test simulator**. Untuk penjelasan bagaimana hasil topologi dipakai oleh detector ML, baca [Implementasi ML pada Topologi NDN](ML_TOPOLOGY_PIPELINE.md). Dua run di bawah bukan train/test set ML final.

## Lokasi berkas

Ketiga berkas **sudah tersedia di branch `main`**, tetapi tidak berada di root repository.

| Kegunaan | Path di repository | Tautan GitHub |
|---|---|---|
| Runner simulasi | `config/architecture/ndnsim/ifa-pilot/scripts/run_ifa.sh` | [Buka runner](config/architecture/ndnsim/ifa-pilot/scripts/run_ifa.sh) |
| Kondisi pembanding tanpa attacker aktif | `config/architecture/ndnsim/ifa-pilot/config/ifa-base-00000-s1.json` | [Buka konfigurasi baseline](config/architecture/ndnsim/ifa-pilot/config/ifa-base-00000-s1.json) |
| IFA ringan 50 Interest/detik | `config/architecture/ndnsim/ifa-pilot/config/ifa-atk1-00050-s1.json` | [Buka konfigurasi IFA](config/architecture/ndnsim/ifa-pilot/config/ifa-atk1-00050-s1.json) |

Struktur singkatnya:

```text
NDN-IFA-Detection/
└── config/
    └── architecture/
        └── ndnsim/
            └── ifa-pilot/
                ├── config/
                │   ├── ifa-base-00000-s1.json
                │   └── ifa-atk1-00050-s1.json
                └── scripts/
                    └── run_ifa.sh
```

## Perintah lengkap dari awal

Jalankan di Ubuntu 24.04 atau Linux Mint 22.x:

```bash
git clone https://github.com/rizkidsaputra/NDN-IFA-Detection.git
cd NDN-IFA-Detection/config/architecture/ndnsim
bash scripts/bootstrap_mint.sh

cd ifa-pilot
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

`bootstrap_mint.sh` hanya diperlukan untuk pemasangan baru. Jika simulator sudah berhasil dipasang dari repository ini, masuk langsung ke folder `ifa-pilot` dan jalankan dua perintah terakhir.

## Jika repository sudah pernah di-clone

Clone lama mungkin belum memuat dokumentasi terbaru. Perbarui branch `main`:

```bash
cd NDN-IFA-Detection
git pull --ff-only origin main
git branch --show-current
git rev-parse --short HEAD
```

Pastikan branch yang tampil adalah `main`. Lalu periksa berkas:

```bash
test -f config/architecture/ndnsim/ifa-pilot/scripts/run_ifa.sh &&
test -f config/architecture/ndnsim/ifa-pilot/config/ifa-base-00000-s1.json &&
test -f config/architecture/ndnsim/ifa-pilot/config/ifa-atk1-00050-s1.json &&
echo "Semua file IFA tersedia"
```

Pesan terakhir hanya akan dicetak jika ketiga pemeriksaan sebelumnya berhasil.

## Apa perbedaan kedua konfigurasi?

`ifa-base-00000-s1.json` adalah pembanding 30 detik tanpa attacker aktif. `ifa-atk1-00050-s1.json` memakai topologi dan trafik normal yang sama, lalu mengaktifkan A1 pada laju 50 Interest/detik selama detik 5 sampai sebelum detik 10. Totalnya 250 Interest serangan unik.

Keduanya memakai seed dan parameter jaringan yang sama agar perbandingannya terkontrol. Konfigurasi IFA ringan menaikkan PIT, tetapi pada hasil acuan tidak menghilangkan Data normal maupun report monitoring.

## Hasil yang diharapkan

| Pemeriksaan | Baseline | IFA ringan |
|---|---:|---:|
| Status validator | PASS | PASS |
| Request serangan mencapai P | 0 | 250 dari 250 |
| Puncak PIT R1 | 1 | 51 |
| Data normal diterima | 345/345 | 345/345 |
| Report tepat waktu | 280/280 | 280/280 |

PASS berarti simulasi dan bukti keluarannya konsisten dengan konfigurasi. PASS tidak berarti serangan berhasil melumpuhkan jaringan dan tidak berarti model ML telah mendeteksi serangan.

## Di mana hasil run disimpan?

Runner membuat folder berikut:

```text
config/architecture/ndnsim/ifa-pilot/runs/<run-id>/
```

Baca `validation.json` terlebih dahulu. Jika terjadi kegagalan, periksa `simulator.log`, `resources.txt`, dan `exit-code.txt`. Runner menolak menimpa hasil lama. Untuk pengulangan, berikan label baru:

```bash
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json latihan-kedua
```

## Catatan keamanan dan batas klaim

Eksperimen berjalan seluruhnya di simulator pada laptop. Script tidak menyerang jaringan Internet. Uji ini adalah pilot terkontrol, bukan dataset final dan bukan bukti bahwa IFA selalu menyebabkan congestion, kegagalan layanan, atau report loss.
