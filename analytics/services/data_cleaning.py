import re
from urllib.parse import urlparse

import pandas as pd


def clean_page_path(path):
    if pd.isna(path):
        return None

    path = str(path).strip().lower()

    if path in ["", "nan", "null", "(other)", "other"]:
        return None

    if path.startswith("http"):
        path = urlparse(path).path

    path = path.split("?")[0].split("#")[0]

    if not path.startswith("/"):
        path = "/" + path

    path = re.sub(r"/+", "/", path)

    if len(path) > 1:
        path = path.rstrip("/")

    return path


def map_category(page_path):
    path = str(page_path).lower().strip()

    if path in ["/", ""]:
        return "Homepage"

    elif any(x in path for x in ["/tag", "/category", "/author", "/date", "/page"]):
        return "Halaman Arsip"

    elif any(x in path for x in [
        "/iklan", "/disclaimer", "/pedoman-media-online",
        "/kebijakan-privasi", "/kontak", "/contact",
        "/redaksi-wearemania", "/sponsor", "/ratecard"
    ]):
        return "Halaman Informasi"

    elif any(x in path for x in [
        "/wp-content", "/.well-known", "wpac-", "xnyc-",
        "sackboy", "panderma", "/resource", "/lander"
    ]):
        return "Noise / Teknis"

    elif "/berita-arema" in path or "/arema-news" in path or path.startswith("/news/"):
        return "Berita Arema"

    elif "/aremaday" in path:
        return "Aremaday"

    elif "/aremania" in path or "/aremania-voice" in path:
        return "Aremania"

    elif "/ngalam" in path or "/malang-raya" in path:
        return "Ngalam / Malang Raya"

    elif "/nasional" in path:
        return "Nasional"

    elif "/fokus" in path or "/ruang-taktik" in path:
        return "Fokus / Analisis"

    elif "/liga-futsal-profesional-indonesia" in path or "/usc-futsal-league" in path:
        return "Futsal"

    elif "/arema-putri" in path:
        return "Arema Putri"

    elif "/arema-junior" in path or "/akademi-arema" in path:
        return "Arema Junior"

    elif any(x in path for x in [
        "/memori-arema", "/legenda", "/this-day-in-history",
        "/sejarah", "sejarah-arema-hari-ini", "sejarah-hari-ini"
    ]):
        return "Sejarah Arema"

    elif "/intip-lawan" in path:
        return "Intip Lawan"

    elif "/featured" in path:
        return "Featured"

    elif "/bursa-transfer-pemain" in path:
        return "Bursa Transfer"

    elif "/pemain" in path or "/player" in path or "/staff" in path:
        return "Profil Pemain & Staff"

    elif any(x in path for x in [
        "/jadwal-hasil", "/pertandingan", "/jadwal_skor",
        "/jadwal", "/klasemen", "/posisi", "/kick-off",
        "/susunan-pemain", "/live_commentary"
    ]):
        return "Jadwal, Hasil & Klasemen"

    elif any(x in path for x in [
        "/lensa", "/berita-foto", "/photoplayer",
        "/topshot", "/wallpaper", "/video"
    ]):
        return "Foto & Video"

    elif "/review-jersey" in path:
        return "Review Jersey"

    elif "/kompetisi" in path:
        return "Kompetisi"

    elif "/indonesian-football-e-league" in path:
        return "E-Football"

    elif "/luar-lapangan" in path:
        return "Luar Lapangan"

    elif any(x in path for x in ["/klub", "/official", "/venue", "/musim", "/liga"]):
        return "Profil Klub / Kompetisi"

    elif path.startswith("/arema/"):
        return "Profil Klub / Kompetisi"

    return "Lainnya"


def process_raw_csv(file):
    df = pd.read_csv(file)

    df = df.rename(columns={
        "Date": "date",
        "Page path": "page_path",
        "Page Path": "page_path",
        "Views": "views",
    })

    required = {"date", "page_path", "views"}
    if not required.issubset(df.columns):
        raise ValueError(f"Kolom wajib: {required}. Kolom ditemukan: {list(df.columns)}")

    total_rows = len(df)

    df = df.dropna(subset=["date", "page_path", "views"])

    df["page_path"] = df["page_path"].apply(clean_page_path)
    df = df.dropna(subset=["page_path"])

    df["views"] = (
        df["views"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["views"] = pd.to_numeric(df["views"], errors="coerce")
    df = df.dropna(subset=["views"])
    df["views"] = df["views"].astype(int)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.date

    df["category"] = df["page_path"].apply(map_category)

    exclude = ["Homepage", "Halaman Arsip", "Halaman Informasi", "Noise / Teknis"]

    df_forecast = df[~df["category"].isin(exclude)].copy()

    daily_category = (
        df_forecast
        .groupby(["date", "category"], as_index=False)["views"]
        .sum()
        .sort_values(["category", "date"])
    )

    info = {
        "total_rows": total_rows,
        "cleaned_rows": len(df),
        "skipped_rows": total_rows - len(df),
        "import_rows": len(daily_category),
        "category_count": daily_category["category"].nunique(),
        "date_start": daily_category["date"].min(),
        "date_end": daily_category["date"].max(),
    }

    return daily_category, info