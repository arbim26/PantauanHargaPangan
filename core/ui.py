"""
Lapisan presentasi: tema, CSS kustom, dan komponen UI yang dipakai ulang
di seluruh halaman (sidebar filter, kartu KPI, header halaman).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import data as D

PAGE_ICON = "🌾"


def _version_tuple(v: str) -> tuple:
    parts = []
    for chunk in v.split(".")[:3]:
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


# Streamlit >= 1.49 mengganti `use_container_width` dengan `width`.
# STRETCH dipakai sebagai **kwargs agar kode berjalan di kedua versi.
STRETCH = (
    {"width": "stretch"}
    if _version_tuple(st.__version__) >= (1, 49, 0)
    else {"use_container_width": True}
)

CUSTOM_CSS = """
<style>
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px; }

    /* Header halaman */
    .page-title { font-size: 1.75rem; font-weight: 650; margin-bottom: .1rem; }
    .page-sub   { color: #6b7280; font-size: .92rem; margin-bottom: 1.4rem; }

    /* Kartu KPI */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e8e6e1;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        height: 100%;
    }
    .kpi-label { font-size: .78rem; color: #6b7280; letter-spacing: .02em; }
    .kpi-value { font-size: 1.55rem; font-weight: 650; line-height: 1.25; margin-top: .2rem; }
    .kpi-note  { font-size: .78rem; color: #6b7280; margin-top: .15rem; }
    .kpi-up    { color: #c0392b; font-weight: 600; }
    .kpi-down  { color: #1e8e5a; font-weight: 600; }

    /* Kotak insight */
    .insight {
        background: #f7f5f0;
        border-left: 3px solid #E07A28;
        border-radius: 0 8px 8px 0;
        padding: .85rem 1rem;
        font-size: .9rem;
        line-height: 1.6;
        margin: 1rem 0;
    }

    section[data-testid="stSidebar"] { background: #fbfaf7; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    hr { margin: 1.6rem 0; }
</style>
"""


def setup_page(title: str, subtitle: str = "") -> None:
    """Konfigurasi halaman + header. Panggil di baris pertama setiap halaman."""
    st.set_page_config(
        page_title=f"{title} · Dashboard Pangan",
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def sidebar_filters() -> dict:
    """
    Filter global di sidebar. Pilihan disimpan di session_state supaya
    konsisten saat pengguna berpindah halaman.
    """
    catalog = D.discover_files()

    with st.sidebar:
        st.markdown("### Filter data")

        if catalog.empty:
            st.error(
                "Dataset tidak ditemukan. Pastikan folder "
                "`data/data_komoditas_pangan/` sudah ada di direktori proyek."
            )
            st.stop()

        komoditas_list = sorted(catalog["komoditas"].unique())
        default_idx = (
            komoditas_list.index("Beras") if "Beras" in komoditas_list else 0
        )
        komoditas = st.selectbox(
            "Komoditas",
            komoditas_list,
            index=st.session_state.get("komoditas_idx", default_idx),
            key="komoditas_select",
        )
        st.session_state["komoditas_idx"] = komoditas_list.index(komoditas)

        df = D.load_commodity(komoditas)
        min_date = df["tanggal"].min().date()
        max_date = df["tanggal"].max().date()

        date_range = st.date_input(
            "Rentang tanggal",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="date_range",
        )

        all_prov = sorted(df["provinsi"].unique())
        pilih_semua = st.checkbox("Semua provinsi", value=True, key="all_prov")
        if pilih_semua:
            provinsi = all_prov
        else:
            provinsi = st.multiselect(
                "Provinsi",
                all_prov,
                default=all_prov[:6],
                key="prov_select",
            )
            if not provinsi:
                st.warning("Pilih minimal satu provinsi.")
                st.stop()

        freq_label = st.radio(
            "Agregasi waktu",
            list(D.FREQ_MAP.keys()),
            index=2,
            horizontal=True,
            key="freq",
        )

        st.divider()
        st.caption(
            f"**{komoditas}** · {len(provinsi)} provinsi · "
            f"{min_date:%b %Y} – {max_date:%b %Y}"
        )

    filtered = D.apply_filters(df, provinsi, date_range)

    return {
        "komoditas": komoditas,
        "df": filtered,
        "df_full": df,
        "provinsi": provinsi,
        "date_range": date_range,
        "freq_label": freq_label,
        "freq": D.FREQ_MAP[freq_label],
    }


def kpi_card(label: str, value: str, note: str = "", tone: str = "") -> str:
    """Membangun HTML satu kartu KPI. tone: '', 'up', atau 'down'."""
    cls = {"up": "kpi-up", "down": "kpi-down"}.get(tone, "kpi-note")
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-note {cls}">{note}</div>'
        f"</div>"
    )


def render_kpis(cards: list[str]) -> None:
    """Menampilkan deretan kartu KPI dalam kolom yang rata tinggi."""
    cols = st.columns(len(cards), gap="small")
    for col, html in zip(cols, cards):
        with col:
            st.markdown(html, unsafe_allow_html=True)


def render_executive_summary(kpi: dict, komoditas: str) -> None:
    """
    Ringkasan eksekutif di halaman utama, memakai komponen NATIVE
    Streamlit (st.columns + st.metric) — bukan HTML kustom — sehingga:
      * otomatis mengikuti tema light/dark bawaan Streamlit,
      * delta arrow (▲/▼) & warna merah/hijau ditangani otomatis oleh
        st.metric, tidak perlu logika manual.

    Untuk metrik HARGA, kita pakai delta_color="inverse": kenaikan harga
    (delta positif) berarti buruk bagi konsumen -> ditampilkan MERAH.
    Penurunan harga -> HIJAU. Ini kebalikan dari default st.metric
    (yang menganggap naik = hijau), makanya harus di-set eksplisit.
    """
    if not kpi:
        st.info("Data tidak tersedia untuk menampilkan ringkasan eksekutif pada filter saat ini.")
        return

    def _delta_str(pct: float) -> str | None:
        """None jika NaN (mis. data historis < 60 hari), agar st.metric tidak menampilkan '+nan%'."""
        return f"{pct:+.1f}%" if pct == pct else None  # pct == pct -> False jika NaN

    level_acuan = kpi.get("level_acuan", "–")
    tanggal_terakhir = kpi.get("tanggal_terakhir")
    if tanggal_terakhir is not None:
        st.caption(
            f"Data terbaru: **{tanggal_terakhir:%d %B %Y}** · level acuan: pasar **{level_acuan}**"
        )

    # --- Baris 1: harga terkini (+ MoM), perubahan mingguan (WoW), margin
    row1 = st.columns(3, gap="small")
    with row1[0]:
        st.metric(
            f"Harga {komoditas} hari ini",
            D.format_rupiah(kpi.get("harga_terakhir")),
            delta=_delta_str(kpi.get("delta_30d_pct", float("nan"))),
            delta_color="inverse",
            help="Rata-rata harga terbaru di pasar acuan. Delta = perubahan "
            "Month-over-Month (rata-rata 30 hari terakhir vs 30 hari sebelumnya).",
        )
    with row1[1]:
        st.metric(
            "Perubahan mingguan (WoW)",
            _delta_str(kpi.get("delta_7d_pct", float("nan"))) or "–",
            delta=_delta_str(kpi.get("delta_7d_pct", float("nan"))),
            delta_color="inverse",
            help="Perubahan Week-over-Week: rata-rata 7 hari terakhir vs 7 hari sebelumnya.",
        )
    with row1[2]:
        st.metric(
            "Margin tradisional",
            D.format_rupiah(kpi.get("margin_tradisional", float("nan"))),
            delta=(
                f"markup {kpi['margin_tradisional_pct']:.1f}% dari harga produsen"
                if "margin_tradisional_pct" in kpi
                else None
            ),
            delta_color="off",
            help="Selisih harga rata-rata antara pasar tradisional dan produsen.",
        )

    # --- Baris 2: provinsi termahal, disparitas antarprovinsi, volatilitas
    row2 = st.columns(3, gap="small")
    with row2[0]:
        st.metric(
            "Provinsi termahal",
            kpi.get("provinsi_termahal", "–"),
            delta=(
                D.format_rupiah(kpi["harga_termahal"])
                if "harga_termahal" in kpi
                else None
            ),
            delta_color="off",
        )
    with row2[1]:
        st.metric(
            "Disparitas antarprovinsi",
            D.format_rupiah(kpi.get("disparitas", float("nan"))),
            delta=(
                f"termurah: {kpi['provinsi_termurah']}"
                if "provinsi_termurah" in kpi
                else None
            ),
            delta_color="off",
            help="Selisih harga rata-rata antara provinsi termahal dan termurah.",
        )
    with row2[2]:
        st.metric(
            "Volatilitas nasional",
            f"{kpi.get('cv_nasional', 0):.1f}%",
            help="Coefficient of Variation (CV) harga harian nasional — "
            "semakin tinggi, semakin fluktuatif harga komoditas ini.",
        )


def add_ref_hline(fig, value: float, label: str, color: str = "#6b7280", position: str = "top right") -> None:
    """
    Tambahkan garis batas HORIZONTAL putus-putus (mis. rata-rata, patokan/HET,
    garis impas 0%) beserta label ke sebuah figure Plotly.

    Dipakai berulang di banyak halaman supaya gaya garis batas konsisten —
    daripada menulis fig.add_hline(...) dengan styling berbeda di tiap file.
    Melewatkan value=NaN/None otomatis diabaikan (aman dipanggil meski data kosong).
    """
    if value is None or value != value:  # None atau NaN
        return
    fig.add_hline(
        y=value,
        line_dash="dash",
        line_color=color,
        line_width=1.4,
        annotation_text=label,
        annotation_position=position,
        annotation_font_size=11,
        annotation_font_color=color,
    )


def add_ref_vline(fig, value: float, label: str, color: str = "#6b7280", position: str = "top") -> None:
    """Versi VERTIKAL dari add_ref_hline — untuk grafik bar horizontal/histogram."""
    if value is None or value != value:
        return
    fig.add_vline(
        x=value,
        line_dash="dash",
        line_color=color,
        line_width=1.4,
        annotation_text=label,
        annotation_position=position,
        annotation_font_size=11,
        annotation_font_color=color,
    )


def policy_alert(breached: bool, label: str, breach_detail: str, ok_detail: str) -> None:
    """
    Banner kebijakan generik. Dipakai di halaman mana pun yang memperlakukan
    garis rata-rata (add_ref_hline/add_ref_vline) sebagai BATAS MAKSIMAL:

        breached=True  -> banner MERAH (st.error): nilai melewati batas,
                           kebijakan/intervensi perlu dipertimbangkan.
        breached=False -> banner HIJAU (st.success): masih dalam batas wajar.

    label          : nama singkat entitas yang diperiksa (mis. nama kuartal).
    breach_detail  : kalimat penjelasan kondisi saat batas dilanggar
                      (sudah memuat angka-angka relevan).
    ok_detail      : kalimat penjelasan kondisi saat masih aman.
    """
    if breached:
        st.error(
            f"⚠️ **{label}** — {breach_detail} "
            f"Kebijakan atau langkah intervensi perlu dipertimbangkan."
        )
    else:
        st.success(f"✅ **{label}** — {ok_detail}")


def insight(text: str) -> None:
    st.markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)


def download_button(df: pd.DataFrame, filename: str, label: str = "Unduh CSV") -> None:
    st.download_button(
        label,
        df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        **STRETCH,
    )
