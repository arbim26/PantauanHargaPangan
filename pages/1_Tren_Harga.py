"""Halaman 1 — Analisis tren harga lintas waktu dan lintas provinsi."""

import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Tren harga",
    "Pergerakan harga menurut level pasar, dengan perbandingan antarprovinsi.",
)

f = ui.sidebar_filters()
df = f["df"]

if df.empty:
    st.warning("Tidak ada data pada filter yang dipilih.")
    st.stop()

c1, c2 = st.columns([3, 1])
with c2:
    show_area = st.toggle("Tampilkan rentang antarprovinsi", value=False)

series = D.national_series(df, f["freq"])

fig = go.Figure()

# Pita min–maks antarprovinsi untuk level tradisional (konteks sebaran)
if show_area:
    trad = df[df["level"] == "Tradisional"]
    if not trad.empty:
        band = (
            trad.groupby("tanggal")["harga"]
            .agg(["min", "max"])
            .resample(f["freq"] if f["freq"] != "D" else "D")
            .agg({"min": "min", "max": "max"})
            .dropna()
            .reset_index()
        )
        fig.add_trace(
            go.Scatter(
                x=band["tanggal"], y=band["max"], mode="lines",
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=band["tanggal"], y=band["min"], mode="lines", fill="tonexty",
                fillcolor="rgba(224,122,40,0.12)", line=dict(width=0),
                name="Rentang provinsi (tradisional)", hoverinfo="skip",
            )
        )

for level in D.LEVEL_ORDER:
    sub = series[series["level"] == level].copy()
    if sub.empty:
        continue
    y = sub["harga"]
    fig.add_trace(
        go.Scatter(
            x=sub["tanggal"], y=y, name=level, mode="lines",
            line=dict(color=D.LEVEL_COLORS[level], width=2.4),
            hovertemplate=f"<b>{level}</b><br>%{{x|%d %b %Y}}<br>Rp%{{y:,.0f}}<extra></extra>",
        )
    )

fig.update_layout(
    height=460, hovermode="x unified", plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
    xaxis=dict(gridcolor="#f5f4f1"),
)
with c1:
    st.plotly_chart(fig, **ui.STRETCH)

st.divider()

# ------------------------------------------- Perbandingan antarprovinsi
st.subheader("Perbandingan antarprovinsi")

col_a, col_b = st.columns([1, 3])
with col_a:
    level_pick = st.selectbox("Level pasar", D.LEVEL_ORDER, index=1)
    prov_all = sorted(df["provinsi"].unique())
    default_prov = [p for p in ["DKI Jakarta", "Jawa Barat", "Jawa Timur", "Papua"] if p in prov_all]
    prov_pick = st.multiselect(
        "Provinsi dibandingkan", prov_all, default=default_prov or prov_all[:4]
    )

sub = df[(df["level"] == level_pick) & (df["provinsi"].isin(prov_pick))]

if sub.empty:
    st.info("Pilih minimal satu provinsi untuk dibandingkan.")
else:
    resampled = (
        sub.set_index("tanggal")
        .groupby("provinsi")["harga"]
        .resample(f["freq"] if f["freq"] != "D" else "D")
        .mean()
        .reset_index()
        .dropna()
    )
    fig2 = go.Figure()
    for p in prov_pick:
        s = resampled[resampled["provinsi"] == p]
        fig2.add_trace(
            go.Scatter(
                x=s["tanggal"], y=s["harga"], name=p, mode="lines",
                line=dict(width=2),
                hovertemplate=f"<b>{p}</b><br>%{{x|%b %Y}}<br>Rp%{{y:,.0f}}<extra></extra>",
            )
        )
    fig2.update_layout(
        height=420, hovermode="x unified", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
        xaxis=dict(gridcolor="#f5f4f1"),
    )
    with col_b:
        st.plotly_chart(fig2, **ui.STRETCH)

# --------------------------------------------------- Pola musiman bulanan
st.divider()
st.subheader("Pola musiman — rata-rata harga per bulan")

seasonal = df[df["level"] == level_pick].copy()
seasonal["bulan"] = seasonal["tanggal"].dt.month
seasonal["tahun"] = seasonal["tanggal"].dt.year
pivot = seasonal.pivot_table(
    index="tahun", columns="bulan", values="harga", aggfunc="mean"
)
nama_bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
pivot.columns = [nama_bulan[c - 1] for c in pivot.columns]

fig3 = go.Figure(
    go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index.astype(str),
        colorscale="YlOrRd",
        hovertemplate="%{y} %{x}<br>Rp%{z:,.0f}<extra></extra>",
        colorbar=dict(title="Rp/kg"),
    )
)
fig3.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig3, **ui.STRETCH)

ui.insight(
    "Heatmap ini membantu mengidentifikasi bulan-bulan dengan tekanan harga "
    "tertinggi. Pada komoditas pangan pokok, lonjakan biasanya terjadi menjelang "
    "hari besar keagamaan dan pada masa paceklik sebelum panen raya."
)
