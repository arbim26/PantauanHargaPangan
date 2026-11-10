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
df_full = f["df_full"]   # seluruh data komoditas sebelum filter provinsi/tanggal
komoditas = f["komoditas"]

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

# ---------------------------------------------------------------------------
# Moving Average & garis HET — mengambil HET dari konfigurasi zona di
# Data Explorer (session_state["het_zona_config"]).
# ---------------------------------------------------------------------------
st.subheader("Moving average & garis patokan (HET per Zona)")

# ── Helper warna zona ──────────────────────────────────────────────────────
ZONA_COLORS_LOCAL = {
    "Zona 1 — Jawa & Bali":                    "#2A6FB5",
    "Zona 2 — Sumatera":                       "#2E7D5B",
    "Zona 3 — Kalimantan":                     "#E07A28",
    "Zona 4 — Sulawesi":                       "#8B44AC",
    "Zona 5 — Nusa Tenggara, Maluku & Papua":  "#C0392B",
}

def _get_het_zona(zona_data: dict, kom: str) -> int:
    het = zona_data.get("het", {})
    if isinstance(het, dict):
        return int(het.get(kom, 0))
    return int(het) if het else 0  # backward compat format lama


# ── Ambil konfigurasi zona dari session_state ──────────────────────────────
zona_config: dict = st.session_state.get("het_zona_config", {})
ada_zona_config = bool(zona_config)

# ── Tentukan zona yang RELEVAN berdasarkan provinsi yang dipilih di sidebar ─
provinsi_dipilih: set = set(f["provinsi"])
pilih_semua_provinsi: bool = bool(st.session_state.get("all_prov", True))

def _zona_relevan(zona_config: dict, provinsi_dipilih: set) -> dict:
    """
    Kembalikan subset zona_config yang memiliki ≥1 provinsi
    beririsan dengan provinsi_dipilih.
    Jika pilih_semua_provinsi=True, semua zona dikembalikan apa adanya.
    """
    if pilih_semua_provinsi:
        return zona_config
    return {
        zn: zd for zn, zd in zona_config.items()
        if provinsi_dipilih & set(zd.get("provinsi", []))
    }

zona_config_relevan = _zona_relevan(zona_config, provinsi_dipilih)

