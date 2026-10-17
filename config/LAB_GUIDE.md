# Lab NDN dan Uji IFA: Panduan untuk Tim

Panduan ini menjelaskan lab yang kita bangun dan cara menjalankannya di **Ubuntu 24.04 LTS atau Linux Mint 22.x**, baik langsung di komputer maupun di dalam satu mesin virtual (VM). Mulai dari trafik normal, lalu lanjutkan ke uji serangan ringan. Semua router, consumer, producer, dan collector dibuat otomatis di dalam simulator **ndnSIM pada satu laptop**. Tidak perlu menyiapkan 17 komputer atau memasang router satu per satu.

## 1. Apa yang sedang kita kerjakan?

Kita ingin mendeteksi **Interest Flooding Attack (IFA)**: banyak permintaan dikirim untuk membebani jaringan NDN. Pada uji awal kita, attacker meminta nama yang memiliki rute, tetapi tidak mendapatkan balasan Data.

Tiga istilah yang perlu dipahami:

- **Interest:** paket permintaan konten.
- **Data:** paket balasan untuk Interest.
- **PIT:** catatan permintaan yang masih menunggu balasan pada router.

Saat ini jaringan, pengukuran router, pengiriman report, dan uji IFA sudah berjalan. **Detektor dan model ML belum dipasang.** Jadi, lab mencatat apa yang terjadi; belum memutuskan sendiri apakah ada serangan.

## 2. Bentuk lab

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

| Komponen | Letak dan tugas |
|---|---|
| R1–R10 | Sepuluh router yang meneruskan paket dan mengukur kondisinya |
| C1, C2, C3 | Consumer, terhubung ke R1, R2, R3; meminta konten normal |
| A1, A2 | Endpoint attacker, terhubung ke R1 dan R3; uji ringan memakai A1 saja |
| P | Producer di sisi R4; membalas permintaan normal |
| M | Collector di sisi R10; meminta dan menerima report router |

Setiap satu detik, agent pada router mencatat kondisi lokal. M meminta report itu melalui jaringan NDN, lalu router mengirimkannya sebagai Data. Report inilah yang nantinya menjadi masukan detektor.

## 3. Persiapan

### Pilih sistem operasi

Gunakan **Ubuntu 24.04 LTS 64-bit (Intel/AMD)** atau **Linux Mint 22.x 64-bit**. Ubuntu dapat dipasang langsung atau dijalankan sebagai satu VM di laptop Windows/Linux. Untuk pemula yang memakai VM, pilih Ubuntu Desktop agar tersedia tampilan dan browser.

