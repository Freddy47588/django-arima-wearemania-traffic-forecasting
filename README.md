# Wearemania Traffic Forecasting Dashboard

Dashboard berbasis Django untuk mengelola data traffic, mengelompokkan URL ke kategori berita, menampilkan analisis dashboard, dan membuat prediksi pageviews menggunakan ARIMA dengan fallback moving average.

Project saat ini berfokus pada workflow upload CSV manual. Data dari CSV dibersihkan, divalidasi, disimpan ke database, lalu digunakan untuk visualisasi dan forecast kategori berita.

## Status Project Saat Ini

- Backend menggunakan Django 5.2.
- Database development menggunakan SQLite.
- Halaman utama dilindungi login.
- Upload CSV manual tersedia di `/upload/`.
- Dashboard tersedia di `/`.
- Generate forecast tersedia dari dashboard dan melalui management command.
- Forecast disimpan per run menggunakan model `ForecastRun`.
- Prediksi disimpan di model `Prediction` dengan `lower_bound`, `upper_bound`, dan `model_name`.
- Static file production-ready memakai WhiteNoise.
- Integrasi Google Analytics 4 masih dapat dikembangkan sebagai workflow lanjutan, tetapi belum menjadi workflow utama aplikasi.

## Fitur Utama

- Login dan logout user Django.
- Upload CSV traffic dengan validasi ekstensi dan ukuran maksimal 20 MB.
- Deteksi kolom CSV dengan beberapa variasi nama kolom.
- Cleaning URL atau page path.
- Mapping page path ke kategori berita Wearemania.
- Pengecualian data non-forecast seperti homepage, arsip, halaman informasi, dan noise teknis.
- Deteksi dan penggabungan duplikat dalam file CSV.
- Skip data yang sudah ada di database.
- Dashboard ringkasan total views, kategori, data aktual, data forecast, kualitas data, insight, dan rekomendasi.
- Filter dashboard berdasarkan kategori dan rentang tanggal.
- Forecast ARIMA per kategori.
- Fallback moving average jika histori terlalu pendek, data datar, atau ARIMA gagal.
- Riwayat forecast terbaru.
- Admin Django untuk pengelolaan data master, traffic, forecast run, dan hasil prediksi.

## Tech Stack

- Python
- Django 5.2
- SQLite untuk development
- Pandas dan NumPy untuk data processing
- Statsmodels ARIMA untuk forecasting
- Chart.js untuk visualisasi frontend
- HTML, CSS, JavaScript
- WhiteNoise untuk static files
- python-dotenv untuk konfigurasi environment

## Struktur Project

```txt
wearemania_dashboard/
|-- analytics/
|   |-- management/commands/
|   |   |-- generate_forecast.py
|   |   `-- import_daily_category.py
|   |-- services/
|   |   |-- data_cleaning.py
|   |   `-- forecasting.py
|   |-- static/assets/
|   |-- templates/
|   |-- admin.py
|   |-- forms.py
|   |-- models.py
|   |-- urls.py
|   `-- views.py
|-- core/
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- staticfiles/
|-- DEPLOY_NORTHFLANK.md
|-- Procfile
|-- build.sh
|-- manage.py
|-- requirements.txt
`-- README.md
```

## Model Database

Model utama yang digunakan:

| Model | Fungsi |
|---|---|
| `Category` | Menyimpan kategori berita dan slug kategori. |
| `TrafficData` | Menyimpan data traffic aktual per kategori, tanggal, page path, dan views. |
| `ForecastRun` | Menyimpan status proses forecast, jumlah hari prediksi, jumlah prediksi, waktu mulai, dan waktu selesai. |
| `Prediction` | Menyimpan hasil prediksi per kategori dan tanggal, termasuk batas bawah/atas confidence dan nama model. |

## Alur Kerja Sistem

```txt
Login
  -> Upload CSV
  -> Validasi file dan kolom
  -> Cleaning page path
  -> Mapping kategori
  -> Skip homepage/arsip/informasi/noise
  -> Gabungkan duplikat dalam CSV
  -> Skip data yang sudah ada
  -> Simpan TrafficData
  -> Dashboard membaca data aktual
  -> Generate Forecast
  -> Simpan ForecastRun dan Prediction
  -> Dashboard menampilkan aktual, forecast, insight, dan rekomendasi
```

## Route Aplikasi

