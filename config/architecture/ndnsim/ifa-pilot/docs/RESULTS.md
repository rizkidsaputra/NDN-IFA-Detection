# Hasil pilot dan perbaikan scheduler

Diuji pada Mint acuan, 17 Oktober 2026. **Dua kontrol burst panjang kini selesai**, setelah perbaikan scheduler. Belum ada detector/ML, dataset final atau klaim keunggulan model.

## Masalah yang ditemukan

Adapter scheduler ndn-cxx pada commit terpin menjadwalkan wakeup baru saat event lebih awal dimasukkan, tetapi assignment EventId tidak membatalkan wakeup lama. Wakeup berlebih terus menjadwalkan wakeup lain. Profil menemukan lebih dari 100 juta event pada sekitar 6,7 detik simulasi. Ini masalah alat simulasi, bukan bukti report loss atau router kehabisan CPU riil.

Patch `ndn-cxx-scheduler-single-wakeup.patch` membatalkan wakeup yang masih tertunda sebelum menggantinya. Patch bersifat fungsional dan berbeda dari dua patch include header awal. Commit dependency tetap sama; patch dicatat dan disertakan secara eksplisit.

Uji regresi sebelum/sesudah: 128 callback terurut membutuhkan 8256/128 event simulator; pembatalan idempotent 4223/64; cancel-all 127/0; reentrant zero-delay/context 2/2. Callback, timestamp dan konteks benar pada kedua versi. Keempat batas event setelah patch PASS. Source pengujian ada di `../checks/`.

## Hasil setelah patch

Laju, durasi, link, lifetime dan deadline tidak dikurangi. Batas mesin tetap 180 detik. Semua 12 kondisi yang disertakan selesai dan PASS; baseline 44 pemeriksaan, kondisi tambahan 46.

| Run | Data normal | Report on-time | PIT R1 puncak | Queue Drop | Waktu mesin (detik) |
|---|---:|---:|---:|---:|---:|
| `fixed-base` | 345/345 | 280/280 | 1 | 0 | 00.53 |
| `fixed-burst-2000` | 345/345 | 280/280 | 64 | 0 | 03.84 |
| `fixed-burst-3000` | 292/345 | 280/280 | 1049 | 4316 | 05.30 |
| `fixed-burst-500` | 345/345 | 280/280 | 16 | 0 | 01.30 |
| `fixed-burst-5000` | 286/345 | 280/280 | 3048 | 14321 | 07.61 |
| `fixed-burst-short` | 340/345 | 280/280 | 1500 | 1341 | 01.24 |
| `fixed-ifa-12000` | 345/345 | 280/280 | 12001 | 0 | 12.81 |
| `fixed-ifa-2000` | 345/345 | 280/280 | 2001 | 0 | 02.27 |
| `fixed-ifa-50` | 345/345 | 280/280 | 51 | 0 | 00.56 |
| `fixed-ifa-500` | 345/345 | 280/280 | 501 | 0 | 00.96 |
| `fixed-ifa-500-L4` | 345/345 | 280/280 | 2001 | 0 | 00.99 |
| `fixed-ifa-5000` | 345/345 | 280/280 | 5001 | 0 | 05.10 |

PIT puncak berasal dari probe audit 100 ms, bukan fitur yang langsung dibaca collector. RSS/waktu mesin merupakan penggunaan proses pada host uji, bukan resource router riil atau benchmark VM minimum.

Burst 3000/s dan 5000/s yang awalnya mencapai batas mesin 180 detik kini selesai sekitar 5,30 dan 7,61 detik. Run IFA 12000/s sebelumnya sekitar 175,62 detik, kini sekitar 12,81 detik. Ini observasi host acuan, bukan jaminan waktu pada komputer lain.

## Pemeriksaan bahwa trafik tetap sama

Sepuluh kondisi yang sudah selesai sebelum patch dibandingkan menggunakan source/config sama. Seluruh CSV aplikasi/report/PIT/drop serta trace paket workload identik. Command manajemen lokal bertanda tangan dikecualikan dari klaim trace identik. Pilot benign asli 15 detik juga kembali lolos 39 pemeriksaan dan conformance. Ini pemeriksaan kesetaraan setelah perubahan dependency, bukan run statistik independen.

Percobaan lama yang dihentikan tetap disimpan sebagai incomplete; tidak diubah menjadi PASS. Rerun menggunakan folder baru. Raw log besar dan log akses mesin tidak dipublikasikan. [Ringkasan terstruktur](../evidence/scheduler-fix-validation.json) menyimpan hash patch/input dan hasil aktual. Raw evidence IFA 50/s disertakan terpisah agar validator bisa dijalankan offline; raw kondisi besar disimpan pada workspace eksperimen.

## Arti hasil

Seluruh kondisi selesai masih menerima 280/280 report tepat waktu. IFA menambah PIT, tetapi tidak mengganggu layanan normal pada konfigurasi ini. Burst sah besar mengganggu layanan normal, dengan telemetry tetap sehat. Belum ada bukti IFA menyebabkan report missing/late. Status ini tidak membuktikan akurasi detector, novelty, representativitas seluruh NDN atau hasil pada Ubuntu/VM yang belum diuji.
