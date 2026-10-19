# Implementasi ML pada Topologi NDN

Dokumen ini adalah pintu masuk utama untuk memahami hubungan antara simulator, telemetry router, dataset, dan detector ML. Ringkasnya: **ML sudah memakai data dari topologi sepuluh router, tetapi belum ditanam sebagai inferensi real-time di dalam ndnSIM.**

## 1. Apa yang sudah diimplementasikan?

Alur penelitian yang sudah selesai adalah:

```text
Consumer / attacker
        |
        v
Topologi NDN 10 router -----> Producer
        |
        | setiap router mengukur kondisi lokal
        v
Report berbentuk Data NDN menuju collector M
        |
        | hanya report yang tersedia saat deadline 250 ms
        v
Dataset snapshot graf per detik
        |
        v
Central detector ML
        |
        v
Probabilitas / keputusan aktivitas IFA
```

Dengan demikian, frasa yang tepat untuk paper adalah:

> Detector ML terpusat dilatih dan dievaluasi secara offline menggunakan telemetry kausal yang dikumpulkan dari topologi NDN sepuluh router.

Frasa yang belum boleh dipakai adalah:

> Model telah di-deploy di collector dan mendeteksi serangan secara real-time selama simulasi.

Deployment online itu masih pekerjaan lanjutan.

## 2. Di mana letak ML terhadap topologi?

Topologi fisik yang dipakai model adalah:

```text
M - R10
     ├── R8
     │   ├── R5
     │   │   ├── R1
     │   │   └── R2
     │   └── R6
     │       └── R3
     └── R9
         └── R7
             └── R4 - P
```

- R1–R10 menjadi sepuluh node graf.
- Sambungan ant-router menjadi edge graf yang tetap.
- Setiap router menghasilkan sebelas nilai pengukuran utama per jendela waktu.
- Collector M meminta report melalui protokol NDN; report dikirim sebagai paket Data NDN.
- Detector pusat menyusun snapshot `10 router x fitur` dan urutan waktu sepanjang 20 jendela.
- GraphSAGE memproses hubungan ant-router, sedangkan GRU memproses perubahan ant-waktu.

Consumer meminta konten normal kepada producer P. Attacker mengirim Interest unik yang memiliki rute tetapi sengaja tidak memperoleh Data. Background traffic juga merupakan trafik NDN dan dipakai untuk membuat kondisi benign yang lebih sulit, termasuk congestion pada sebagian workload.

## 3. Data apa yang masuk ke model?

Satu keputusan jaringan dibuat setiap satu detik. Untuk setiap router, model memakai sebelas measurement field dari report yang telah tersedia secara kausal. Contohnya mencakup jumlah Interest/Data, ukuran PIT, PIT yang puas/tidak puas, NACK, dan cache hit/miss.

Aturan pentingnya:

- Label berasal dari aktivitas IFA pada jendela keputusan, bukan dari nama konfigurasi yang diberikan kepada model.
- Waktu absolut, identitas run, kondisi eksperimen, jumlah serangan, tracer masa depan, dan metadata audit tidak dipakai sebagai fitur.
- Jika report belum tersedia pada deadline 250 ms, input memakai last observation carried forward (LOCF).
- Varian `Mask` menambahkan penanda tersedia/tidak tersedia.
- Varian `Mask+Age` juga menambahkan umur sampel terakhir.
- Normalisasi hanya dipelajari dari train set.
- Urutan tidak pernah menyeberang dari satu run ke run lain.

Ini disebut dataset **kausal** karena detector hanya melihat informasi yang sudah sampai pada saat keputusan dibuat, bukan report masa depan.

## 4. Dataset dan pembagian evaluasi

Dataset final lokal v3+v4 berisi:

| Bagian | Jumlah |
|---|---:|
| Workload family | 31 |
| Run simulasi | 124 |
| Snapshot jaringan | 36.952 |
| Baris router | 369.520 |
| Jendela positif IFA | 4.586 |

Setiap workload family memiliki empat kondisi berpasangan: normal, IFA, background-only, dan IFA+background. Pembagian dilakukan berdasarkan **family**, bukan dengan mengacak baris atau jendela:

| Partisi | Family | Run | Snapshot |
|---|---:|---:|---:|
| Train | 19 | 76 | 22.648 |
| Validation | 8 | 32 | 9.536 |
| Test | 4 | 16 | 4.768 |

Cara ini mengurangi kebocoran akibat jendela berurutan yang sangat mirip. Test set hanya dibuka satu kali setelah preprocessing, model, threshold, checkpoint, dan kode dibekukan serta di-hash.

## 5. Model yang dibandingkan

Eksperimen tidak hanya menguji GraphSAGE+GRU. Pembanding berikut wajib agar penilaian objektif:

- threshold PIT mean dan PIT max;
- logistic regression;
- Random Forest;
- XGBoost;
- logistic regression berbasis R4 saja;
- GRU tanpa graf;
- GraphSAGE tanpa komponen temporal;
- GraphSAGE+GRU Plain, Mask, dan Mask+Age.

