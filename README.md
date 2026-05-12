# Django ARIMA Wearemania Traffic Forecasting

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-django-green.svg)](https://www.djangoproject.com/)
[![Algorithm](https://img.shields.io/badge/algorithm-ARIMA-orange.svg)](https://www.statsmodels.org/)

Dashboard internal berbasis web yang dirancang untuk memprediksi traffic (pageviews) portal berita **Wearemania** per kategori berita menggunakan metode statistika **ARIMA**. Proyek ini mengintegrasikan data real-time dari **Google Analytics 4 (GA4) API**.

## 🚀 Fitur Utama
- **Automated Data Fetching**: Penarikan data traffic otomatis dari API GA4.
- **Traffic Forecasting**: Prediksi jumlah kunjungan untuk 7 hari ke depan menggunakan model ARIMA.
- **Category-Based Analysis**: Pengelompokan data berdasarkan kategori berita (Arema FC, Liga 1, Kriminal, dll).
- **Interactive Dashboard**: Visualisasi perbandingan data aktual dan hasil prediksi.

## 🛠️ Tech Stack
- **Backend**: Django (Python)
- **Database**: SQLite
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: Statsmodels (ARIMA), Scikit-Learn
- **API Integration**: Google Analytics Data API v1beta

## 📋 Struktur Anggota Tim
- **Fredi Irawan**: Backend Developer & API Integration (Project Leader)
- **Achmad Zaki Naufal**: Data Analyst & ARIMA Modeling
- **Irsal Fauzan Alfarizi**: Data Scientist & Machine Learning Engineer

## ⚙️ Instalasi (Local Development)

1. **Clone Repository**
   ```bash
   git clone [https://github.com/](https://github.com/)[username_anda]/django-arima-wearemania-traffic-forecasting.git
   cd django-arima-wearemania-traffic-forecasting
