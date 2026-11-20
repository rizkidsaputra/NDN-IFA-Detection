# Konfirmasi workload bervariasi — protokol sebelum hasil

Tanggal: 24 Oktober 2026. Pengguna mengizinkan akses Mint, eksperimen tambahan, penelaahan hasil dan laporan. Revisi paper menunggu persetujuan terpisah. Seluruh keluaran berada di namespace baru; bukti kampanye sebelumnya tetap utuh.

## Pertanyaan dan batas

1. Apakah manfaat total FIFO–Priority untuk ketersediaan laporan, deteksi dan layanan bertahan ketika fase, durasi, intensitas serta lokasi serangan berubah?
2. Apakah model historis yang dibekukan mentransfer ke workload baru? Secara terpisah, bagaimana RF/HistGB yang dikembangkan pada workload baru dengan jumlah kandidat sama?
3. Apakah informasi mask/age saja atau aturan sederhana cukup menjelaskan hasil? Apakah prediksi berubah ketika input aktual diganti pengukuran lengkap yang sudah tersedia pada trajectory jaringan yang sama?

Ini konfirmasi baru yang diinformasikan hasil lama, bukan preregistrasi sebelum seluruh penelitian dimulai. Replay source-complete adalah diagnosis input offline; tidak membuktikan efek kebijakan jaringan. Tidak ada klaim algoritma pemenang universal, mitigasi, autentikasi atau latency alarm online.

## Desain yang ditetapkan

- Simulator biner lama yang tervalidasi, SHA256 `074e556583583dbf9eb2b1ec6f40a64058710f55477f82140306717bd4ff7924`; tree 10 router, 30 s, 28 sampel, deadline250 ms, input5×10×13. Source simulator tidak diubah.
- Background100/200/300/1500 Hz. 200 Hz adalah titik tambahan di bawah kapasitas payload nominal1 Mbps; bukan ambang kongesti yang telah diketahui.
- 24 workload draws per rate:8 train,4 validation,12 test;96 draws×S2/S3×FIFO/Priority=384 run. Split dilakukan sebelum sequence. Dua policy dan S2/S3 memakai offered schedule/benign burst identik dalam satu draw.
- Onset serangan integer8–16 s; durasi3/5/7 s; rate25/50/100 Hz. Penyerang bergantian A1/A2 pada seluruh split. Label positif untuk sampel satu detik yang beririsan dengan interval serangan; dengan batas integer: onset < window <= stop. Keputusan window terakhir terjadi setelah stop dan tidak dihitung timely.
- Background mulai integer3–7 s; durasi14–18 s, dipilih independen dari onset/durasi serangan. Jadwal fixed-count uniform tanpa pengembalian pada nanosecond ticks. Seed generator deterministik baru dan dicatat. Draws di setiap rate berbeda.
- Setengah draw pada setiap split memiliki tambahan burst legitimate dari C1 atau C3, onset8–18 s, durasi2/4 s, rate20/50/100 Hz. Burst yang sama hadir di S2/S3 dan kedua policy. Burst mempunyai prefix legitimate yang dijawab producer; bukan label serangan.
- Consumer dasar tetap3×5Hz pada[2,25),345 request/run. Burst dilaporkan terpisah dari completion consumer dasar. Tidak mengubah endpoint lama secara diam-diam.
- Tiga atau lebih keputusan sebelum onset paling awal8s tersedia mulai5,25s. Episode praalarm dihitung dari keputusan < onset; S3 sebelum/sesudah serangan dilaporkan terpisah.
- Validasi aplikasi dan queue memakai salinan kode audit aktif. Interval deskriptif yang sebelumnya hard-coded akan diganti metadata konfigurasi. Tidak menjadikan hasil Priority sempurna sebagai gate integritas.

## Model, kontrol dan freeze

Transfer historis:9 checkpoint dari lima tipe model kampanye216run, dengan scaler dan threshold asli. Tidak ada tuning ulang. Periksa hash dan reproduksi skor validation tersimpan sebelum scoring baru.

Pengembangan baru: RF dan HistGB, masing-masing8 konfigurasi untuk setiap representasi: full (11measurement+mask+age), measurements-only (11measurement LOCF) dan mask-age-only (2channel). RF grid trees200/400 × minleaf1/2/5/10. HistGB grid iterations200/400 × minleaf10/20/40/80; learning rate0,05,maxleaf15,L2=1,noearlystop. Candidate seed11; konfigurasi terbaik diulang seed23/37 tanpa seleksi seed. Sama jumlah kandidat, bukan klaim FLOPs/kapasitas identik. Tidak menambah keluarga deep learning.

