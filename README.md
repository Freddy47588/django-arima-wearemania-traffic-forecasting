# Django ARIMA Wearemania Traffic Forecasting

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-django-green.svg)](https://www.djangoproject.com/)
[![Algorithm](https://img.shields.io/badge/algorithm-ARIMA-orange.svg)](https://www.statsmodels.org/)

Dashboard internal berbasis web untuk mengelola, menganalisis, dan memprediksi traffic atau pageviews portal berita **Wearemania** menggunakan Django dan metode time-series **ARIMA**.

Pada tahap pengembangan saat ini, project difokuskan pada fitur **upload CSV manual** sebagai sumber data utama. Data traffic dari file CSV akan diproses, dibersihkan, disimpan ke database, dikelompokkan berdasarkan kategori berita, lalu divisualisasikan pada dashboard.

Integrasi langsung dengan Google Analytics 4 API belum menjadi fokus utama pada tahap ini dan direncanakan sebagai pengembangan lanjutan.

---

## Deskripsi Project

Wearemania memiliki pola traffic pembaca yang dinamis karena dipengaruhi oleh jadwal pertandingan, isu klub, performa konten, dan tren berita harian. Dashboard ini dibuat untuk membantu tim melihat data historis traffic dan memperkirakan potensi kunjungan pada periode berikutnya.

Dengan adanya dashboard forecasting ini, proses analisis tidak hanya dilakukan secara reaktif berdasarkan data sebelumnya, tetapi juga dapat digunakan untuk memperkirakan tren traffic ke depan.

Project ini mendukung pendekatan data-driven agar redaksi dapat melihat kategori berita yang berpotensi mengalami kenaikan atau penurunan traffic.

---

## Fokus Pengembangan Saat Ini

Fokus utama project saat ini adalah:

- Upload file CSV traffic secara manual.
- Membersihkan dan memvalidasi data CSV.
- Menyimpan data hasil upload ke database.
- Mengelompokkan data berdasarkan kategori berita.
- Menampilkan data aktual pada dashboard.
- Menyiapkan data agar dapat digunakan untuk proses forecasting ARIMA.
- Menampilkan visualisasi data aktual dan hasil prediksi pada dashboard.

---

## Fitur Utama

- Upload dataset traffic dalam format CSV.
- Validasi format file sebelum data diproses.
- Import data traffic ke database.
- Menampilkan status import data.
- Menampilkan jumlah data yang berhasil disimpan.
- Menampilkan periode data yang berhasil diimport.
- Menampilkan total kategori berita.
- Data cleaning dan preprocessing menggunakan Python.
- Mapping URL path ke kategori berita.
- Visualisasi data aktual pada dashboard.
- Forecasting traffic menggunakan model ARIMA.
- Visualisasi perbandingan data aktual dan data prediksi.
- Dashboard internal berbasis Django.

---

## Tech Stack

- **Backend**: Django
- **Bahasa Pemrograman**: Python
- **Database Development**: SQLite
- **Database Production**: MySQL / PostgreSQL
- **Data Processing**: Pandas, NumPy
- **Machine Learning / Forecasting**: Statsmodels ARIMA
- **Visualisasi**: Chart.js
- **Frontend**: HTML, CSS, JavaScript
- **Version Control**: Git & GitHub

---

## Struktur Project

```bash
django-arima-wearemania-traffic-forecasting/
│
├── analytics/              # App utama untuk upload CSV, cleaning data, analisis, dan forecasting
├── core/                   # Konfigurasi utama project Django
├── manage.py               # File utama untuk menjalankan perintah Django
├── requirements.txt        # Daftar dependency Python
├── README.md               # Dokumentasi project
└── .gitignore              # File dan folder yang tidak diikutkan ke Git
```

---

## Struktur Anggota Tim

| Nama | Peran |
|---|---|
| Fredi Irawan | Backend Developer, Upload CSV, Database Management, Dashboard Integration |
| Achmad Zaki Naufal | Data Analyst, Data Cleaning, ARIMA Modeling |
| Irsal Fauzan Alfarizi | Data Analyst, Data Cleaning, ARIMA Modeling |

---

## Alur Kerja Sistem

Alur utama sistem pada tahap saat ini:

```txt
Upload CSV Manual
        ↓
Validasi File CSV
        ↓
Data Cleaning
        ↓
Mapping Kategori Berita
        ↓
Simpan ke Database
        ↓
Dashboard Menampilkan Data Aktual
        ↓
Generate Forecast ARIMA
        ↓
Dashboard Menampilkan Data Prediksi
```

Penjelasan alur:

1. Admin mengupload file CSV traffic melalui halaman upload.
2. Sistem memvalidasi file yang diupload.
3. Data dibaca dan dibersihkan menggunakan Python.
4. URL path berita dipetakan ke kategori tertentu.
5. Data yang sudah bersih disimpan ke database.
6. Dashboard membaca data aktual dari database.
7. Model ARIMA digunakan untuk menghasilkan prediksi traffic.
8. Dashboard menampilkan perbandingan traffic aktual dan hasil prediksi.

---

## Format Dataset CSV

Dataset CSV yang digunakan sebaiknya memiliki kolom utama berikut:

| Kolom | Keterangan |
|---|---|
| date | Tanggal data traffic |
| page_path | URL atau path halaman berita |
| views | Jumlah pageviews |
| category | Kategori berita, jika tersedia |

Contoh format CSV:

```csv
date,page_path,views,category
2026-04-01,/arema-fc/berita-contoh,1200,Arema FC
2026-04-01,/liga-1/jadwal-pertandingan,850,Liga 1
2026-04-02,/kriminal/berita-contoh,430,Kriminal
```

Catatan:

- Kolom `date` harus berisi tanggal.
- Kolom `views` harus berupa angka.
- Kolom `page_path` digunakan untuk membaca sumber halaman atau URL berita.
- Kolom `category` dapat diisi langsung atau dihasilkan dari proses mapping URL.
- Format kolom dapat disesuaikan dengan struktur model dan script preprocessing pada project.

---

## Instalasi dan Menjalankan Project

Ikuti langkah-langkah berikut untuk menjalankan project di local development.

---

### 1. Clone Repository

Buka terminal, CMD, atau Git Bash, lalu jalankan:

```bash
git clone https://github.com/Freddy47588/django-arima-wearemania-traffic-forecasting.git
```

Masuk ke folder project:

```bash
cd django-arima-wearemania-traffic-forecasting
```

---

### 2. Buat Virtual Environment

#### Windows

```bash
python -m venv venv
```

Aktifkan virtual environment:

```bash
venv\Scripts\activate
```

#### Linux / MacOS

```bash
python3 -m venv venv
```

Aktifkan virtual environment:

```bash
source venv/bin/activate
```

Jika berhasil, terminal akan menampilkan tanda seperti berikut:

```bash
(venv)
```

---

### 3. Install Dependency

Pastikan virtual environment sudah aktif, lalu jalankan:

```bash
pip install -r requirements.txt
```

Jika terjadi error saat install dependency, update pip terlebih dahulu:

```bash
python -m pip install --upgrade pip
```

Lalu ulangi proses install:

```bash
pip install -r requirements.txt
```

---

### 4. Konfigurasi Environment

Jika project menggunakan file `.env`, buat file `.env` pada root folder project.

Contoh isi file `.env`:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_NAME=db.sqlite3
```

Catatan:

- Jangan upload file `.env` ke GitHub.
- Jangan upload file credentials ke repository publik.
- Simpan konfigurasi rahasia secara lokal atau di server yang aman.
- Untuk tahap upload CSV manual, konfigurasi GA4 API belum wajib digunakan.

---

### 5. Jalankan Migrasi Database

Project ini dapat menggunakan SQLite untuk development lokal.

Jalankan perintah berikut:

```bash
python manage.py makemigrations
```

```bash
python manage.py migrate
```

---

### 6. Buat Akun Superuser

Agar bisa masuk ke halaman admin Django, buat akun admin terlebih dahulu:

```bash
python manage.py createsuperuser
```

Isi username, email, dan password sesuai kebutuhan.

---

### 7. Jalankan Server Development

Jalankan server Django:

```bash
python manage.py runserver
```

Jika berhasil, akan muncul alamat seperti berikut:

```bash
http://127.0.0.1:8000/
```

Buka alamat tersebut di browser.

---

## Akses Halaman Admin

Untuk membuka halaman admin Django, gunakan alamat berikut:

```bash
http://127.0.0.1:8000/admin/
```

Login menggunakan akun superuser yang sudah dibuat sebelumnya.

---

## Panduan Upload CSV Manual

Langkah penggunaan fitur upload CSV:

1. Jalankan server Django.
2. Buka halaman dashboard melalui browser.
3. Masuk ke halaman **Upload & Cleaning**.
4. Pilih file CSV traffic.
5. Klik tombol upload atau import.
6. Sistem akan membaca file CSV.
7. Sistem melakukan validasi dan cleaning data.
8. Data yang valid disimpan ke database.
9. Sistem menampilkan status import.
10. Dashboard dapat membaca dan menampilkan data yang sudah diimport.

Output yang diharapkan setelah import berhasil:

```txt
Import berhasil.
Data harian kategori berhasil disimpan.
Periode data berhasil terdeteksi.
Total kategori berhasil dihitung.
Data siap dianalisis.
```

---

## Panduan Generate Forecast

Setelah data CSV berhasil diimport, proses forecasting dapat dijalankan.

Alur forecasting:

```txt
Data CSV berhasil diimport
        ↓
Data tersimpan di TrafficData
        ↓
User menjalankan Generate Forecast
        ↓
Model ARIMA membuat prediksi
        ↓
Hasil disimpan ke Prediction
        ↓
Dashboard menampilkan hasil prediksi
```

Jika tersedia management command, jalankan:

```bash
python manage.py generate_forecast
```

Jika ingin menentukan jumlah hari prediksi:

```bash
python manage.py generate_forecast --days 7
```

Catatan:

- Forecasting sebaiknya tidak dijalankan otomatis setiap dashboard dibuka.
- Dashboard cukup membaca hasil prediksi dari database.
- Training atau generate forecast lebih baik dijalankan melalui tombol khusus atau management command.

---

## Database Utama

Pada tahap development, database yang digunakan adalah SQLite.

File database lokal biasanya bernama:

```bash
db.sqlite3
```

Catatan:

- File `db.sqlite3` tidak wajib diupload ke GitHub.
- Database lokal dapat dibuat ulang dengan perintah migrate.
- Untuk deployment atau produksi, database dapat dipindahkan ke MySQL atau PostgreSQL.

---

## Rencana Pengembangan

Beberapa fitur yang dapat dikembangkan selanjutnya:

- Integrasi langsung dengan Google Analytics 4 API.
- Import data otomatis dari GA4.
- Penyimpanan data produksi menggunakan MySQL atau PostgreSQL.
- Training model ARIMA berdasarkan kategori berita.
- Hyperparameter tuning untuk mencari kombinasi ARIMA terbaik.
- Penyimpanan model hasil training agar dapat dipanggil ulang.
- Endpoint API untuk mengambil hasil forecasting.
- Filter dashboard berdasarkan kategori berita.
- Filter dashboard berdasarkan rentang tanggal.
- Visualisasi data menggunakan Chart.js atau ApexCharts.
- Deployment ke server hosting atau cloud.
- Dokumentasi teknis dan user manual.

---

## Catatan Development

Untuk tahap development lokal:

- Gunakan SQLite agar setup lebih sederhana.
- Jangan upload file `db.sqlite3` jika database hanya digunakan lokal.
- Jangan upload folder `venv`.
- Jangan upload file `.env`.
- Jangan upload file credentials.
- Simpan konfigurasi rahasia di file environment.
- Fokus development saat ini adalah upload CSV manual terlebih dahulu.

Contoh isi `.gitignore` yang disarankan:

```gitignore
venv/
__pycache__/
*.pyc
db.sqlite3
.env
media/
*.sqlite3
google-credentials.json
```

---

## Perintah Git Dasar

Cek status perubahan:

```bash
git status
```

Tambahkan semua perubahan:

```bash
git add .
```

Commit perubahan:

```bash
git commit -m "docs: update README for manual CSV upload workflow"
```

Push ke GitHub:

```bash
git push origin main
```

Jika branch utama menggunakan `master`, gunakan:

```bash
git push origin master
```

---

## Troubleshooting

### 1. `python` tidak dikenali

Cek versi Python:

```bash
python --version
```

Jika tidak dikenali di Windows, coba gunakan:

```bash
py --version
```

Lalu jalankan perintah Django menggunakan:

```bash
py manage.py runserver
```

---

### 2. Virtual environment tidak aktif

Aktifkan ulang virtual environment.

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / MacOS

```bash
source venv/bin/activate
```

---

### 3. Module tidak ditemukan

Install ulang dependency:

```bash
pip install -r requirements.txt
```

---

### 4. Database error setelah update model

Jalankan ulang migrasi:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 5. Port 8000 sudah digunakan

Gunakan port lain:

```bash
python manage.py runserver 8080
```

Lalu buka:

```bash
http://127.0.0.1:8080/
```

---

### 6. File CSV gagal diupload

Beberapa hal yang perlu dicek:

- Pastikan file berformat `.csv`.
- Pastikan kolom tanggal tersedia.
- Pastikan kolom views berisi angka.
- Pastikan file tidak kosong.
- Pastikan ukuran file tidak melebihi batas upload.
- Pastikan delimiter CSV sesuai dengan script import yang digunakan.

---

## Status Project

Project masih dalam tahap pengembangan. Fokus terbaru project adalah menyelesaikan fitur upload CSV manual, proses cleaning data, penyimpanan data traffic ke database, dan visualisasi data pada dashboard.

Integrasi Google Analytics 4 API belum menjadi prioritas utama pada tahap ini dan akan dikembangkan setelah alur upload CSV manual stabil.

---

## Lisensi

Project ini digunakan untuk kebutuhan pembelajaran, internship, dan pengembangan internal dashboard Wearemania.
