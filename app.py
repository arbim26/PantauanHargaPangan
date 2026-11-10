"""
Dashboard Analisis Harga Komoditas Pangan Indonesia (2022–2026)
Halaman utama: ringkasan eksekutif.

Jalankan dengan:  streamlit run app.py
"""

import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Dashboard harga pangan nasional",
    "Analisis harga tiga level rantai pasok — produsen, pasar tradisional, "
    "dan pasar modern — di 34 provinsi, periode 2022–2026.",
)

f = ui.sidebar_filters()
df = f["df"]
kpi = D.kpi_snapshot(df)

if not kpi:
    st.warning("Tidak ada data pada filter yang dipilih.")
    st.stop()

# --------------------------------------------------------- Executive Summary
# Ringkasan eksekutif native (st.columns + st.metric) dengan delta MoM & WoW.
# Lihat core/ui.py::render_executive_summary untuk detail logika warna delta.
st.subheader("Ringkasan eksekutif")
ui.render_executive_summary(kpi, f["komoditas"])

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------- Grafik tren utama
st.subheader("Tren harga rata-rata nasional")

series = D.national_series(df, f["freq"])
fig = go.Figure()
for level in D.LEVEL_ORDER:
    sub = series[series["level"] == level]
    if sub.empty:
        continue
    fig.add_trace(
        go.Scatter(
            x=sub["tanggal"],
            y=sub["harga"],
            name=level,
            mode="lines",
            line=dict(color=D.LEVEL_COLORS[level], width=2.4),
            hovertemplate=f"<b>{level}</b><br>%{{x|%d %b %Y}}<br>Rp%{{y:,.0f}}/kg<extra></extra>",
        )
    )

fig.update_layout(
    height=420,
    hovermode="x unified",
    plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
    xaxis=dict(title="", gridcolor="#f5f4f1"),
)
st.plotly_chart(fig, **ui.STRETCH)

# ------------------------------------------------------- Insight otomatis
wide = D.pivot_levels(df, f["freq"])
if len(wide) > 1 and "Tradisional" in wide.columns:
    awal = wide["Tradisional"].iloc[0]
    akhir = wide["Tradisional"].iloc[-1]
    growth = (akhir - awal) / awal * 100
    ui.insight(
        f"Harga <b>{f['komoditas']}</b> di pasar tradisional bergerak dari "
        f"{D.format_rupiah(awal)} menjadi {D.format_rupiah(akhir)} "
        f"sepanjang periode terpilih — perubahan <b>{growth:+.1f}%</b>. "
        f"Selisih harga antara pasar tradisional dan produsen rata-rata "
        f"{D.format_rupiah(kpi.get('margin_tradisional', 0))}/kg, yang mencerminkan "
        f"biaya distribusi dan marjin pedagang perantara."
    )

# --------------------------------------------- Ranking provinsi ringkas
left, right = st.columns(2, gap="large")
prov = D.province_summary(df, kpi["level_acuan"])
rata_nasional = prov["rata_rata"].mean() if not prov.empty else float("nan")

with left:
    st.subheader("10 provinsi termahal")
    top = prov.head(10).sort_values("rata_rata")
    fig_top = go.Figure(
        go.Bar(
            x=top["rata_rata"],
            y=top["provinsi"],
            orientation="h",
            marker_color="#C0563A",
            hovertemplate="%{y}<br>Rp%{x:,.0f}/kg<extra></extra>",
        )
    )
    fig_top.update_layout(
        height=380,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Rata-rata harga (Rp/kg)", gridcolor="#eeece7"),
    )
    # Garis batas: rata-rata nasional, supaya terlihat seberapa jauh
    # provinsi termahal berada di atas rata-rata.
    ui.add_ref_vline(fig_top, rata_nasional, f"Rata-rata nasional: {D.format_rupiah(rata_nasional)}")
    st.plotly_chart(fig_top, **ui.STRETCH)

with right:
    st.subheader("10 provinsi termurah")
    bottom = prov.tail(10).sort_values("rata_rata", ascending=False)
    fig_bot = go.Figure(
        go.Bar(
            x=bottom["rata_rata"],
            y=bottom["provinsi"],
            orientation="h",
            marker_color="#2E7D5B",
            hovertemplate="%{y}<br>Rp%{x:,.0f}/kg<extra></extra>",
        )
    )
    fig_bot.update_layout(
        height=380,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Rata-rata harga (Rp/kg)", gridcolor="#eeece7"),
    )
    # Garis batas yang sama, supaya kedua chart bisa dibandingkan langsung.
    ui.add_ref_vline(fig_bot, rata_nasional, f"Rata-rata nasional: {D.format_rupiah(rata_nasional)}")
    st.plotly_chart(fig_bot, **ui.STRETCH)

st.divider()
st.caption(
    "Gunakan menu di sidebar kiri untuk berpindah ke analisis tren, margin "
    "rantai pasok, volatilitas, perbandingan antarprovinsi, dan data mentah."
)
