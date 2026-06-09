# Deploy ke Northflank

Panduan final deployment Wearemania Traffic Forecasting Dashboard ke Northflank dengan Aiven MySQL.

## Konfigurasi Northflank

Platform:
Northflank

Service Type:
Combined Service

Source:
GitHub Repository

Branch:
main

Build Type:
Buildpack

Build Command:

```bash
./build.sh
```

Procfile / Start Command:

```Procfile
web: sh -c 'gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 120'
```

Port:
8000

Protocol:
HTTP

Public:
Yes

Folder Django yang berisi `wsgi.py` pada project ini adalah `core`, sehingga module WSGI yang dipakai adalah `core.wsgi:application`.

## Runtime Variables

Isi variable berikut secara manual di Northflank. Jangan commit `.env`, password, host database, `SECRET_KEY`, atau file CA asli ke repository.

```env
DEBUG=False
SECRET_KEY=isi_manual_di_northflank
ALLOWED_HOSTS=.code.run,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.code.run
DB_ENGINE=django.db.backends.mysql
DB_NAME=defaultdb
DB_USER=avnadmin
DB_PASSWORD=isi_manual_di_northflank
DB_HOST=isi_manual_di_northflank
DB_PORT=isi_manual_di_northflank
DB_SSL_CA=
FORECAST_HISTORY_LIMIT=10
FORECAST_DAYS=7
FORECAST_MAX_DAYS=14
PYTHON_VERSION=3.11.10
```

## Aiven MySQL CA

Jika Aiven membutuhkan `ca.pem`:

- Upload `ca.pem` sebagai Secret File di Northflank.
- Mount path contoh:

```txt
/etc/secrets/aiven-ca.pem
```

- Isi env:

```env
DB_SSL_CA=/etc/secrets/aiven-ca.pem
```

Jika tidak memakai CA file, biarkan `DB_SSL_CA` kosong.

## Domain Final Northflank

Setelah Northflank memberi domain final, misalnya:

```txt
web--wearemania-dashboard--xxxx.code.run
```

Update env:

```env
ALLOWED_HOSTS=web--wearemania-dashboard--xxxx.code.run
CSRF_TRUSTED_ORIGINS=https://web--wearemania-dashboard--xxxx.code.run
```

## Build dan Runtime

`build.sh` menjalankan:

```bash
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

Procfile hanya menjalankan Gunicorn agar restart container tetap ringan. Build dan startup tidak menjalankan forecast otomatis.

Forecast hanya berjalan melalui:

- Tombol Generate Forecast di dashboard.
- Management command:

```bash
python manage.py generate_forecast
```

## Catatan Keamanan

- Jangan upload `.env` ke GitHub.
- Jangan commit `ca.pem` atau file `.pem` asli.
- Jangan hardcode credential di `settings.py`, `build.sh`, README, atau file dokumentasi.
- Gunakan `SECRET_KEY` yang kuat dan unik di Northflank.
