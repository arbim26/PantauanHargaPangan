"""Halaman 2 — Margin antar level rantai pasok (produsen → pasar)."""

import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Margin rantai pasok",
    "Selisih harga antara produsen dan pasar sebagai indikator efisiensi "
    "distribusi serta marjin perantara.",
)

f = ui.sidebar_filters()
df = f["df"]

wide = D.pivot_levels(df, f["freq"])
if wide.empty or "margin_tradisional" not in wide.columns:
    st.warning("Data margin tidak tersedia untuk kombinasi filter ini.")
    st.stop()

ui.render_kpis(
    [
        ui.kpi_card(
            "Rata-rata margin tradisional",
            D.format_rupiah(wide["margin_tradisional"].mean()),
            f"{wide['margin_tradisional_pct'].mean():.1f}% di atas harga produsen",
        ),
        ui.kpi_card(
            "Margin tertinggi",
            D.format_rupiah(wide["margin_tradisional"].max()),
            f"tercatat pada {wide.loc[wide['margin_tradisional'].idxmax(), 'tanggal']:%b %Y}",
        ),
        ui.kpi_card(
            "Margin terendah",
            D.format_rupiah(wide["margin_tradisional"].min()),
            f"tercatat pada {wide.loc[wide['margin_tradisional'].idxmin(), 'tanggal']:%b %Y}",
        ),
    ]
)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------ Bar chart margin kuartal
st.subheader("Rata-rata margin per kuartal")

qm = D.quarterly_margin(df)

fig = go.Figure()
s = qm[qm["jenis"] == "Tradisional − Produsen"]
fig.add_trace(
    go.Bar(
        x=s["kuartal"], y=s["margin"], name="Tradisional − Produsen",
        marker_color="#E07A28",
        hovertemplate="<b>Tradisional − Produsen</b><br>%{x}<br>Rp%{y:,.0f}/kg<extra></extra>",
    )
)

fig.update_layout(
    barmode="group", height=420, plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(title="Margin (Rp/kg)", gridcolor="#eeece7"),
    xaxis=dict(title="Kuartal"),
)
# Garis batas: rata-rata margin tradisional sepanjang periode terpilih,
# sebagai patokan untuk menilai kuartal mana yang di atas/di bawah normal.
ui.add_ref_hline(
    fig, wide["margin_tradisional"].mean(),
    f"Rata-rata margin: {D.format_rupiah(wide['margin_tradisional'].mean())}",
)
st.plotly_chart(fig, **ui.STRETCH)

# ------------------------------------ Alert kebijakan: batas rata-rata margin
# Garis rata-rata margin di atas diperlakukan sebagai batas maksimal wajar.
# Jika margin kuartal TERBARU melebihinya, tandai sebagai perlu perhatian
# kebijakan (mis. pengawasan rantai distribusi/perantara).
qm_trad = qm[qm["jenis"] == "Tradisional − Produsen"].sort_values("kuartal")
if not qm_trad.empty:
    kuartal_now = qm_trad.iloc[-1]
    margin_rata2 = wide["margin_tradisional"].mean()
    ui.policy_alert(
        breached=kuartal_now["margin"] > margin_rata2,
        label=f"Margin kuartal {kuartal_now['kuartal']}",
        breach_detail=(
            f"Margin tradisional ({D.format_rupiah(kuartal_now['margin'])}) melebihi "
            f"batas rata-rata margin sepanjang periode terpilih "
            f"({D.format_rupiah(margin_rata2)})."
        ),
        ok_detail=(
            f"Margin tradisional ({D.format_rupiah(kuartal_now['margin'])}) masih di bawah "
            f"batas rata-rata margin sepanjang periode terpilih "
            f"({D.format_rupiah(margin_rata2)})."
        ),
    )

# ----------------------------------------------------- Margin persentase
st.subheader("Margin relatif terhadap harga produsen")

fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=wide["tanggal"], y=wide["margin_tradisional_pct"],
        name="Tradisional", mode="lines", line=dict(color="#E07A28", width=2.4),
        hovertemplate="Tradisional<br>%{x|%b %Y}<br>%{y:.1f}%<extra></extra>",
    )
)
fig2.update_layout(
    height=360, hovermode="x unified", plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    yaxis=dict(title="Markup (%)", gridcolor="#eeece7", ticksuffix="%"),
)
# Garis batas: 0% = harga pasar sama persis dengan harga produsen (impas,
# tanpa markup). Di bawah garis ini berarti margin negatif — kondisi tak lazim
# yang patut diperiksa (mis. subsidi atau kesalahan data).
ui.add_ref_hline(fig2, 0, "Impas (markup 0%)", color="#9ca3af", position="bottom right")
st.plotly_chart(fig2, **ui.STRETCH)

ui.insight(
    "Margin yang <b>melebar</b> saat harga produsen turun menandakan penurunan "
    "di tingkat petani tidak diteruskan ke konsumen. Sebaliknya, margin yang "
    "<b>menyempit</b> saat harga produsen naik menunjukkan pedagang menyerap "
    "sebagian kenaikan biaya."
)

with st.expander("Lihat tabel margin"):
    tampil = wide[[c for c in wide.columns if c != "tanggal"]].copy()
    tampil.insert(0, "Periode", wide["tanggal"].dt.strftime("%b %Y"))
    st.dataframe(tampil.round(1), **ui.STRETCH, hide_index=True)
    ui.download_button(tampil, f"margin_{f['komoditas'].lower()}.csv")