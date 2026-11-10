"""
Lapisan data: penemuan file, pemuatan, dan transformasi analitik.
Semua fungsi berat di-cache agar dashboard tetap responsif.
"""

from __future__ import annotations

import glob
import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# Konfigurasi lokasi data
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "data_komoditas_pangan")

# Nama folder pada dataset -> label level pasar yang dipakai di UI
LEVEL_DIRS = {
    "produsen": "Produsen",
    "pasar_tradisional": "Tradisional",
    "pasar_modern": "Modern",
}

LEVEL_ORDER = ["Produsen", "Tradisional", "Modern"]

LEVEL_COLORS = {
    "Produsen": "#2E7D5B",
    "Tradisional": "#E07A28",
    "Modern": "#2A6FB5",
}

DATE_COL = "Date_Param"

# --------------------------------------------------------------------------
# GeoJSON batas provinsi (untuk choropleth map di halaman Antarprovinsi)
# --------------------------------------------------------------------------

GEOJSON_PATH = os.path.join(BASE_DIR, "data", "geo", "indonesia-38-provinces.geojson")

# Satu-satunya perbedaan penamaan antara dataset CSV dan properti "PROVINSI"
# pada GeoJSON (hasil audit manual). Provinsi hasil pemekaran Papua
# (Papua Selatan/Tengah/Pegunungan/Barat Daya) ADA di GeoJSON tapi TIDAK ADA
# di dataset harga (data historis memakai struktur 34 provinsi) — ini normal,
# wilayah tsb akan tampil tanpa warna/data di peta.
PROVINCE_GEOJSON_ALIAS = {
    "DI Yogyakarta": "Daerah Istimewa Yogyakarta",
}


def to_geojson_name(provinsi: str) -> str:
    """Konversi nama provinsi pada dataset -> nama persis di properti GeoJSON."""
    return PROVINCE_GEOJSON_ALIAS.get(provinsi, provinsi)


@st.cache_data(show_spinner=False)
def load_provinces_geojson() -> dict | None:
    """
    Memuat GeoJSON batas wilayah 38 provinsi Indonesia untuk choropleth map.

    Sumber: "Indonesia GeoJSON & TopoJSON Maps (38 Provinces)" oleh
    denyherianto, dataset dilisensikan CC BY 4.0 (lihat data/geo/DATA_LICENSE.md).
    Properti nama provinsi ada pada kunci "PROVINSI".

    Mengembalikan None (BUKAN melempar error) jika berkas tidak ditemukan atau
    rusak, supaya halaman yang memanggilnya bisa fallback dengan aman ke
    visualisasi alternatif (mis. bar chart) tanpa membuat aplikasi crash.
    """
    if not os.path.exists(GEOJSON_PATH):
        return None
    try:
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _prettify(slug: str) -> str:
    """final_komoditas_modern_bawang_merah_2022_2026 -> Bawang Merah"""
    return slug.replace("_", " ").title()