| URL | Nama route | Fungsi |
|---|---|---|
| `/login/` | `login` | Login user. |
| `/logout/` | `logout` | Logout user. |
| `/` | `dashboard` | Dashboard utama. |
| `/upload/` | `upload_raw_data` | Upload CSV traffic. |
| `/forecast/generate/` | `generate_forecast` | Generate forecast melalui POST dari dashboard. |

Halaman dashboard, upload, dan generate forecast membutuhkan login. Admin Django tersedia untuk user yang memiliki akses staff.

## Format CSV Upload

Kolom wajib yang harus tersedia:

| Kolom utama | Contoh nama kolom yang diterima |
|---|---|
| `date` | `date`, `tanggal`, `day`, `Date`, `Tanggal` |
| `page_path` | `page_path`, `path`, `url`, `url_path`, `page`, `pagePath`, `Page path`, `Page Path`, `Landing page`, `landing_page` |
| `views` | `views`, `screen_page_views`, `page_views`, `pageviews`, `total_views`, `Views`, `Page views`, `Screen page views` |

Contoh CSV:

```csv
date,page_path,views
2026-05-01,/berita-arema/arema-menang,1200
2026-05-01,/aremaday/jadwal-latihan,450
2026-05-02,https://example.com/berita-arema/contoh-artikel/?utm_source=x,900
```

Catatan:

