"""Halaman 4 — Perbandingan dan disparitas harga antarprovinsi."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Perbandingan antarprovinsi",
    "Peta panas harga per provinsi dari waktu ke waktu, serta besarnya "
    "kesenjangan harga antarwilayah.",
)

f = ui.sidebar_filters()
df = f["df"]

level = st.selectbox("Level pasar", D.LEVEL_ORDER, index=1)
sub = df[df["level"] == level]

if sub.empty:
    st.warning("Tidak ada data untuk level pasar ini.")
    st.stop()

# --------------------------------------------- Peta harga antarprovinsi
# Dua cara melihat hal yang sama: peta choropleth (visual, spasial) dan bar
# chart terurut (presisi, mudah dibaca angkanya) — keduanya memakai garis
# batas rata-rata nasional sebagai patokan.
st.subheader("Peta harga antarprovinsi")

prov_all_level = D.province_summary(sub, level)
rata_nasional_level = prov_all_level["rata_rata"].mean() if not prov_all_level.empty else float("nan")

tab_map, tab_bar = st.tabs(["🗺️ Peta interaktif (choropleth)", "📊 Bar chart terurut"])

with tab_map:
    geojson = D.load_provinces_geojson()
    if geojson is None:
        st.info(
            "Berkas GeoJSON batas provinsi tidak ditemukan di "
            "`data/geo/indonesia-38-provinces.geojson`. Gunakan tab "
            "**Bar chart terurut** sebagai gantinya, atau tempatkan berkas "
            "tersebut di lokasi itu untuk mengaktifkan peta."
        )
    else:
        peta_data = prov_all_level.copy()
        peta_data["provinsi_geo"] = peta_data["provinsi"].apply(D.to_geojson_name)

        fig_map = px.choropleth(
            peta_data,
            geojson=geojson,
            locations="provinsi_geo",
            featureidkey="properties.PROVINSI",
            color="rata_rata",
            color_continuous_scale="RdYlGn_r",
            hover_name="provinsi",
            hover_data={"provinsi_geo": False, "rata_rata": ":,.0f"},
            labels={"rata_rata": "Rata-rata (Rp/kg)"},
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar=dict(title="Rp/kg"),
        )
        st.plotly_chart(fig_map, **ui.STRETCH)
        st.caption(
            "Warna makin merah = harga makin tinggi. Provinsi hasil pemekaran "
            "Papua (Selatan/Tengah/Pegunungan/Barat Daya) tidak berwarna karena "
            "belum tercakup dalam dataset harga historis. Batas wilayah: "
            "*Indonesia GeoJSON & TopoJSON Maps (38 Provinces)* oleh "
            "denyherianto, lisensi CC BY 4.0."
        )

with tab_bar:
    bar_data = prov_all_level.sort_values("rata_rata", ascending=True)
    warna_bar = [
        "#C0563A" if v > rata_nasional_level else "#2E7D5B"
        for v in bar_data["rata_rata"]
    ]
    fig_bar = go.Figure(
        go.Bar(
            x=bar_data["rata_rata"], y=bar_data["provinsi"], orientation="h",
            marker_color=warna_bar,
            hovertemplate="%{y}<br>Rp%{x:,.0f}/kg<extra></extra>",
        )
    )
    fig_bar.update_layout(
        height=760, plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Rata-rata harga (Rp/kg)", gridcolor="#eeece7"),
    )
    # Garis batas: rata-rata nasional, sebagai patokan di atas/di bawah.
    ui.add_ref_vline(
        fig_bar, rata_nasional_level,
        f"Rata-rata nasional: {D.format_rupiah(rata_nasional_level)}",
    )
    st.plotly_chart(fig_bar, **ui.STRETCH)
    st.caption("🔴 Di atas rata-rata nasional · 🟢 Di bawah rata-rata nasional.")

    # Alert kebijakan: rata-rata nasional diperlakukan sebagai batas maksimal.
    breach_level = prov_all_level[prov_all_level["rata_rata"] > rata_nasional_level].sort_values(
        "rata_rata", ascending=False
    )
    ui.policy_alert(
        breached=not breach_level.empty,
        label="Rata-rata nasional sebagai batas maksimal wajar",
        breach_detail=(
            f"{len(breach_level)} dari {len(prov_all_level)} provinsi memiliki "
            f"harga di atas rata-rata nasional "
            f"({D.format_rupiah(rata_nasional_level)}), terutama: "
            f"{', '.join(breach_level['provinsi'].head(5))}."
        ),
        ok_detail=(
            f"Seluruh provinsi berada pada atau di bawah rata-rata nasional "
            f"({D.format_rupiah(rata_nasional_level)})."
        ),
    )

st.divider()

# ------------------------------------------------------------- Heatmap
st.subheader("Peta panas harga provinsi × waktu")

hm = (
    sub.set_index("tanggal")
    .groupby("provinsi")["harga"]
    .resample("QE")
    .mean()
    .reset_index()
)
hm["periode"] = hm["tanggal"].dt.to_period("Q").astype(str)
pivot = hm.pivot(index="provinsi", columns="periode", values="harga")
pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]

fig = go.Figure(
    go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale="RdYlGn_r",
        hovertemplate="%{y}<br>%{x}<br>Rp%{z:,.0f}<extra></extra>",
        colorbar=dict(title="Rp/kg"),
    )
)
fig.update_layout(
    height=760, margin=dict(l=10, r=10, t=20, b=10),
    xaxis=dict(tickangle=-45, title="Kuartal"),
)
st.plotly_chart(fig, **ui.STRETCH)

st.divider()

# ------------------------------------------------- Disparitas sepanjang waktu
st.subheader("Kesenjangan harga antarprovinsi")

gap = sub.groupby("tanggal")["harga"].agg(["min", "max", "mean"]).reset_index()
gap["selisih"] = gap["max"] - gap["min"]
gap = gap.set_index("tanggal").resample("ME").mean().reset_index()

fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(x=gap["tanggal"], y=gap["max"], name="Provinsi termahal",
               mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
)
fig2.add_trace(
    go.Scatter(x=gap["tanggal"], y=gap["min"], name="Rentang antarprovinsi",
               mode="lines", fill="tonexty", fillcolor="rgba(42,111,181,0.14)",
               line=dict(width=0), hoverinfo="skip")
)
fig2.add_trace(
    go.Scatter(x=gap["tanggal"], y=gap["mean"], name="Rata-rata nasional",
               mode="lines", line=dict(color="#2A6FB5", width=2.4),
               hovertemplate="%{x|%b %Y}<br>Rp%{y:,.0f}<extra></extra>")
)
fig2.update_layout(
    height=400, hovermode="x unified", plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
)
st.plotly_chart(fig2, **ui.STRETCH)

ui.render_kpis(
    [
        ui.kpi_card("Kesenjangan rata-rata", D.format_rupiah(gap["selisih"].mean()),
                    "selisih provinsi termahal dan termurah"),
        ui.kpi_card("Kesenjangan terlebar", D.format_rupiah(gap["selisih"].max()),
                    f"pada {gap.loc[gap['selisih'].idxmax(), 'tanggal']:%b %Y}"),
        ui.kpi_card("Kesenjangan tersempit", D.format_rupiah(gap["selisih"].min()),
                    f"pada {gap.loc[gap['selisih'].idxmin(), 'tanggal']:%b %Y}"),
    ]
)

st.divider()

# ------------------------------------------------------ Head-to-head provinsi
st.subheader("Bandingkan dua provinsi")

prov_all = sorted(sub["provinsi"].unique())
c1, c2 = st.columns(2)
with c1:
    p1 = st.selectbox("Provinsi A", prov_all, index=0)
with c2:
    p2 = st.selectbox("Provinsi B", prov_all, index=min(1, len(prov_all) - 1))

pair = (
    sub[sub["provinsi"].isin([p1, p2])]
    .set_index("tanggal")
    .groupby("provinsi")["harga"]
    .resample("ME")
    .mean()
    .reset_index()
)

fig3 = go.Figure()
for prov, color in [(p1, "#C0563A"), (p2, "#2E7D5B")]:
    s = pair[pair["provinsi"] == prov]
    fig3.add_trace(
        go.Scatter(x=s["tanggal"], y=s["harga"], name=prov, mode="lines",
                   line=dict(color=color, width=2.4),
                   hovertemplate=f"<b>{prov}</b><br>%{{x|%b %Y}}<br>Rp%{{y:,.0f}}<extra></extra>")
    )
fig3.update_layout(
    height=360, hovermode="x unified", plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
)
st.plotly_chart(fig3, **ui.STRETCH)

banding = pair.pivot(index="tanggal", columns="provinsi", values="harga").dropna()
if not banding.empty and p1 != p2:
    selisih = (banding[p1] - banding[p2]).mean()
    lebih = p1 if selisih > 0 else p2
    ui.insight(
        f"Sepanjang periode terpilih, harga di <b>{lebih}</b> rata-rata "
        f"{D.format_rupiah(abs(selisih))}/kg lebih tinggi. "
        f"Korelasi pergerakan kedua provinsi: "
        f"<b>{banding[p1].corr(banding[p2]):.2f}</b> — nilai mendekati 1 berarti "
        f"keduanya bergerak seirama, menandakan pasar yang terintegrasi."
    )
