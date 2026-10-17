# Lab NDN dan IFA

Baca **[Panduan membuat lab](LAB_GUIDE.md)** untuk langkah dari instalasi sampai hasil PASS. Ubuntu 24.04/Mint dapat dipakai langsung atau melalui satu VM; spesifikasi kecil dalam panduan merupakan rekomendasi praktis, belum benchmark minimum.

| Kebutuhan | Buka |
|---|---|
| Memasang dan menjalankan lab | [Panduan utama](LAB_GUIDE.md) |
| Source IFA dan perintah uji | [Pilot IFA](architecture/ndnsim/ifa-pilot/README.md) |
| Hasil yang sudah diuji | [Hasil IFA dan scheduler](architecture/ndnsim/ifa-pilot/docs/RESULTS.md) |
| Arsitektur dan literatur rinci | [Dokumentasi teknis](architecture/README.md) |

Lab normal, agent/collector dan mekanisme IFA sudah diuji pada Mint acuan. Belum ada detector, training ML, dataset final atau hasil keunggulan metode. Reproduksi Ubuntu/VM harus melewati pengujian PASS di mesin masing-masing.

Hasil acuan benign awal tetap utuh di `architecture/evidence/reference-run/`. Dependency, build dan hasil percobaan baru tidak dimasukkan ke Git.
