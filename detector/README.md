# Training dan testing NDN IFA

Paket ini berisi dataset offline 9.216 row, skrip untuk seluruh 10 model, dan 10 checkpoint asli seed11. Tidak perlu ndnSIM untuk training/testing pada dataset yang sudah direkam.

Model yang tersedia: `logistic`, `rf`, `histgb`, `gbdt`, `adaboost`, `xgboost`, `lightgbm`, `catboost`, `gru`, `graph` (GraphSAGE+GRU).

## Persiapan

Ekstrak ke folder baru. Gunakan Python 3.11 atau lebih baru. Buka terminal pada folder paket, buat virtual environment, lalu instal dependency dari `requirements.txt`. File tersebut mencantumkan nama dependency, bukan menjamin versi terbaru kompatibel dengan checkpoint lama. Versi eksperimen asal dicatat di `reference/original-environment-and-grid.json` dan `requirements-original.txt`. Untuk reproduksi checkpoint, samakan versi lingkungan asal; ketersediaan wheel bergantung platform/sumber paket.

```text
python -m venv .venv
```

Aktifkan environment di Windows dengan `.venv\Scripts\activate`, atau di Linux dengan `source .venv/bin/activate`. Kemudian:

```text
python -m pip install -r requirements.txt
python verify_files.py
```

Jika menggunakan versi berbeda, lihat hasil pemeriksaan referensi. Serialisasi model sklearn dapat bergantung pada versi. Jangan menganggap model berhasil direproduksi hanya karena skrip tidak error.

## 1. Testing langsung dengan checkpoint asli

```text
python test.py --models-dir pretrained --out results/test-original --reference reference/expected-original-predictions.csv
```

Perintah ini mengevaluasi 10 checkpoint seed11 pada 4.608 row test, menghasilkan 46.080 prediksi. Semua skor dibandingkan dengan keluaran eksperimen asal: toleransi skor <1e-6 dan keputusan threshold harus identik. Checkpoint/scaler/threshold tidak diubah.

Hasil utama: `predictions.csv`, `metrics-per-family-seed.csv`, `metrics-pooled-by-seed.csv`, `summary.csv`, dan `receipt.json` pada folder output. F1 adalah untuk kelas positif. `summary.csv` merata-ratakan seed di dalam family terlebih dahulu, kemudian family. Pooled FPR dan mean FPR per family disimpan terpisah.

Setiap sel summary memakai 12 family test per background 100/200/300/1500 Hz. Checkpoint bawaan hanya seed11, sehingga nilainya tidak selalu sama dengan tabel proyek yang merangkum seed11/23/37.

## 2. Training ulang semua model

```text
python train.py --models all --seeds 11 --search selected --out results/training
python test.py --models-dir results/training --out results/test-retrained
```

Mode `selected` menggunakan konfigurasi yang sudah terpilih pada validation eksperimen asal. Model dilatih ulang pada train, scaler dihitung dari train, dan threshold dikalibrasi pada validation. Mode ini tidak melakukan grid search baru dan tidak menjanjikan checkpoint neural byte-identik: early stopping/cap waktu dapat dipengaruhi mesin/runtime.

Untuk tiga seed seperti eksperimen utama:

```text
python train.py --models all --seeds 11,23,37 --search selected --out results/training-three-seeds
python test.py --models-dir results/training-three-seeds --out results/test-three-seeds
```

Untuk mencoba satu model:

```text
python train.py --models histgb --seeds 11 --out results/training-histgb
python test.py --models-dir results/training-histgb --models histgb --out results/test-histgb
```

## 3. Pencarian konfigurasi dari validation

```text
python train.py --models all --seeds 11,23,37 --search grid --out results/grid-search
python test.py --models-dir results/grid-search --out results/test-grid
```

Mode `grid` mencoba delapan konfigurasi per keluarga pada seed11. Konfigurasi dipilih dari validation saja, kemudian diulang pada seed yang diminta. Semua kandidat disimpan. Jumlah kandidat sama, tetapi komputasi/kapasitas dan pemilihan epoch berbeda antar-model. Source factory, grid dan training neural di `models.py` sama persis dengan source eksperimen aktif.

Threshold global tiap checkpoint memaksimalkan mean recall validation lintas background/policy, dengan pooled FPR seluruh S2 dan busy S2 <=5% pada setiap background/policy. Tie-break mengikuti skrip asli. Neural menggunakan maksimal80 epoch, minimum20, patience12 dan cap120detik/fit setelah minimum20. Output training memuat konfigurasi, threshold, history neural, skor validation dan hash checkpoint dalam `FREEZE.json`.