- File wajib berformat `.csv`.
- Ukuran maksimal file adalah 20 MB.
- Nilai tanggal akan dibaca dari beberapa format umum, termasuk `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, `DD-MM-YYYY`, `YYYYMMDD`, dan format tanggal berbahasa Inggris.
- Nilai `views` harus angka dan tidak boleh negatif.
- URL penuh akan diubah menjadi path.
- Query string dan fragment URL akan dibuang.
- Data homepage, arsip, halaman informasi, dan noise teknis tidak disimpan untuk workflow forecast.

## Kategori yang Dipetakan

Beberapa kategori yang dipetakan dari URL:

- Berita Arema
- Aremaday
- Aremania
- Fokus / Analisis
- Nasional
- Ngalam / Malang Raya
- Futsal
- Arema Putri
- Arema Junior
- Sejarah Arema
- Intip Lawan
- Bursa Transfer
- Jadwal, Hasil & Klasemen
- Profil Pemain & Staff
- Foto & Video
- Review Jersey
- Kompetisi
- E-Football
- Luar Lapangan
- Profil Klub / Kompetisi
- Liga 1
- Timnas
- Kriminal
- Pendidikan
- Ekonomi
- Politik
- Lainnya

## Instalasi Lokal

Clone repository:

```bash
git clone https://github.com/Freddy47588/django-arima-wearemania-traffic-forecasting.git
cd django-arima-wearemania-traffic-forecasting
```

Buat dan aktifkan virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

Install dependency:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Buat file `.env` di root project:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

Jalankan migrasi:

```bash
python manage.py migrate
```

Buat user admin:

```bash
python manage.py createsuperuser
```

Jalankan server:

```bash
python manage.py runserver
```

Buka aplikasi:

```txt
http://127.0.0.1:8000/
```

## Cara Menggunakan

1. Login melalui `/login/`.
2. Buka `/upload/`.
3. Upload file CSV traffic.
4. Pastikan pesan import berhasil muncul.
5. Buka dashboard `/`.
6. Gunakan filter kategori atau rentang tanggal jika diperlukan.
7. Jalankan generate forecast dari dashboard.
8. Lihat hasil prediksi, insight, kualitas forecast, dan rekomendasi.

## Generate Forecast dari Terminal

Default forecast adalah 7 hari:

```bash
python manage.py generate_forecast
```

Tentukan jumlah hari forecast:

```bash
python manage.py generate_forecast --days 14
```

Jumlah hari forecast dibatasi 1 sampai 14 hari agar prediksi tetap berada pada rentang yang lebih akurat untuk data traffic harian.

## Import CSV Harian Kategori dari Terminal

Selain upload CSV mentah melalui UI, tersedia command untuk import CSV yang sudah berbentuk agregat harian per kategori:

```bash
python manage.py import_daily_category path/to/cleaned_daily_category.csv
```

Format kolom wajib:

```csv
date,category,views
2026-05-01,Berita Arema,1200
2026-05-01,Aremaday,450
```

Command ini memakai `update_or_create` berdasarkan kategori dan tanggal.

## Konfigurasi Environment

Environment variable yang digunakan:

| Variable | Default | Keterangan |
|---|---|---|
| `SECRET_KEY` | - | Secret key Django dari environment variable. |
| `DEBUG` | `False` | Mode debug. |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Daftar host yang diizinkan. |
| `CSRF_TRUSTED_ORIGINS` | - | Origin tepercaya untuk request HTTPS production. |
| `DB_ENGINE` | SQLite fallback jika kosong | Engine database Django. Untuk production gunakan `django.db.backends.mysql`. |
| `DB_NAME` | `BASE_DIR / db.sqlite3` | Nama/path database. |
| `DB_USER` | - | Username database production. |
| `DB_PASSWORD` | - | Password database production. |
| `DB_HOST` | - | Host database production. |
| `DB_PORT` | `3306` | Port database MySQL. |
| `DB_SSL_CA` | - | Path CA certificate Aiven jika diperlukan. |
| `FORECAST_HISTORY_LIMIT` | `10` | Jumlah `ForecastRun` terbaru yang disimpan. |
| `FORECAST_DAYS` | `7` | Default jumlah hari forecast. |
| `FORECAST_MAX_DAYS` | `14` | Batas maksimal hari forecast. |

Catatan keamanan:

- Jangan commit `.env`.
- Jangan commit `db.sqlite3` jika hanya database lokal.
- Jangan commit file credential, token, database lokal, atau konfigurasi rahasia ke repository publik.
- Untuk production, gunakan `DEBUG=False`, secret key kuat, host yang sesuai, dan database production.

## Static Files

Project memakai WhiteNoise dan `CompressedManifestStaticFilesStorage`.

Untuk menyiapkan static files production:

```bash
python manage.py collectstatic
```

Output static akan masuk ke folder `staticfiles/`.

## Deployment

Deployment utama project ini menggunakan Northflank dengan Aiven MySQL melalui environment variables.

```txt
DEPLOY_NORTHFLANK.md
```

Ringkasan konfigurasi Northflank:

```bash
Build Command: ./build.sh
Port: 8000
Procfile: web: sh -c 'gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 120'
```

Build dan startup tidak menjalankan forecast otomatis. Forecast tetap hanya berjalan dari tombol Generate Forecast di dashboard atau management command `python manage.py generate_forecast`.

### Legacy deployment notes

Dokumentasi Render dan Koyeb lama sudah dihapus agar konfigurasi deployment tidak membingungkan. Jika ingin memakai platform lain, gunakan pola generic yang sama: environment variables untuk Django/Aiven MySQL, WhiteNoise untuk static files, dan Gunicorn untuk WSGI.

## Testing dan Cek Project

Jalankan test Django:

```bash
python manage.py test
```

Cek konfigurasi deployment:

```bash
python manage.py check --deploy
```

Untuk development lokal, peringatan dari `check --deploy` bisa muncul karena konfigurasi production memang belum diaktifkan.

## Troubleshooting

### Login redirect ke halaman login terus

Pastikan user sudah dibuat dan aktif:

```bash
python manage.py createsuperuser
```

### CSV ditolak

Pastikan:

- File berekstensi `.csv`.
- Ukuran file tidak lebih dari 20 MB.
- Kolom `date`, `page_path`, dan `views` tersedia atau memakai variasi nama kolom yang dikenali.
- Nilai `views` berupa angka.
- Data tidak semuanya termasuk homepage, arsip, halaman informasi, atau noise teknis.

### Tidak ada data baru tersimpan

Kemungkinan semua data sudah pernah diimport. Sistem akan melewati data dengan kombinasi kategori, tanggal, dan page path yang sudah ada di database.

### Forecast tidak menghasilkan prediksi

Pastikan data `TrafficData` sudah tersedia. Untuk hasil yang lebih stabil, gunakan histori harian yang cukup panjang per kategori. Jika data kategori kurang dari 10 titik atau datanya datar, sistem akan memakai moving average fallback.

### Port 8000 sudah digunakan

Gunakan port lain:

```bash
python manage.py runserver 8080
```

## Rencana Pengembangan

- Integrasi langsung dengan Google Analytics 4 API.
- Import otomatis data GA4.
- Endpoint API untuk data dashboard dan forecast.
- Export hasil forecast.
- Evaluasi akurasi forecast.
- Tuning parameter ARIMA per kategori.
- Deployment.
- Dokumentasi user manual untuk pengguna dashboard.

## Lisensi

Project ini digunakan untuk kebutuhan pembelajaran, pengembangan, dan dokumentasi sistem dashboard traffic forecasting.