Model dipilih menggunakan family-macro PR-AUC pada validation. Threshold dipilih di validation dan tidak diubah setelah melihat test. Model neural dilaporkan sebagai rerata dan simpangan baku lima seed, bukan seed terbaik saja.

## 6. Hasil one-shot test

Hasil utama test family-disjoint:

| Model | Family-macro PR-AUC | Family-macro F1 | FPR | Episode recall |
|---|---:|---:|---:|---:|
| Logistic regression | 1,0000 | 0,9926 | 0,0014 | 1,0000 |
| XGBoost, dipilih sebelum test | 0,9989 | 0,9912 | 0,0010 | 1,0000 |
| GraphSAGE+GRU Plain, 5 seed | 0,9967 ± 0,0017 | 0,9602 ± 0,0160 | 0,0079 | 1,0000 |
| GRU-only Plain, 5 seed | 0,9968 ± 0,0006 | 0,9705 ± 0,0030 | 0,0053 | 1,0000 |
| Static GraphSAGE, 5 seed | 0,9981 ± 0,0010 | 0,9258 ± 0,0205 | 0,0097 | 1,0000 |

Interpretasinya:

1. Telemetry topologi ini cukup untuk mendeteksi aktivitas IFA pada domain simulasi yang diuji.
2. GraphSAGE+GRU bekerja, tetapi tidak lebih baik daripada baseline tabular sederhana.
3. Mask dan sample age tidak memperbaiki metrik pemilihan validation dibanding Plain.
4. Skor tinggi bukan otomatis bukti model baru lebih unggul; audit menunjukkan tugas pada satu domain ini memang mudah dipisahkan.

## 7. Hubungan background traffic, congestion, dan report loss

Background adalah trafik NDN tambahan yang sah. Pada workload tertentu, background menimbulkan congestion nyata dan mengganggu jalur monitoring.

Dari 369.520 report yang dibuat:

- 365.975 tersedia tepat waktu;
- 3.545 tidak pernah diterima sampai run berakhir;
- 0 report datang terlambat melewati deadline 250 ms.

Semua report yang tidak diterima muncul pada kondisi dengan background: 1.712 pada background-only dan 1.833 pada IFA+background. Tidak ada report hilang pada normal atau IFA tanpa background. Karena itu, data ini menunjukkan **background/congestion dapat membuat report tidak tersedia**, tetapi tidak menunjukkan bahwa IFA sendirian menyebabkan report loss.

## 8. Dua jenis pengujian yang jangan tertukar

### Smoke test simulator

Perintah berikut memeriksa bahwa skenario normal dan IFA ringan dapat berjalan:

```bash
cd config/architecture/ndnsim/ifa-pilot
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

Ini menghasilkan satu run simulator dan bukti seperti PIT, Data consumer, dan report collector. Ini **bukan** test set ML final.

### One-shot test ML

Test ML memakai 16 run dari empat workload family yang tidak dipakai untuk training atau pemilihan model. Pipeline telah dikunci dan evaluator menolak menjalankan test untuk kedua kali. Hasil yang sudah tersimpan harus dilaporkan apa adanya; jangan melakukan retuning berdasarkan test.

## 9. Klaim yang aman untuk paper

Klaim yang didukung:

- telemetry router yang tersedia secara kausal dapat mendeteksi aktivitas IFA pada topologi simulasi tetap;
- desain pengumpulan report melalui NDN dapat direkonstruksi menjadi input graf-temporal terpusat;
- evaluasi family-disjoint dan one-shot test mengurangi risiko kebocoran;
- pada eksperimen ini, baseline sederhana menyamai atau mengungguli model graf-temporal;
- background traffic dapat mengganggu ketersediaan report monitoring.

Klaim yang tidak didukung:

- GraphSAGE+GRU adalah model terbaik;
- model sudah melakukan deteksi real-time di dalam ndnSIM;
- model sudah terbukti general untuk topologi atau jaringan nyata lain;
- IFA sendiri menyebabkan congestion atau report loss;
- empat family pada test cukup untuk generalisasi luas.

## 10. Fokus paper yang disarankan

Paper sebaiknya berfokus pada integrasi metodologis berikut:

1. topologi NDN sepuluh router dan agent pengukuran lokal;
2. report monitoring yang dikirim sebagai Data NDN;
3. rekonstruksi dataset arrival-only/causal pada collector;
4. pemodelan topologi melalui GraphSAGE dan dinamika waktu melalui GRU;
5. pembandingan adil dengan baseline sederhana;
6. hasil negatif yang penting: kompleksitas graf-temporal tidak memberi keuntungan akurasi pada domain tetap ini;
7. batas deployment: evaluasi masih offline dan lintas topologi belum diuji.

## 11. Status artefak publik

Repository ini memuat source simulator, runner, konfigurasi, dan dokumentasi hubungan ML-topologi. Dataset final, checkpoint, dan paket pipeline ML masih berada pada workspace penelitian aktif dan belum dimasukkan ke repository publik ini. Karena itu, dokumentasi ini menerangkan hasil yang telah divalidasi, tetapi clone publik saat ini belum merupakan paket reproduksi training ML lengkap.
