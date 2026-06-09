# Deploy ke Koyeb Free

Panduan deployment Wearemania Traffic Forecasting Dashboard ke Koyeb Free dengan Aiven MySQL.

## Ringkasan Koyeb

- Platform: Koyeb
- Service type: Web Service
- Source: GitHub
- Branch: `main`
- Build command:

  ```bash
  ./build.sh
  ```

- Run command:

  ```bash
  gunicorn core.wsgi:application --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
  ```

Folder Django yang berisi `wsgi.py` pada project ini adalah `core`, sehingga module WSGI yang dipakai adalah `core.wsgi:application`.

Jika nama folder WSGI berbeda pada fork atau project lain, ganti `core` dengan nama folder yang berisi `wsgi.py`.

Contoh format umum:

```bash
gunicorn <nama_folder_wsgi>.wsgi:application --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
```

## Environment Variables

Isi variable berikut secara manual di dashboard Koyeb. Jangan commit `.env`, password, host database, `SECRET_KEY`, atau file CA asli ke repository.

```env
DEBUG=False
SECRET_KEY=isi_manual_di_koyeb
ALLOWED_HOSTS=.koyeb.app,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.koyeb.app
DB_ENGINE=django.db.backends.mysql
DB_NAME=defaultdb
DB_USER=avnadmin
DB_PASSWORD=isi_manual_di_koyeb
DB_HOST=isi_manual_di_koyeb
DB_PORT=isi_manual_di_koyeb
DB_SSL_CA=
FORECAST_HISTORY_LIMIT=10
FORECAST_DAYS=7
PYTHON_VERSION=3.11.10
```

## Aiven MySQL

Database tetap memakai Aiven MySQL melalui environment variables:

- `DB_ENGINE=django.db.backends.mysql`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_SSL_CA`

Jika Aiven membutuhkan CA certificate, simpan file CA secara aman di Koyeb atau gunakan mekanisme secret yang tersedia, lalu isi `DB_SSL_CA` dengan path file CA tersebut. Jika tidak memakai CA file, biarkan `DB_SSL_CA` kosong.

## Static Files

Static files diproses saat build dengan:

```bash
python manage.py collectstatic --no-input
```

Project memakai WhiteNoise, sehingga Koyeb dapat melayani static files langsung dari aplikasi Django.

## Migrasi Database

`build.sh` menjalankan:

```bash
python manage.py migrate
```

Pastikan semua environment variable database Aiven sudah lengkap sebelum deploy, karena konfigurasi MySQL yang tidak lengkap akan membuat aplikasi berhenti dengan error konfigurasi.

## Forecast

Build Koyeb tidak menjalankan training atau generate forecast otomatis.

Forecast hanya berjalan melalui:

- Tombol **Buat Prediksi** di dashboard.
- Management command:

  ```bash
  python manage.py generate_forecast
  ```

## Catatan Keamanan

- Jangan upload `.env` ke GitHub.
- Jangan commit `ca.pem` atau file `.pem` asli.
- Jangan hardcode credential di `settings.py`, `build.sh`, README, atau file dokumentasi.
- Gunakan `SECRET_KEY` yang kuat dan unik di Koyeb.
