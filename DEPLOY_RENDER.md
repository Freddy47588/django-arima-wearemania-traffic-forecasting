# Deploy ke Render Free

Panduan singkat deployment Wearemania Traffic Forecasting Dashboard ke Render Free dengan Aiven MySQL.

## Render Web Service

1. Buat **New Web Service** di Render.
2. Connect ke GitHub repository project ini.
3. Pilih branch: `main`.
4. Gunakan build command:

   ```bash
   ./build.sh
   ```

5. Gunakan start command:

   ```bash
   gunicorn core.wsgi:application --workers 1 --timeout 120
   ```

6. Isi environment variables secara manual di dashboard Render.
7. Jangan upload `.env` ke GitHub.

## Environment Variables

Isi variable berikut di Render tanpa menyimpan credential di repository:

```env
DEBUG=False
SECRET_KEY=
ALLOWED_HOSTS=
CSRF_TRUSTED_ORIGINS=
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
DB_ENGINE=django.db.backends.mysql
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
DB_SSL_CA=
FORECAST_HISTORY_LIMIT=10
FORECAST_DAYS=7
PYTHON_VERSION=3.11.10
```

Untuk `ALLOWED_HOSTS`, isi domain Render tanpa skema, misalnya `nama-service.onrender.com`.

Untuk `CSRF_TRUSTED_ORIGINS`, isi origin lengkap dengan skema, misalnya `https://nama-service.onrender.com`.

Jika memakai Aiven CA, gunakan **Render Secret File** dengan path:

```txt
/etc/secrets/ca.pem
```

Lalu set environment variable:

```env
DB_SSL_CA=/etc/secrets/ca.pem
```
