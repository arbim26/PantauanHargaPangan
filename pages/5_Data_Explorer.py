"""Halaman 5 — Penjelajah data mentah dan kualitas data."""

import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Data explorer",
    "Telusuri data mentah, periksa kualitasnya, dan unduh subset sesuai filter.",
)

f = ui.sidebar_filters()
df = f["df"]
full = f["df_full"]

tab1, tab2, tab3 = st.tabs(["Data terfilter", "Kualitas data", "Katalog berkas"])

with tab1:
    st.caption(f"{len(df):,} baris setelah filter diterapkan.")

    c1, c2 = st.columns(2)
    with c1:
        level_pick = st.multiselect(
            "Level pasar", D.LEVEL_ORDER, default=D.LEVEL_ORDER
        )
    with c2:
        bentuk = st.radio(
            "Bentuk tabel", ["Panjang (tidy)", "Lebar (provinsi sebagai kolom)"],
            horizontal=True,
        )

    view = df[df["level"].isin(level_pick)]

    if bentuk.startswith("Lebar"):
        view = (
            view.pivot_table(
                index=["tanggal", "level"], columns="provinsi",
                values="harga", aggfunc="mean", observed=True,
            )
            .reset_index()
        )
        view.columns.name = None
    else:
        view = view.rename(
            columns={"tanggal": "Tanggal", "provinsi": "Provinsi",
                     "level": "Level pasar", "harga": "Harga (Rp/kg)"}
        )

    st.dataframe(view.head(2000), **ui.STRETCH, hide_index=True)
    if len(view) > 2000:
        st.caption("Menampilkan 2.000 baris pertama. Unduh CSV untuk data lengkap.")
    ui.download_button(view, f"data_{f['komoditas'].lower()}.csv")

with tab2:
    st.subheader("Cakupan dan kelengkapan")

    ringkas = (
        full.groupby("level", observed=True)
        .agg(
            baris=("harga", "size"),
            provinsi=("provinsi", "nunique"),
            tanggal_awal=("tanggal", "min"),
            tanggal_akhir=("tanggal", "max"),
            harga_min=("harga", "min"),
            harga_maks=("harga", "max"),
            harga_rata=("harga", "mean"),
        )
        .reset_index()
    )
    ringkas["tanggal_awal"] = ringkas["tanggal_awal"].dt.strftime("%d %b %Y")
    ringkas["tanggal_akhir"] = ringkas["tanggal_akhir"].dt.strftime("%d %b %Y")
    st.dataframe(ringkas.round(0), **ui.STRETCH, hide_index=True)

    st.subheader("Provinsi yang tidak tersedia di semua level")
    per_level = {
        lvl: set(full[full["level"] == lvl]["provinsi"].unique())
        for lvl in full["level"].unique()
    }
    semua = set().union(*per_level.values()) if per_level else set()
    irisan = set.intersection(*per_level.values()) if per_level else set()
    beda = sorted(semua - irisan)

    if beda:
        st.warning(
            "Provinsi berikut tidak lengkap di seluruh level pasar, sehingga "
            "analisis margin untuk wilayah tersebut perlu dibaca hati-hati: "
            + ", ".join(beda)
        )
    else:
        st.success("Semua provinsi tersedia di ketiga level pasar.")

    st.subheader("Deteksi nilai ekstrem")
    level_out = st.selectbox("Level pasar", D.LEVEL_ORDER, index=1, key="outlier_lvl")
    sub = full[full["level"] == level_out]
    q1, q3 = sub["harga"].quantile([0.25, 0.75])
    iqr = q3 - q1
    batas_bawah, batas_atas = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outlier = sub[(sub["harga"] < batas_bawah) | (sub["harga"] > batas_atas)]

    st.caption(
        f"Batas IQR: {D.format_rupiah(batas_bawah)} – {D.format_rupiah(batas_atas)} · "
        f"{len(outlier):,} observasi di luar batas ({len(outlier)/len(sub)*100:.2f}%)."
    )
    if not outlier.empty:
        teratas = (
            outlier.groupby("provinsi")["harga"]
            .agg(jumlah="size", rata_rata="mean")
            .sort_values("jumlah", ascending=False)
            .head(10)
            .reset_index()
        )
        st.dataframe(teratas.round(0), **ui.STRETCH, hide_index=True)

with tab3:
    st.subheader("Berkas sumber yang terdeteksi")
    katalog = D.discover_files()
    st.dataframe(
        katalog[["komoditas", "level", "path"]],
        **ui.STRETCH, hide_index=True,
    )
    st.caption(f"Total {len(katalog)} berkas CSV ditemukan.")
