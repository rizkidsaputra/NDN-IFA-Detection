# Dataset konfirmasi NDN IFA — 24 Oktober 2026

Dataset simulasi milik proyek, dibuat dengan ndnSIM pada tree10router. Berisi9.216sequence dari384run/96family workload. Background100/200/300/1500Hz; S2tanpa attack danS3dengan attack; FIFO/Priority. Tiap family memiliki empat kondisi berpasangan. Split tetap:train3.072row(128run/32family),validation1.536row(64run/16family),test4.608row(192run/48family,12family/rate). Pengujian semua model sebelumnya memakai kembali dataset ini.

## Isi dan cara membuka

- `npz/train.npz`, `validation.npz`, `test.npz`: salinan byte-identik data sumber. Gunakan NumPy `np.load(...,allow_pickle=False)` dan kunci `X`, `history`, `y`.
- `csv/*_features.csv`: row_id+650fitur numerik mentah. Kolom disusun time paling lama→terbaru, R1→R10,13channel. `tminus4` sampai`t0` relatif terhadap target window pada metadata.
- `csv/*_history.csv`: row_id+50flag riwayat untuk membedakan no-history dari nilai pengukuran0.
- `csv/*_metadata.csv`: row_id,npz_index,label`y`,identitasrun/family dan kondisi. Join menggunakan row_id. **Metadata bukan predictor**, termasuk waktu serangan/scenario/model target.
- `SCHEMA.json`: urutan fitur, unit, label dan missing handling. `graph.json`: adjacency10router. `scaler-train-only.json`: scaler asli yang hanya dipelajari dari training.
- Jalankan `python verify_files.py` untuk memeriksa checksum seluruh payload. Jalankan `python load_example.py` dengan NumPy untuk memuat dan menormalkan data. Normalisasi tidak dilakukan pada CSV mentah.

Satu row berisi5frame×10router×13channel=650nilai. Channel0–9adalah selisih forwarder counters perwindow1detik,channel10PITsize,channel11mask,channel12age_s. Historyflag berbeda dari mask: history1berarti pernah ada sampel yang diterima, mask1berarti sampel sesuai window saatitu. Sampel stale menggunakan LOCF. Cutoff frame adalah akhirwindow+0,25s. Nilai0 dapat merupakan pengukuran sah.

## Label dan pemakaian yang sesuai

`y=1` hanya jika scenarioS3 dan attack_start<window<=attack_stop, selain itu0. Metadata onset/stop padaS2adalah jadwal pembanding, bukan attack nyata. Targetwindowterakhir tetappositive tetapi keputusanwindow+0,25s dapat terjadi setelahattackstop; F1dan deteksi sebelumstop merupakan endpoint berbeda.

Jangan acak ulang semua row lalu membaginya: history saling bertumpang tindih dan empat kondisi dalam family berpasangan. Pertahankan split family yang disertakan. Fit scaler/tuning/threshold pada train/validation saja. Test cohort telah diamati sebelumnya dalam pengembangan proyek; penggunaan ulang bukan konfirmasi independen baru. Kedua lokasi penyerang terlihat dalam development, topologi hanya satu, jadi tidak membuktikan generalisasi universal.

**NPZ asli juga menyimpan `X_complete` dan `history_complete`. Keduanya adalah diagnosis offline dengan report sumber lengkap, bukan observasi yang benar-benar sampai collector. Untuk eksperimen detector aktual gunakan `X` dan `history`; CSV hanya mengekspor jalur aktual.**

Paket berisi data siap analisis, bukan seluruh raw packet/queue trace384run sekitar8GB atau modelcheckpoint/simulator dependencies. Bukti asal dan rencana run terdapat di`provenance/`. Tidak ada training atau simulasi baru ketika paket ini dibuat. Tidak menetapkan lisensi rilis baru atau mengklaim dataset publik.
