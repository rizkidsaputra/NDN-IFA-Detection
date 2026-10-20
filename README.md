# NDN-IFA Detection

Eksperimen deteksi **Interest Flooding Attack (IFA)** pada topologi NDN sepuluh router. Router mengirim telemetry sebagai paket Data NDN ke collector terpusat; telemetry yang benar-benar tersedia pada deadline kemudian dipakai oleh detector machine learning (ML).

**Arah penelitian, 20 Oktober 2026:** dampak gangguan report saat congestion serta manfaat dan trade-off prioritas pengiriman monitoring. Mulai dari [RQ, hasil FIFO-Priority dan status audit terbaru](RESEARCH_STATUS.md). Campaign ini berbeda dari evaluasi ML lokal sebelumnya.

## Status implementasi

ML **sudah diimplementasikan, dilatih, dan diuji** memakai dataset yang dihasilkan topologi ini. Integrasinya saat ini bersifat **offline**:

```text
topologi ndnSIM -> report NDN -> dataset kausal -> central detector ML -> evaluasi
```

Model belum berjalan sebagai alarm real-time di dalam proses ndnSIM. Jadi, jangan menulis bahwa router atau collector sudah melakukan inferensi online saat simulasi berlangsung.

[Dokumentasi ML dan topologi](ML_TOPOLOGY_PIPELINE.md) menjelaskan evaluasi lokal sebelumnya. Repository juga memiliki modul replay offline dan satu bundle GraphSAGE+GRU Mask+Age seed11; ini belum merupakan paket reproduksi lengkap campaign FIFO-Priority atau training ML.

## Berkas pengujian simulator

Tiga berkas yang sebelumnya sulit ditemukan berada di dalam `config/architecture/ndnsim/ifa-pilot/`, bukan di root repository:

- [Runner `scripts/run_ifa.sh`](config/architecture/ndnsim/ifa-pilot/scripts/run_ifa.sh)
- [Konfigurasi normal `ifa-base-00000-s1.json`](config/architecture/ndnsim/ifa-pilot/config/ifa-base-00000-s1.json)
- [Konfigurasi IFA ringan `ifa-atk1-00050-s1.json`](config/architecture/ndnsim/ifa-pilot/config/ifa-atk1-00050-s1.json)

Perintah berikut benar setelah masuk ke folder `ifa-pilot`:

```bash
cd config/architecture/ndnsim/ifa-pilot
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

Kedua konfigurasi ini adalah smoke test simulator, bukan test set ML final.

## Dokumentasi

- [Arah paper, dua RQ, FIFO-Priority dan batas bukti](RESEARCH_STATUS.md)
- [Alur topologi ke detector ML dan hasil final](ML_TOPOLOGY_PIPELINE.md)
- [Quick start dua pengujian simulator](IFA_QUICKSTART.md)
- [Panduan membangun lab](config/LAB_GUIDE.md)
- [Source dan konfigurasi IFA](config/architecture/ndnsim/ifa-pilot/README.md)
- [Hasil pilot dan perbaikan scheduler](config/architecture/ndnsim/ifa-pilot/docs/RESULTS.md)
- [Dokumentasi teknis dan literatur](config/architecture/README.md)

## Kesimpulan objektif

Pada campaign prioritization, Priority menjaga report tepat waktu dan memulihkan sensitivitas GRU pada workload yang diuji, dengan biaya goodput background terukur. False alarm tetap menjadi masalah, terutama pada model graf; telemetry lengkap belum menjamin deteksi yang spesifik terhadap IFA.

Telemetry router dapat mendeteksi aktivitas IFA dengan sangat baik pada domain simulasi tetap ini. Namun, GraphSAGE+GRU tidak mengungguli baseline tabular sederhana, dan hasil satu topologi tidak membuktikan generalisasi lintas topologi. Report yang hilang pada dataset muncul ketika background traffic aktif; hasil ini bukan bukti bahwa IFA sendirian menyebabkan report loss.
