"""Halaman 3 — Volatilitas dan distribusi harga."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Volatilitas dan distribusi",
    "Seberapa lebar rentang harga dan seberapa stabil pergerakannya di tiap "
    "kuartal dan tiap provinsi.",
)

f = ui.sidebar_filters()
df = f["df"]

level = st.selectbox("Level pasar yang dianalisis", D.LEVEL_ORDER, index=1)
daily = D.volatility_table(df, level)

if daily.empty:
    st.warning("Tidak ada data untuk level pasar ini.")
    st.stop()

# ------------------------------------------------------------- Boxplot
st.subheader("Sebaran harga per kuartal")

fig = px.box(
    daily, x="kuartal", y="harga", points=False,
    color_discrete_sequence=["#E07A28"],
)
fig.update_traces(marker_line_width=1, width=0.55)
fig.update_layout(
    height=440, plot_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis=dict(title="Harga rata-rata nasional (Rp/kg)", gridcolor="#eeece7"),
    xaxis=dict(title="Kuartal", tickangle=-45),
)
# Garis batas: rata-rata keseluruhan periode terpilih, sebagai patokan untuk
# menilai apakah suatu kuartal berada di atas/di bawah kondisi normal.
rata_keseluruhan = daily["harga"].mean()
ui.add_ref_hline(fig, rata_keseluruhan, f"Rata-rata periode: {D.format_rupiah(rata_keseluruhan)}")
st.plotly_chart(fig, **ui.STRETCH)

# ------------------------------------ Alert kebijakan: batas rata-rata periode
# Garis rata-rata periode di atas diperlakukan sebagai batas maksimal wajar.
# Jika rata-rata harga KUARTAL TERBARU melebihinya, tandai perlu perhatian.
kuartal_means = daily.groupby("kuartal")["harga"].mean().reset_index().sort_values("kuartal")
if not kuartal_means.empty:
    kuartal_now = kuartal_means.iloc[-1]
    ui.policy_alert(
        breached=kuartal_now["harga"] > rata_keseluruhan,
        label=f"Kuartal {kuartal_now['kuartal']}",
        breach_detail=(
            f"Rata-rata harga ({D.format_rupiah(kuartal_now['harga'])}) melebihi "
            f"batas rata-rata keseluruhan periode ({D.format_rupiah(rata_keseluruhan)})."
        ),
        ok_detail=(
            f"Rata-rata harga ({D.format_rupiah(kuartal_now['harga'])}) masih di bawah "
            f"batas rata-rata keseluruhan periode ({D.format_rupiah(rata_keseluruhan)})."
        ),
    )

ui.insight(
    "Kotak yang <b>tinggi</b> menandakan harga banyak bergerak dalam kuartal "
    "tersebut; kotak yang <b>pendek</b> menandakan harga relatif stabil. "
    "Garis di tengah kotak adalah median."
)

st.divider()

# ---------------------------------------------- Volatilitas per provinsi
st.subheader("Volatilitas per provinsi")

prov = D.province_summary(df, level)
prov_sorted = prov.sort_values("cv_pct", ascending=True).tail(20)

fig2 = go.Figure(
    go.Bar(
        x=prov_sorted["cv_pct"], y=prov_sorted["provinsi"], orientation="h",
        marker=dict(
            color=prov_sorted["cv_pct"], colorscale="OrRd", showscale=False
        ),
        hovertemplate="%{y}<br>CV: %{x:.2f}%<extra></extra>",
    )
)
fig2.update_layout(
    height=560, plot_bgcolor="white",
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis=dict(title="Koefisien variasi (%) — makin besar makin fluktuatif",
               gridcolor="#eeece7", ticksuffix="%"),
)
# Garis batas: rata-rata CV seluruh provinsi, agar mudah melihat provinsi
# mana yang volatilitasnya di atas/di bawah rata-rata nasional.
cv_rata_rata = prov["cv_pct"].mean()
ui.add_ref_vline(fig2, cv_rata_rata, f"Rata-rata CV: {cv_rata_rata:.1f}%", position="bottom")
st.plotly_chart(fig2, **ui.STRETCH)

# ------------------------------------ Alert kebijakan: batas rata-rata CV
# Garis rata-rata CV di atas diperlakukan sebagai batas maksimal wajar.
# Provinsi dengan CV di atasnya ditandai sebagai kandidat yang perlu
# perhatian kebijakan stabilisasi harga.
breach_cv = prov[prov["cv_pct"] > cv_rata_rata].sort_values("cv_pct", ascending=False)
ui.policy_alert(
    breached=not breach_cv.empty,
    label="Rata-rata CV nasional sebagai batas maksimal wajar",
    breach_detail=(
        f"{len(breach_cv)} dari {len(prov)} provinsi memiliki volatilitas (CV) "
        f"di atas batas rata-rata nasional ({cv_rata_rata:.1f}%), terutama: "
        f"{', '.join(breach_cv['provinsi'].head(5))}."
    ),
    ok_detail=(
        f"Seluruh provinsi memiliki volatilitas (CV) pada atau di bawah batas "
        f"rata-rata nasional ({cv_rata_rata:.1f}%)."
    ),
)

st.divider()

# ---------------------------------------------------- Statistik ringkas
st.subheader("Ringkasan statistik per provinsi")

tahun_opsi = ["Semua tahun"] + sorted(daily["tahun"].unique().tolist())
tahun = st.selectbox("Tahun", tahun_opsi)

sub = df[df["level"] == level]
if tahun != "Semua tahun":
    sub = sub[sub["tanggal"].dt.year == tahun]

tabel = D.province_summary(sub, level)
tampil = tabel.rename(
    columns={
        "provinsi": "Provinsi",
        "rata_rata": "Rata-rata",
        "median": "Median",
        "minimum": "Minimum",
        "maksimum": "Maksimum",
        "std_dev": "Std. deviasi",
        "cv_pct": "CV (%)",
        "rentang": "Rentang",
    }
)
st.dataframe(
    tampil.round(1),
    **ui.STRETCH,
    hide_index=True,
    column_config={
        "Rata-rata": st.column_config.NumberColumn(format="Rp%d"),
        "Median": st.column_config.NumberColumn(format="Rp%d"),
        "Minimum": st.column_config.NumberColumn(format="Rp%d"),
        "Maksimum": st.column_config.NumberColumn(format="Rp%d"),
        "CV (%)": st.column_config.ProgressColumn(
            format="%.2f%%", min_value=0.0,
            max_value=float(tampil["CV (%)"].max() or 1),
        ),
    },
)
ui.download_button(tampil, f"statistik_{f['komoditas'].lower()}_{tahun}.csv")