col_het1, col_het2 = st.columns([1, 3])
with col_het1:
    het_level = st.selectbox(
        "Level pasar", D.LEVEL_ORDER, index=1, key="het_level"
    )

    if not pilih_semua_provinsi:
        # Tampilkan info zona mana yang aktif berdasarkan filter provinsi
        zona_nama_relevan = list(zona_config_relevan.keys())
        if zona_nama_relevan:
            st.info(
                f"📍 Provinsi terpilih termasuk dalam **{len(zona_nama_relevan)} zona**: "
                + ", ".join(z.split("—")[0].strip() for z in zona_nama_relevan)
                + ". HET zona lain disembunyikan."
            )
        else:
            st.warning("Tidak ada zona yang cocok dengan provinsi yang dipilih.")

    if ada_zona_config:
        zona_dengan_het = {
            zn: zd for zn, zd in zona_config_relevan.items()
            if _get_het_zona(zd, komoditas) > 0
        }
        if zona_dengan_het:
            st.success(
                f"✅ Menggunakan HET dari **{len(zona_dengan_het)} zona** "
                f"untuk **{komoditas}**."
            )
        else:
            st.info(
                f"Belum ada HET zona untuk **{komoditas}**. "
                "Atur di **Data Explorer → HET per Zona & Komoditas**."
            )
    else:
        st.info(
            "Konfigurasi zona belum ada. Atur HET di "
            "**Data Explorer → HET per Zona & Komoditas**."
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
    daily_het["ma7"]  = daily_het["harga"].rolling(7,  min_periods=1).mean()
    daily_het["ma30"] = daily_het["harga"].rolling(30, min_periods=1).mean()

    fig_het = go.Figure()

    # Harga harian aktual (abu-abu tipis)
    fig_het.add_trace(go.Scatter(
        x=daily_het["tanggal"], y=daily_het["harga"], name="Harga harian",
        mode="lines", line=dict(color="#d8d4cb", width=1),
        hovertemplate="%{x|%d %b %Y}<br>Rp%{y:,.0f}<extra>Harian</extra>",
    ))
    fig_het.add_trace(go.Scatter(
        x=daily_het["tanggal"], y=daily_het["ma7"], name="MA 7 hari",
        mode="lines", line=dict(color=D.LEVEL_COLORS[het_level], width=2.2),
        hovertemplate="%{x|%d %b %Y}<br>MA7: Rp%{y:,.0f}<extra></extra>",
    ))
    fig_het.add_trace(go.Scatter(
        x=daily_het["tanggal"], y=daily_het["ma30"], name="MA 30 hari",
        mode="lines", line=dict(color="#2A6FB5", width=2.2, dash="dot"),
        hovertemplate="%{x|%d %b %Y}<br>MA30: Rp%{y:,.0f}<extra></extra>",
    ))

    # ── Garis HET per zona ─────────────────────────────────────────────────
    # Hanya zona yang memiliki ≥1 provinsi dari filter sidebar yang ditampilkan.
    total_breach_zona: dict[str, int] = {}
    if ada_zona_config:
        for zona_nama, zona_data in zona_config_relevan.items():
            het_val = _get_het_zona(zona_data, komoditas)
            if het_val <= 0:
                continue

            prov_zona = zona_data.get("provinsi", [])
            color = ZONA_COLORS_LOCAL.get(zona_nama, "#6b7280")

            # Hitung breach berdasarkan rata-rata nasional harian untuk level ini
            breach_days = int((daily_het["harga"] > het_val).sum())
            total_breach_zona[zona_nama] = breach_days

            if breach_days > 0:
                breach_df = daily_het[daily_het["harga"] > het_val]
                fig_het.add_trace(go.Scatter(
                    x=breach_df["tanggal"],
                    y=breach_df["harga"],
                    mode="markers",
                    marker=dict(color=color, size=5, symbol="x"),
                    name=f"Breach {zona_nama.split('—')[0].strip()}",
                    showlegend=False,
                    hovertemplate=(
                        f"⚠️ Melewati HET {zona_nama.split('—')[0].strip()}<br>"
                        f"%{{x|%d %b %Y}}<br>Rp%{{y:,.0f}}<extra></extra>"
                    ),
                ))
                fig_het.add_hrect(
                    y0=het_val,
                    y1=max(daily_het["harga"].max(), het_val),
                    fillcolor=f"rgba(192,57,43,0.04)",
                    line_width=0,
                )

            fig_het.add_hline(
                y=het_val,
                line_dash="dash",
                line_color=color,
                line_width=1.6,
                annotation_text=(
                    f"HET {zona_nama.split('—')[0].strip()} "
                    f"({komoditas}): {D.format_rupiah(het_val)}"
                ),
                annotation_position="top left",
                annotation_font_color=color,
                annotation_font_size=10,
            )

    fig_het.update_layout(
        height=460, hovermode="x unified", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title="Harga (Rp/kg)", gridcolor="#eeece7"),
        xaxis=dict(gridcolor="#f5f4f1"),
    )
    with col_het2:
        st.plotly_chart(fig_het, **ui.STRETCH)

    # ── Banner status per zona ─────────────────────────────────────────────
    if total_breach_zona:
        harga_terkini = float(daily_het["harga"].iloc[-1])
        total_hari = len(daily_het)
        for zona_nama, breach_days in total_breach_zona.items():
            het_val = _get_het_zona(zona_config_relevan[zona_nama], komoditas)
            pct = breach_days / total_hari * 100 if total_hari else 0
            if harga_terkini > het_val:
                selisih = harga_terkini - het_val
                st.error(
                    f"⚠️ **{zona_nama}** — Harga {het_level.lower()} terkini nasional "
                    f"({D.format_rupiah(harga_terkini)}) **melebihi HET** "
                    f"({D.format_rupiah(het_val)}) sebesar {D.format_rupiah(selisih)} "
                    f"({selisih / het_val * 100:.1f}%). "
                    f"Sepanjang periode: di atas HET **{breach_days} dari {total_hari} hari "
                    f"({pct:.1f}%)**."
                )
            else:
                st.success(
                    f"✅ **{zona_nama}** — Harga {het_level.lower()} terkini nasional "
                    f"({D.format_rupiah(harga_terkini)}) masih **di bawah HET** "
                    f"({D.format_rupiah(het_val)}). "
                    f"Sempat melewati HET {breach_days} dari {total_hari} hari ({pct:.1f}%)."
                )

    if not ada_zona_config:
        st.caption(
            "💡 Atur HET di **Data Explorer → HET per Zona & Komoditas** "
            "agar garis patokan muncul otomatis di sini untuk setiap komoditas."
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
        fig2.add_trace(go.Scatter(
            x=s["tanggal"], y=s["harga"], name=p, mode="lines",
            line=dict(width=2),
            hovertemplate=f"<b>{p}</b><br>%{{x|%b %Y}}<br>Rp%{{y:,.0f}}<extra></extra>",
        ))
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

fig3 = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns,
    y=pivot.index.astype(str),
    colorscale="YlOrRd",
    hovertemplate="%{y} %{x}<br>Rp%{z:,.0f}<extra></extra>",
    colorbar=dict(title="Rp/kg"),
))
fig3.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig3, **ui.STRETCH)

ui.insight(
    "Heatmap ini membantu mengidentifikasi bulan-bulan dengan tekanan harga "
    "tertinggi. Pada komoditas pangan pokok, lonjakan biasanya terjadi menjelang "
    "hari besar keagamaan dan pada masa paceklik sebelum panen raya."
)