Scaler log1p measurement/age dan standardisasi hanya dari train. HistGB sample weights seimbang; RF class_weight balanced. Pilih threshold global percheckpoint dari validation untuk memaksimalkan mean recall lintas rate/policy, dengan FPR <=5% pada setiap rate/policy untuk seluruh S2 dan S2 saat background aktif. Ties: worst busyFPR lebih rendah, mean allS2FPR lebih rendah, kemudian threshold lebih tinggi. Pilih konfigurasi memakai recall/FPR tersebut, tie urutan grid; jangan membandingkan threshold numerik antar konfigurasi. Seluruh kandidat dipertahankan.

Aturan sederhana memakai frame terbaru aktual: max PIT seluruh router, serta max unsatisfied/(satisfied+unsatisfied) seluruh router (denominator0→0). Masing-masing threshold ditentukan validation dengan aturan yang sama; bukan mengambil counter audit tersembunyi. Kontrol clock-only memakai frekuensi label positif per window pada train, kemudian threshold validation; kontrol ini sengaja memakai waktu dan bukan kandidat deployment. S2/S3 berpasangan membatasi kemampuan waktu saja membedakan label.

Semua model/configuration/scaler/threshold dibekukan sebelum file test dibuka untuk scoring. Test baru tidak digunakan untuk mengganti model historis atau memperbaiki hyperparameter. Kegagalan/incomplete attempt disimpan; perbaikan diberi catatan, tidak dihapus.

## Endpoint dan analisis

- Recall rata-rata workload draw; positive F1 dihitung pada seluruh keputusan S2/S3 berpasangan perdraw/policy; busy FPR pada S2 window yang beririsan dengan background. Denominator berubah mengikuti durasi, wajib dicatat. False alarm semua S2 dan S3 pre/post dipisahkan.
- Episode timely: keputusan positif berlabelattack dan waktu keputusan < stop. Late-only dan miss terpisah; TTD conditional-hit, miss bukan0. Praalarm: ada prediksi positif sebelum onset pada S3, dan run-level false alert pada S2. Belum aturan penggabungan alarm untuk sistem operasional.
- On-time/late/never-received dan age; completion3consumer dasar, burst terpisah, background goodput pada interval background aktual. Laporkan absolut, selisihpp, perubahan relatif, perconsumer dan S2/S3×rate.
- Unit independen workload draw, bukan window/seed. Dua belas pasangan test perrate. Laporkan setiap draw dan seed; interval bootstrap mean paired effects menggunakan resampling workload draw, seed tetap dirata-ratakan di dalam draw. Bootstrap deskriptif bersyarat pada keluarga workload ini, bukan bukti seluruh populasi jaringan. Fixed seedbootstrap1024,10000 resamples.
- Analisis stratifikasi lokasi attacker dan keberadaan burst telah ditetapkan, bukan dipilih menurut hasil. Tidak mencari best subset.
- Replay actual(A) vs source-complete(C) pada test di trajectory yang sama:source samples yang sudah siap sebelum cutoff, mask/age/history dihitung kembali, frame lama tidak dibackfill. Model/scaler/threshold tetap. C tidak digunakan untuk train/tune. Perubahan adalah intervensi representasi ketersediaan input, bukan efek intervensi jaringan atau jaminan improvement.

## Kriteria penelaahan

Tidak ada target skor paper atau kewajiban hasil positif. Temuan dinilai lebih kuat bila arah manfaat bertahan pada variasi baru, sensitivitas disertai specificity dan timely episodes, serta biaya layanan transparan. Bila manfaat hilang/berbalik, model sederhana sudah memadai, atau false alarm tinggi, laporkan itu. Kelulusan validator/hash hanya menunjukkan konsistensi teknis. Topologi tetap satu dan prioritas tetap digabung push-out; kedua batas itu dipertahankan.

## Pelaksanaan dan sumber daya

Maksimal dua run simulator paralel; fitting dua CPU thread. Runtime lama median2,6s/run, maksimum8,9s; durasi background baru lebih panjang, sehingga perkiraan awal campaign sekitar15–40menit ditambah fitting, audit dan transfer, bukan jaminan. Pantau disk/memori; stop dengan status incomplete bila integritas gagal. Paper dan ZIP paper tidak disentuh sampai pengguna menyetujui hasil.