@st.cache_data(show_spinner=False)
def discover_files(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """
    Menelusuri folder dataset dan mengembalikan katalog:
    komoditas | level | path
    """
    rows = []
    pattern = re.compile(
        r"final_komoditas_(produsen|tradisional|modern)_(.+?)_\d{4}_\d{4}\.csv$"
    )

    for folder, level_label in LEVEL_DIRS.items():
        search = os.path.join(data_dir, folder, "**", "*.csv")
        for path in glob.glob(search, recursive=True):
            # abaikan artefak notebook
            if ".ipynb_checkpoints" in path:
                continue
            match = pattern.search(os.path.basename(path))
            if not match:
                continue
            rows.append(
                {
                    "komoditas": _prettify(match.group(2)),
                    "komoditas_slug": match.group(2),
                    "level": level_label,
                    "path": path,
                }
            )

    catalog = pd.DataFrame(rows)
    if catalog.empty:
        return catalog
    return catalog.sort_values(["komoditas", "level"]).reset_index(drop=True)


def _melt_wide_to_long(
    wide: pd.DataFrame, level_label: str, komoditas: str | None = None
) -> pd.DataFrame:
    """
    Helper bersama (dipakai oleh load_commodity & load_all_data) untuk
    mengubah SATU file CSV berformat lebar (kolom = nama provinsi) menjadi
    format panjang/tidy: tanggal | provinsi | harga [+ level, komoditas].

    Memisahkan logika "melt" ke satu tempat supaya load_commodity() dan
    load_all_data() tidak duplikasi kode dan konsisten dalam penanganan
    tanggal/tipe data.
    """
    wide = wide.copy()
    wide[DATE_COL] = pd.to_datetime(wide[DATE_COL], errors="coerce")
    wide = wide.dropna(subset=[DATE_COL])

    long = wide.melt(id_vars=DATE_COL, var_name="provinsi", value_name="harga")
    long = long.rename(columns={DATE_COL: "tanggal"})
    long["harga"] = pd.to_numeric(long["harga"], errors="coerce")
    long = long.dropna(subset=["harga"])
    long["level"] = level_label
    if komoditas is not None:
        long["komoditas"] = komoditas
    return long


@st.cache_data(show_spinner=False)
def load_commodity(komoditas: str) -> pd.DataFrame:
    """
    Memuat satu komoditas untuk SEMUA level pasar dan mengubahnya
    menjadi format panjang (tidy):

        tanggal | provinsi | level | harga
    """
    catalog = discover_files()
    subset = catalog[catalog["komoditas"] == komoditas]

    frames = []
    for _, row in subset.iterrows():
        try:
            wide = pd.read_csv(row["path"])
        except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError):
            # Lewati file yang rusak/tidak terbaca agar dashboard tidak crash
            continue
        frames.append(_melt_wide_to_long(wide, row["level"]))

    if not frames:
        return pd.DataFrame(columns=["tanggal", "provinsi", "level", "harga"])

    df = pd.concat(frames, ignore_index=True)
    df["level"] = pd.Categorical(df["level"], categories=LEVEL_ORDER, ordered=True)
    return df


@st.cache_data(show_spinner="Memuat seluruh dataset komoditas pangan...")
def load_all_data() -> pd.DataFrame:
    """
    Menggabungkan (concat) seluruh data dari TIGA tingkat pasar — produsen,
    pasar tradisional, dan pasar modern — untuk SEMUA komoditas menjadi satu
    DataFrame utama, diselaraskan berdasarkan Tanggal, Provinsi, dan
    Komoditas.

    Hasil berupa format panjang/tidy sehingga siap dipakai untuk agregasi,
    groupby, atau pivot apa pun:

        tanggal | komoditas | provinsi | level | harga

    Fungsi ini di-cache dengan @st.cache_data agar proses membaca puluhan
    file CSV (periode 2022-2026) hanya dijalankan sekali per sesi/hingga
    file sumber berubah — sehingga performa dashboard tetap ringan saat
    pengguna berpindah halaman atau mengganti filter.

    Fungsi TIDAK memanggil perintah st.* apa pun (mis. st.error) di dalam
    dirinya sendiri, karena efek samping semacam itu tidak akan terulang
    saat hasilnya diambil dari cache. Penanganan kondisi "data kosong"
    diserahkan ke pemanggil (mis. app.py) lewat DataFrame kosong yang
    tetap memiliki skema kolom yang konsisten.
    """
    kolom_kosong = ["tanggal", "komoditas", "provinsi", "level", "harga"]

    catalog = discover_files()
    if catalog.empty:
        # Tidak ada file CSV yang cocok dengan pola nama yang diharapkan.
        return pd.DataFrame(columns=kolom_kosong)

    frames = []
    for _, row in catalog.iterrows():
        try:
            wide = pd.read_csv(row["path"])
        except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError):
            # File individual gagal dibaca -> lewati, jangan gagalkan
            # keseluruhan proses pemuatan data.
            continue
        frames.append(
            _melt_wide_to_long(wide, row["level"], komoditas=row["komoditas"])
        )

    if not frames:
        return pd.DataFrame(columns=kolom_kosong)

    df = pd.concat(frames, ignore_index=True)
    df["level"] = pd.Categorical(df["level"], categories=LEVEL_ORDER, ordered=True)
    df["komoditas"] = df["komoditas"].astype("category")

    # Urutkan agar konsisten & enak dibaca saat ditampilkan mentah
    # (mis. di halaman Data Explorer).
    df = df.sort_values(
        ["komoditas", "level", "tanggal", "provinsi"]
    ).reset_index(drop=True)

    return df


