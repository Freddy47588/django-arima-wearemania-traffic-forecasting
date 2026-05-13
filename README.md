# Django ARIMA Wearemania Traffic Forecasting

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-django-green.svg)](https://www.djangoproject.com/)
[![Algorithm](https://img.shields.io/badge/algorithm-ARIMA-orange.svg)](https://www.statsmodels.org/)

Dashboard internal berbasis web untuk menganalisis dan memprediksi traffic atau pageviews portal berita **Wearemania** menggunakan metode time-series **ARIMA**. Project ini dikembangkan untuk membantu proses analisis performa konten, visualisasi data traffic, serta mendukung pengambilan keputusan redaksi berbasis data.

Sistem ini dirancang agar dapat menggunakan data dari **Google Analytics 4 (GA4)** melalui integrasi API. Pada tahap development, sistem juga dapat menggunakan file **CSV** sebagai sumber data awal atau fallback.

---

## Deskripsi Project

Wearemania memiliki pola traffic yang dinamis karena dipengaruhi oleh jadwal pertandingan, isu klub, performa konten, dan tren berita harian. Dashboard ini dibuat untuk membantu tim melihat data historis traffic dan memperkirakan potensi kunjungan pada periode berikutnya.

Dengan adanya dashboard forecasting ini, analisis traffic tidak hanya dilakukan secara reaktif berdasarkan data sebelumnya, tetapi juga dapat digunakan untuk memperkirakan tren traffic ke depan.

---

## Fitur Utama

- Upload dataset traffic dalam format CSV.
- Menampilkan data traffic pada dashboard.
- Data cleaning dan preprocessing menggunakan Python.
- Pengelompokan data berdasarkan kategori berita.
- Prediksi traffic untuk beberapa hari ke depan menggunakan model ARIMA.
- Visualisasi perbandingan data aktual dan data hasil prediksi.
- Dashboard internal berbasis Django.
- Rencana integrasi data langsung dari Google Analytics 4 API.

---

## Tech Stack

- **Backend**: Django
- **Bahasa Pemrograman**: Python
- **Database Development**: SQLite
- **Database Production**: MySQL / PostgreSQL
- **Data Processing**: Pandas, NumPy
- **Machine Learning / Forecasting**: Statsmodels ARIMA
- **Visualisasi**: Chart.js / template dashboard
- **API Integration**: Google Analytics Data API
- **Version Control**: Git & GitHub

---

## Struktur Project

```bash
django-arima-wearemania-traffic-forecasting/
│
├── analytics/              # App utama untuk data traffic, upload, analisis, dan forecasting
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
| Fredi Irawan | Backend Developer, API Integration, Database Management |
| Achmad Zaki Naufal | Data Analyst, Data Cleaning, ARIMA Modeling |
| Irsal Fauzan Alfarizi | Data Analyst, Data Cleaning, ARIMA Modeling |

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
- Jangan upload credentials Google API ke repository publik.
- Simpan file credentials seperti `google-credentials.json` secara lokal atau di server yang aman.

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

## Panduan Upload Dataset CSV

Jika fitur upload CSV sudah tersedia pada dashboard, langkah penggunaannya sebagai berikut:

1. Jalankan server Django.
2. Buka halaman dashboard melalui browser.
3. Pilih menu atau tombol upload CSV.
4. Pilih file dataset traffic.
5. Upload file ke sistem.
6. Sistem akan membaca dan menampilkan data pada dashboard.
7. Data dapat digunakan untuk analisis dan proses forecasting.

Format data yang disarankan:

| Kolom | Keterangan |
|---|---|
| date | Tanggal data traffic |
| page_path | URL atau path halaman berita |
| views | Jumlah pageviews |
| category | Kategori berita, jika tersedia |

Catatan:

Nama kolom dapat disesuaikan dengan struktur model, script preprocessing, atau format export dari Google Analytics.

---

## Alur Kerja Sistem

1. Data traffic diperoleh dari Google Analytics 4 API atau file CSV.
2. Data dibersihkan dan disesuaikan formatnya.
3. URL atau path berita dipetakan ke kategori tertentu.
4. Data historis digunakan sebagai input model ARIMA.
5. Model menghasilkan prediksi traffic untuk periode berikutnya.
6. Hasil prediksi divisualisasikan pada dashboard.
7. Pengguna dapat melihat perbandingan antara data aktual dan data prediksi.

---

## Rencana Pengembangan

Beberapa fitur yang dapat dikembangkan selanjutnya:

- Integrasi langsung dengan Google Analytics 4 API.
- Penyimpanan data produksi menggunakan MySQL atau PostgreSQL.
- Training model ARIMA berdasarkan kategori berita.
- Penyimpanan model hasil training agar dapat dipanggil ulang tanpa training berulang.
- Endpoint API untuk mengambil hasil forecasting.
- Filter data berdasarkan kategori dan rentang tanggal.
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
- Jangan upload file credentials seperti JSON dari Google API.
- Simpan konfigurasi rahasia di file environment.

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
git commit -m "docs: update README setup guide"
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

Aktifkan ulang virtual environment:

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

## Status Project

Project masih dalam tahap pengembangan. Fitur upload CSV dan tampilan data dashboard sudah berjalan. Tahap berikutnya adalah pengembangan model ARIMA, penyimpanan model hasil training, integrasi hasil prediksi ke dashboard, serta integrasi lanjutan dengan Google Analytics 4 API.

---

## Lisensi

Project ini digunakan untuk kebutuhan pembelajaran, internship, dan pengembangan internal dashboard Wearemania.
