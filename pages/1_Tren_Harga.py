"""Halaman 1 — Analisis tren harga lintas waktu dan lintas provinsi."""

import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Tren harga",
    "Pergerakan harga menurut level pasar, dengan opsi moving average dan "
    "perbandingan antarprovinsi.",
)

f = ui.sidebar_filters()
df = f["df"]

if df.empty:
    st.warning("Tidak ada data pada filter yang dipilih.")
    st.stop()

c1, c2 = st.columns([3, 1])
with c2:
    ma_window = st.slider("Moving average (periode)", 1, 12, 1, key="ma")
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
    y = sub["harga"].rolling(ma_window, min_periods=1).mean() if ma_window > 1 else sub["harga"]
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

# ------------------------------------- Moving Average & garis patokan (HET)
# Bagian ini SELALU memakai data HARIAN (bukan hasil agregasi "freq" di
# sidebar), supaya Moving Average 7 & 30 hari akurat secara kalender —
# terlepas dari agregasi Mingguan/Bulanan/Kuartalan yang dipilih pengguna.
st.subheader("Moving average & garis patokan (HET)")

col_het1, col_het2 = st.columns([1, 3])
with col_het1:
    het_level = st.selectbox(
        "Level pasar", D.LEVEL_ORDER, index=1, key="het_level"
    )
    het_value = st.number_input(
        "Harga Eceran Tertinggi / HET (Rp per kg)",
        min_value=0,
        value=0,
        step=500,
        key="het_value",
        help="Masukkan 0 untuk menyembunyikan garis patokan.",
    )
    st.caption(
        "Garis merah putus-putus = HET. Titik merah = hari-hari ketika "
        "harga aktual melewati HET."
    )

daily_het = D.national_series(df, "D")
daily_het = (
    daily_het[daily_het["level"] == het_level]
    .sort_values("tanggal")
    .reset_index(drop=True)
)

if daily_het.empty:
    with col_het2:
        st.info(f"Tidak ada data harian untuk level {het_level} pada filter saat ini.")
else:
    # Moving Average 7 hari & 30 hari (bukan berbasis periode, tapi hari kalender asli)
    daily_het["ma7"] = daily_het["harga"].rolling(7, min_periods=1).mean()
    daily_het["ma30"] = daily_het["harga"].rolling(30, min_periods=1).mean()

    fig_het = go.Figure()

    # Harga harian aktual sebagai konteks (garis tipis abu-abu)
    fig_het.add_trace(
        go.Scatter(
            x=daily_het["tanggal"], y=daily_het["harga"], name="Harga harian",
            mode="lines", line=dict(color="#d8d4cb", width=1),
            hovertemplate="%{x|%d %b %Y}<br>Rp%{y:,.0f}<extra>Harian</extra>",
        )
    )
    fig_het.add_trace(
        go.Scatter(
            x=daily_het["tanggal"], y=daily_het["ma7"], name="MA 7 hari",
            mode="lines", line=dict(color=D.LEVEL_COLORS[het_level], width=2.2),
            hovertemplate="%{x|%d %b %Y}<br>MA7: Rp%{y:,.0f}<extra></extra>",
        )
    )
    fig_het.add_trace(
        go.Scatter(
            x=daily_het["tanggal"], y=daily_het["ma30"], name="MA 30 hari",
            mode="lines", line=dict(color="#2A6FB5", width=2.2, dash="dot"),
            hovertemplate="%{x|%d %b %Y}<br>MA30: Rp%{y:,.0f}<extra></extra>",
        )
    )

    # breach = hari-hari ketika harga aktual > HET (dipakai juga untuk indikator teks di bawah)
    breach = daily_het.iloc[0:0]
    if het_value and het_value > 0:
        breach = daily_het[daily_het["harga"] > het_value]
        if not breach.empty:
            # Tandai titik-titik yang melewati HET dengan marker merah
            fig_het.add_trace(
                go.Scatter(
                    x=breach["tanggal"], y=breach["harga"], name="Di atas HET",
                    mode="markers", marker=dict(color="#c0392b", size=6),
                    hovertemplate="%{x|%d %b %Y}<br>Rp%{y:,.0f} — di atas HET<extra></extra>",
                )
            )
            # Arsir tipis area di atas HET sebagai indikator visual tambahan
            fig_het.add_hrect(
                y0=het_value,
                y1=max(daily_het["harga"].max(), het_value),
                fillcolor="rgba(192,57,43,0.06)", line_width=0,
            )

        # Garis patokan HET: horizontal, putus-putus, merah
        fig_het.add_hline(
            y=het_value, line_dash="dash", line_color="#c0392b", line_width=1.6,
            annotation_text=f"HET: {D.format_rupiah(het_value)}",
            annotation_position="top left",
        )

    fig_het.update_layout(
        height=440, hovermode="x unified", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
        xaxis=dict(gridcolor="#f5f4f1"),
    )
    with col_het2:
        st.plotly_chart(fig_het, **ui.STRETCH)

    # Indikator status HET dalam bentuk banner teks (merah jika melanggar hari ini)
    if het_value and het_value > 0:
        harga_terkini = float(daily_het["harga"].iloc[-1])
        pct_breach = len(breach) / len(daily_het) * 100 if len(daily_het) else 0.0
        if harga_terkini > het_value:
            selisih = harga_terkini - het_value
            st.error(
                f"⚠️ Harga **{het_level.lower()}** terkini "
                f"({D.format_rupiah(harga_terkini)}) **melebihi HET** "
                f"({D.format_rupiah(het_value)}) sebesar "
                f"{D.format_rupiah(selisih)} ({selisih / het_value * 100:.1f}%). "
                f"Sepanjang periode terpilih, harga berada di atas HET pada "
                f"**{len(breach)} dari {len(daily_het)} hari ({pct_breach:.1f}%)**."
            )
        else:
            st.success(
                f"✅ Harga **{het_level.lower()}** terkini "
                f"({D.format_rupiah(harga_terkini)}) masih **di bawah HET** "
                f"({D.format_rupiah(het_value)}). Sepanjang periode terpilih, harga "
                f"sempat melewati HET pada {len(breach)} dari {len(daily_het)} hari "
                f"({pct_breach:.1f}%)."
            )

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