# --------------------------------------------------------------------------
# Transformasi analitik
# --------------------------------------------------------------------------

FREQ_MAP = {"Harian": "D", "Mingguan": "W", "Bulanan": "ME", "Kuartalan": "QE"}


def apply_filters(
    df: pd.DataFrame,
    provinsi: list[str] | None,
    date_range: tuple | None,
) -> pd.DataFrame:
    """Terapkan filter provinsi dan rentang tanggal."""
    out = df
    if provinsi:
        out = out[out["provinsi"].isin(provinsi)]
    if date_range and len(date_range) == 2 and all(date_range):
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        out = out[(out["tanggal"] >= start) & (out["tanggal"] <= end)]
    return out


def national_series(df: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """
    Rata-rata nasional per level pasar, di-resample ke frekuensi tertentu.
    Hasil: tanggal | level | harga
    """
    daily = (
        df.groupby(["tanggal", "level"], observed=True)["harga"].mean().reset_index()
    )
    if freq == "D":
        return daily

    out = (
        daily.set_index("tanggal")
        .groupby("level", observed=True)["harga"]
        .resample(freq)
        .mean()
        .reset_index()
        .dropna(subset=["harga"])
    )
    return out


def pivot_levels(df: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """
    Tabel lebar: tanggal | Produsen | Tradisional | Modern
    plus kolom margin absolut dan margin persentase.
    """
    series = national_series(df, freq)
    wide = series.pivot(index="tanggal", columns="level", values="harga")
    wide = wide.reindex(columns=[c for c in LEVEL_ORDER if c in wide.columns])
    wide = wide.reset_index()
    wide.columns.name = None

    if {"Produsen", "Tradisional"}.issubset(wide.columns):
        wide["margin_tradisional"] = wide["Tradisional"] - wide["Produsen"]
        wide["margin_tradisional_pct"] = (
            wide["margin_tradisional"] / wide["Produsen"] * 100
        )
    if {"Produsen", "Modern"}.issubset(wide.columns):
        wide["margin_modern"] = wide["Modern"] - wide["Produsen"]
        wide["margin_modern_pct"] = wide["margin_modern"] / wide["Produsen"] * 100

    return wide


def province_summary(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """
    Statistik per provinsi untuk satu level pasar:
    rata-rata, min, maks, standar deviasi, dan koefisien variasi (%).
    """
    sub = df[df["level"] == level]
    if sub.empty:
        return pd.DataFrame()

    stats = (
        sub.groupby("provinsi")["harga"]
        .agg(["mean", "median", "min", "max", "std"])
        .reset_index()
    )
    stats["cv_pct"] = stats["std"] / stats["mean"] * 100
    stats["rentang"] = stats["max"] - stats["min"]
    stats = stats.rename(
        columns={
            "mean": "rata_rata",
            "median": "median",
            "min": "minimum",
            "max": "maksimum",
            "std": "std_dev",
        }
    )
    return stats.sort_values("rata_rata", ascending=False).reset_index(drop=True)


def quarterly_margin(df: pd.DataFrame) -> pd.DataFrame:
    """Rata-rata margin per kuartal, format panjang untuk bar chart berkelompok."""
    wide = pivot_levels(df, freq="D")
    if wide.empty:
        return pd.DataFrame()

    wide["kuartal"] = wide["tanggal"].dt.to_period("Q").astype(str)
    cols = [c for c in ["margin_tradisional", "margin_modern"] if c in wide.columns]
    if not cols:
        return pd.DataFrame()

    agg = wide.groupby("kuartal")[cols].mean().reset_index()
    long = agg.melt(id_vars="kuartal", var_name="jenis", value_name="margin")
    long["jenis"] = long["jenis"].map(
        {
            "margin_tradisional": "Tradisional − Produsen",
            "margin_modern": "Modern − Produsen",
        }
    )
    return long


def volatility_table(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Rata-rata nasional harian + kuartal, untuk boxplot volatilitas."""
    sub = df[df["level"] == level]
    if sub.empty:
        return pd.DataFrame()

    daily = sub.groupby("tanggal")["harga"].mean().reset_index()
    daily["kuartal"] = daily["tanggal"].dt.to_period("Q").astype(str)
    daily["tahun"] = daily["tanggal"].dt.year
    return daily


def kpi_snapshot(df: pd.DataFrame) -> dict:
    """
    Ringkasan angka kunci untuk kartu KPI di halaman utama.
    Perbandingan memakai rata-rata 30 hari terakhir vs 30 hari sebelumnya.
    """
    out: dict = {}
    if df.empty:
        return out

    ref_level = "Tradisional" if "Tradisional" in df["level"].unique() else df["level"].iloc[0]
    sub = df[df["level"] == ref_level]
    daily = sub.groupby("tanggal")["harga"].mean().sort_index()

    out["level_acuan"] = ref_level
    out["harga_terakhir"] = float(daily.iloc[-1])
    out["tanggal_terakhir"] = daily.index[-1]

    akhir = daily.index[-1]
    last_30 = daily.loc[akhir - pd.Timedelta(days=30) : akhir].mean()
    prev_30 = daily.loc[akhir - pd.Timedelta(days=60) : akhir - pd.Timedelta(days=31)].mean()
    out["delta_30d_pct"] = (
        float((last_30 - prev_30) / prev_30 * 100)
        if prev_30 and not np.isnan(prev_30)
        else float("nan")
    )

    # Perubahan Week-over-Week (WoW): rata-rata 7 hari terakhir vs 7 hari
    # sebelumnya. Melengkapi delta_30d_pct (Month-over-Month) di atas agar
    # Executive Summary bisa menampilkan kedua horizon waktu.
    last_7 = daily.loc[akhir - pd.Timedelta(days=7) : akhir].mean()
    prev_7 = daily.loc[akhir - pd.Timedelta(days=14) : akhir - pd.Timedelta(days=8)].mean()
    out["delta_7d_pct"] = (
        float((last_7 - prev_7) / prev_7 * 100)
        if prev_7 and not np.isnan(prev_7)
        else float("nan")
    )

    wide = pivot_levels(df, freq="D")
    if "margin_tradisional" in wide.columns:
        out["margin_tradisional"] = float(wide["margin_tradisional"].mean())
        out["margin_tradisional_pct"] = float(wide["margin_tradisional_pct"].mean())
    if "margin_modern" in wide.columns:
        out["margin_modern"] = float(wide["margin_modern"].mean())
        out["margin_modern_pct"] = float(wide["margin_modern_pct"].mean())

    prov = province_summary(df, ref_level)
    if not prov.empty:
        out["provinsi_termahal"] = prov.iloc[0]["provinsi"]
        out["harga_termahal"] = float(prov.iloc[0]["rata_rata"])
        out["provinsi_termurah"] = prov.iloc[-1]["provinsi"]
        out["harga_termurah"] = float(prov.iloc[-1]["rata_rata"])
        out["disparitas"] = out["harga_termahal"] - out["harga_termurah"]
        out["cv_nasional"] = float(daily.std() / daily.mean() * 100)

    return out


def format_rupiah(value: float, decimals: int = 0) -> str:
    """12345.6 -> 'Rp12.346' (format Indonesia: titik sebagai pemisah ribuan)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "–"
    formatted = f"{value:,.{decimals}f}"
    formatted = formatted.replace(",", "#").replace(".", ",").replace("#", ".")
    return f"Rp{formatted}"