Ubuntu 24.04 dipilih karena Mint 22.x memakai basis Ubuntu 24.04, sehingga lebih dekat dengan lingkungan lab acuan. Dasarnya ada pada [catatan resmi Linux Mint](https://www.linuxmint.com/rel_wilma_mate.php). Paket lab ini belum diuji ulang secara khusus pada Ubuntu atau VM; hasil **PASS** pada langkah pengujian tetap menjadi pemeriksaan keberhasilan di komputer masing-masing.

### Minimum praktis untuk mengikuti tutorial

**Tidak wajib laptop RAM 16 GB.** Angka berikut adalah minimum praktis yang disarankan untuk lab normal dan IFA ringan, dengan build satu pekerjaan. Ini perkiraan kebutuhan kerja, **belum merupakan batas minimum yang dibuktikan lewat pengujian mesin kecil**. Tidak mencakup training ML, dataset besar, atau serangan berkecepatan tinggi.

| Komponen | Linux langsung di komputer | Linux di dalam VM |
|---|---|---|
| CPU | Intel/AMD 64-bit, 2 core, sekitar 2 GHz | 2 vCPU; virtualisasi VT-x/AMD-V tersedia pada komputer induk |
| RAM untuk Linux | 4 GB | 4 GB **dialokasikan ke VM**, di luar kebutuhan sistem induk |
| Disk untuk OS dan lab | 40 GB; sisakan minimal 15 GB kosong sebelum memasang lab | Disk virtual 40 GB; sisakan minimal 15 GB kosong di Linux setelah instalasi OS |
| Komputer induk VM | Tidak berlaku | RAM total minimal praktis 8 GB; sediakan sekitar 50 GB disk kosong untuk VM dan unduhan ISO |
| GPU khusus | Tidak diperlukan untuk tutorial ini | Tidak diperlukan untuk tutorial ini |

**Agar lebih nyaman:** RAM Linux 8 GB dan disk 60 GB; untuk VM, RAM 6–8 GB jika komputer induk masih memiliki cukup RAM. Laptop induk 8 GB dapat memulai dengan VM 4 GB dan menutup aplikasi berat lain. Jika RAM seluruh laptop hanya 4 GB, lebih masuk akal memakai Linux langsung daripada membaginya lagi untuk VM Desktop.

Sebagai pembanding, [panduan resmi Ubuntu untuk VM](https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox) menyebut 4 GB masih dapat digunakan dan sekitar 8 GB lebih nyaman untuk Ubuntu Desktop. Kebutuhan lab di tabel menambahkan ruang bagi compiler dan source simulator; bukan angka minimum resmi ndnSIM. Mesin acuan kita memakai Mint 22.2 dan RAM 16 GB, tetapi spesifikasi itu tidak menjadi persyaratan teman-teman.

### Jika menggunakan VM

1. Pasang VirtualBox pada komputer induk, atau gunakan aplikasi VM yang sudah tersedia.
2. Unduh **ISO Ubuntu 24.04.x LTS Desktop amd64** dari [direktori resmi Ubuntu 24.04](https://releases.ubuntu.com/24.04/). Pilih berkas yang namanya memuat `24.04` dan `desktop-amd64.iso`.
3. Buat **satu VM** bernama `NDN-IFA-Lab`: RAM **4096 MB**, CPU **2 vCPU**, disk **40 GB**. Disk boleh memakai alokasi dinamis. Biarkan jaringan pada **NAT** agar VM bisa mengunduh paket.
4. Pasang Ubuntu di disk virtual, buat akun sendiri, lalu masuk ke desktop Ubuntu. Seluruh 17 node lab dibuat oleh ndnSIM di dalam VM ini; tidak perlu membuat satu VM per router atau mengatur jaringan bridged.
5. Buka Terminal **di dalam Ubuntu VM**. Semua perintah tutorial berikut dijalankan di sana, bukan di PowerShell Windows.

Jika Ubuntu/Mint sudah terpasang langsung di komputer, lewati bagian pembuatan VM. Siapkan koneksi internet untuk mengambil paket dan source simulator.

Buka Terminal. Jalankan blok perintah secara berurutan dan tunggu setiap tahap selesai. Saat diminta password `sudo`, masukkan password laptop sendiri; karakter password biasanya tidak ditampilkan.

### Langkah 1 - Ambil paket lab

```bash
sudo apt update
sudo apt install -y git python3 unzip
mkdir -p "$HOME/ndn-ifa-lab"
cd "$HOME/ndn-ifa-lab"
git clone https://github.com/rizkidsaputra/NDN-IFA-Detection.git
cd NDN-IFA-Detection
git rev-parse --short HEAD
```

Catat kode commit yang ditampilkan agar versi lab dapat dibandingkan saat bekerja bersama. Repository menyediakan **lab normal, report router, dan source uji IFA**. Ikuti panduan ini pada pemasangan baru; hasil dari lab sebelumnya tetap disimpan terpisah.

### Langkah 2 - Pasang simulator

```bash
cd "$HOME/ndn-ifa-lab/NDN-IFA-Detection/config/architecture/ndnsim"
bash scripts/bootstrap_mint.sh
```

Nama script tetap `bootstrap_mint.sh`, tetapi perintah di dalamnya memakai paket Ubuntu/Mint. Build memakai **satu pekerjaan** agar lebih hemat RAM. Script juga memasang patch scheduler yang mencegah penjadwalan timer berulang; patch tidak mengubah laju trafik atau kapasitas link.

Script memasang kebutuhan sistem, mengambil versi simulator yang sesuai, membangunnya, dan menjalankan contoh sederhana. Tunggu sampai perintah selesai tanpa error. Proses ini bisa lebih lama daripada menjalankan percobaannya.

**Jika lab sudah terpasang, lewati perintah `bash scripts/bootstrap_mint.sh`.** Script instalasi menolak menimpa folder simulator yang sudah ada. Instalasi asli sudah berhasil di Mint acuan; komputer teman tetap perlu melewati pemeriksaan berikut untuk memastikan labnya berjalan.

## 4. Jalankan lab normal

### Langkah 3 - Mulai simulasi

```bash
cd "$HOME/ndn-ifa-lab/NDN-IFA-Detection/config/architecture/ndnsim"
bash scripts/run_pilot.sh config/benign-pilot.json
```

Pada tahap ini attacker belum aktif. Simulasi berjalan selama **15 detik waktu simulasi**. C1, C2, dan C3 masing-masing meminta 50 konten; sepuluh router mengirim total 130 report.

### Langkah 4 - Periksa hasil

Salin blok ini ke Terminal:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('runs/benign-tree-s1-r3/validation.json')
d = json.loads(p.read_text())
print('Validasi:', d['status'])
for name, item in d['consumers'].items():
    e = item['events']
    print(f"{name}: {e.get('data', 0)}/{e.get('request', 0)} Data diterima")
print('Report tepat waktu:', d['collector_status_counts'].get('on_time', 0), '/130')
PY
```

Hasil yang diharapkan:

```text
Validasi: PASS
C1: 50/50 Data diterima
C2: 50/50 Data diterima
C3: 50/50 Data diterima
Report tepat waktu: 130 /130
```

**Kalau hasilnya sesuai, lab normal sudah berhasil dibuat.** Tidak perlu membaca seluruh CSV untuk menyelesaikan tahap ini.

### Langkah 5 - Ulangi tanpa menimpa hasil pertama

```bash
bash scripts/run_pilot.sh config/benign-pilot.json latihan-kedua
```

Hasil baru berada di `runs/latihan-kedua/`. Gunakan nama hasil yang berbeda untuk percobaan berikutnya. Parameter trafiknya masih sama.

## 5. Coba satu serangan IFA ringan

### Langkah 6 - Masuk ke folder IFA

Source IFA sudah tersedia di repository; tidak perlu mengunduh arsip terpisah. Setelah lab normal berhasil:

```bash
cd "$HOME/ndn-ifa-lab/NDN-IFA-Detection/config/architecture/ndnsim/ifa-pilot"
```

Runner memakai simulator dari langkah 2, memeriksa patch scheduler, dan membangun source bila diperlukan. Jika memakai instalasi lama, helper hanya menerapkan patch pada commit dependency yang sesuai; jika source berbeda, proses berhenti tanpa menimpa perubahan.

### Langkah 7 - Jalankan pembanding normal, lalu IFA

```bash
bash scripts/run_ifa.sh config/ifa-base-00000-s1.json
bash scripts/run_ifa.sh config/ifa-atk1-00050-s1.json
```

Keduanya berjalan selama **30 detik waktu simulasi**. Pada percobaan kedua, A1 mengirim **50 Interest/detik selama detik 5 sampai sebelum detik 10**: total 250 Interest unik. Permintaan diteruskan sampai aplikasi di P yang sengaja tidak memberikan Data. Producer untuk trafik normal tetap membalas seperti biasa.

Perintah akan menampilkan ringkasan. Pada lab acuan, hasilnya:

| Yang diperiksa | Normal 30 detik | IFA ringan 30 detik |
|---|---:|---:|
| Validasi | PASS | PASS |
| Request serangan yang mencapai P | 0 | 250 dari 250 |
| Puncak jumlah entry PIT R1 | 1 | 51 |
| Data consumer normal diterima | 345/345 | 345/345 |
| Report tepat waktu | 280/280 | 280/280 |

Angka request/report lebih banyak daripada langkah 3 karena percobaannya lebih panjang. Pada IFA ringan, PIT meningkat tetapi layanan normal dan report masih berhasil. **PASS berarti percobaan dan catatannya lolos pemeriksaan, bukan berarti serangan berhasil melumpuhkan jaringan atau terdeteksi oleh ML.**

## 6. Hasil mana yang perlu dibaca?

Untuk lab normal, buka folder `runs/benign-tree-s1-r3/`. Untuk IFA, buka `ifa-pilot/runs/ifa-atk1-00050-s1/` dari folder lab normal.

| Berkas | Gunanya |
|---|---|
| `validation.json` | Ringkasan hasil dan pemeriksaan PASS/FAIL; baca ini dahulu |
| `simulator.log` | Pesan saat simulasi berjalan; periksa jika gagal |
| `collector-received.csv` | Report router yang benar-benar sampai ke M |
| `client-C1.csv` dan padanannya | Permintaan normal, Data diterima, atau timeout |
| `flow-A1.csv` dan `sink.csv` pada uji IFA | Permintaan serangan dan bukti kedatangannya di P |

Simpan folder hasil ketika meminta bantuan. Cukup sampaikan tahap yang gagal dan isi pesan error; tidak perlu mengubah banyak parameter sekaligus.

## 7. Kalau ada masalah

| Gejala | Yang dilakukan |
|---|---|
| Build berhenti dengan `Killed` atau compiler kehabisan memori | Pastikan build satu pekerjaan; tutup aplikasi berat. Pada VM, periksa bahwa RAM 4 GB benar-benar dialokasikan ke VM |
| VM lambat atau tidak bisa membuka Ubuntu 64-bit | Periksa alokasi RAM/CPU serta pengaturan virtualisasi pada aplikasi VM/BIOS |
| `No such file or directory` | Pastikan posisi folder sesuai perintah `cd` pada tahap tersebut |
| Folder repository sudah ada | Gunakan folder yang sudah ada; tidak perlu clone ulang |
| Instalasi menolak karena `deps/ns-3` sudah ada | Jika instalasi sebelumnya berhasil, lanjutkan ke langkah 3. Jika sempat gagal, simpan pesan error untuk diperiksa |
| Hasil run sudah ada | Gunakan nama hasil baru, seperti `latihan-ketiga`; jangan hapus hasil lama |
| `FAIL` | Buka `validation.json` dan `simulator.log`; jangan menganggapnya otomatis sebagai serangan |
| `NACK NoRoute` | Rute atau prefix perlu diperiksa; ini belum membuktikan jaringan penuh |
| Exit code `124` pada uji IFA | Proses mencapai batas 180 detik waktu laptop. Percobaan belum selesai; ini berbeda dari report yang hilang |

## 8. Apa hasil penelitian sementara?

Uji IFA sudah dilakukan pada beberapa laju. Sampai 12.000 Interest/detik, PIT bertambah tetapi layanan normal dan report tetap berhasil pada konfigurasi yang diuji. Burst permintaan sah pendek juga pernah menimbulkan pembuangan paket dan timeout layanan, sementara report tetap tepat waktu. Dua percobaan burst panjang awalnya terhenti karena batas waktu komputasi. Setelah bug scheduler diperbaiki, keduanya selesai dengan beban yang sama. Report tetap tepat waktu; layanan consumer normal menurun pada burst tinggi.

Artinya, **kita belum membuktikan bahwa IFA menyebabkan report hilang**. Kita juga belum menguji performa detektor karena detektornya belum dipasang. Hasil lab awal ini menjadi dasar untuk menentukan percobaan berikutnya.

**Tentang istilah yang sebelumnya membingungkan:** “biaya komputasi” berarti waktu dan RAM yang dibutuhkan laptop untuk menjalankan simulasi. “Model resource” berarti batas kemampuan router yang kita tiru; misalnya, berapa banyak permintaan yang dapat disimpan dalam PIT. Saat ini batas kapasitas PIT belum diterapkan. Ini pekerjaan pengembangan lanjutan; untuk membuat lab, cukup ikuti langkah pemasangan dan uji ringan di atas.