Varian current-NaN opsional untuk tiga boosting:

```text
python train.py --models histgb,xgboost,lightgbm --representation currentnan --search grid --seeds 11 --out results/grid-currentnan
python test.py --models-dir results/grid-currentnan --out results/test-currentnan
```

Current-NaN membuang raw11 pada mask0 sesudah normalisasi, sementara mask/age tetap finite. Ini berbeda dari LOCF dan tidak otomatis lebih baik. HistGB menolak kolom training yang seluruhnya NaN sesuai batas runtime yang telah ditemukan.

## 4. Memeriksa kembali dataset pilot online

Ekstrak ZIP dataset online yang dibagikan terpisah, misalnya ke `online-dataset/`, lalu:

```text
python replay_online.py --data-online online-dataset --models-dir pretrained --out results/replay-online
```

Ini **replay offline terhadap input pilot yang direkam**, bukan menjalankan simulasi atau mengukur ulang latensi realtime. Dengan checkpoint asli, keluaran dapat dicocokkan terhadap 1.920 keputusan pilot. Jika menggunakan checkpoint hasil training ulang, perbedaan prediksi dilaporkan; tidak diklaim harus sama. Data pilot hanya memiliki dua family, satu per background100/1500Hz dan satu checkpoint/model. Online200/300Hz belum tersedia.

## Data dan interpretasi

- Split tetap: train3.072, validation1.536, test4.608 row. Satu row berisi 5frame x10router x13channel. Tabular meratakan650nilai, neural memakai struktur temporal/router.
- `train.py` hanya membuka train dan validation. `test.py` membuka test dan memakai threshold frozen. Jangan menggunakan hasil test untuk mengganti threshold lalu mengklaimnya konfirmasi independen.
- Predictor adalah `X` dan informasi history untuk preprocessing. Label `y`, waktu serangan, scenario, rate, policy, run/family, dan metadata lainnya bukan predictor.
- NPZ asli juga memuat `X_complete`, yang merupakan diagnosis sumber lengkap. Helper hanya membaca `X` actual-arrival dan tidak menggunakan `X_complete` untuk training/testing.
- Family tidak tumpang tindih antar-split. Jangan acak ulang baris karena history saling bertumpang tindih dan empat kondisi per family berpasangan.
- Timely pada evaluasi offline memakai waktu keputusan asumsi window+0,25s. Itu bukan waktu selesai inferensi yang diukur pada pilot online.
- Cohort sudah pernah diamati dalam proyek. Paket ini untuk reproduksi/pengembangan, bukan dataset test baru yang belum diamati atau bukti pemenang universal.
- Setiap output harus memakai nama folder baru. Skrip menolak menimpa folder hasil yang sudah ada. Percobaan gagal disimpan untuk diperiksa.

Paket ini mencakup jalur utama 10 keluarga LOCF dan opsi current-NaN. Ia tidak menjalankan ulang panel checkpoint historis, semua anchor konfigurasi lama, diagnosis complete-source, atau 384 simulasi jaringan. Source/protokol eksperimen lengkap tersedia sebagai referensi; `original-experiment.py` bergantung pada layout proyek asal. Gunakan entry point portable pada root paket untuk perintah di atas.

Tidak ada perubahan pada dataset/checkpoint asli atau paper ketika paket ini dibuat.

## Pemeriksaan paket

Paket ini diuji pada Linux Mint dengan Python3.12.3 dan environment eksperimen asal. Testing 10 checkpoint asli menghasilkan46.080prediksi, dengan keputusan sama seluruhnya terhadap referensi. Training ulang10model dan testingnya selesai. Cabang grid diuji pada8kandidat HistGB; cabang current-NaN diuji pada HistGB/XGBoost/LightGBM. Replay1.920keputusan pilot cocok pada threshold yang sama.

Perbaikan akhir pelaporan hanya mengeluarkan endpoint episode dari tabel pooled window dan menambahkan hash source. F1/recall/precision/accuracy/FPR/timely pada summary tetap sama sesudah perbaikan. Bukti di`validation/FINAL-VALIDATION.json`. Validasi ini tidak menjalankan ulang seluruh grid untuk10keluarga atau tiga seed lengkap. Instalasi dari environment kosong dan sistem operasi lain belum diuji.
