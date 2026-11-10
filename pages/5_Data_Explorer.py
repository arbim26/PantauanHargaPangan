"""Halaman 5 — Penjelajah data mentah, kualitas data, dan HET per Zona & Komoditas."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import ui

ui.setup_page(
    "Data Explorer",
    "Telusuri data mentah, periksa kualitasnya, kelola HET per zona & komoditas, "
    "dan unduh subset sesuai filter.",
)

f = ui.sidebar_filters()
df = f["df"]
full = f["df_full"]
komoditas_aktif = f["komoditas"]

# ---------------------------------------------------------------------------
# Definisi zona HET default (berdasarkan pembagian wilayah Indonesia)
# ---------------------------------------------------------------------------
ZONA_DEFAULT: dict[str, list[str]] = {
    "Zona 1 — Jawa & Bali": [
        "Banten", "DKI Jakarta", "Jawa Barat", "Jawa Tengah",
        "DI Yogyakarta", "Jawa Timur", "Bali",
    ],
    "Zona 2 — Sumatera": [
        "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau",
        "Kepulauan Riau", "Jambi", "Bengkulu", "Sumatera Selatan",
        "Kepulauan Bangka Belitung", "Lampung",
    ],
    "Zona 3 — Kalimantan": [
        "Kalimantan Barat", "Kalimantan Tengah", "Kalimantan Selatan",
        "Kalimantan Timur", "Kalimantan Utara",
    ],
    "Zona 4 — Sulawesi": [
        "Sulawesi Utara", "Gorontalo", "Sulawesi Tengah",
        "Sulawesi Barat", "Sulawesi Selatan", "Sulawesi Tenggara",
    ],
    "Zona 5 — Nusa Tenggara, Maluku & Papua": [
        "Nusa Tenggara Barat", "Nusa Tenggara Timur",
        "Maluku", "Maluku Utara",
        "Papua Barat", "Papua",
    ],
}

ZONA_COLORS = {
    "Zona 1 — Jawa & Bali":                    "#2A6FB5",
    "Zona 2 — Sumatera":                       "#2E7D5B",
    "Zona 3 — Kalimantan":                     "#E07A28",
    "Zona 4 — Sulawesi":                       "#8B44AC",
    "Zona 5 — Nusa Tenggara, Maluku & Papua":  "#C0392B",
}

# ---------------------------------------------------------------------------
# Session state: simpan konfigurasi zona & HET per komoditas
# Struktur: { zona_nama: { "provinsi": [...], "het": { komoditas: nilai } } }
# ---------------------------------------------------------------------------
if "het_zona_config" not in st.session_state:
    st.session_state["het_zona_config"] = {
        nama: {"provinsi": list(prov), "het": {}}
        for nama, prov in ZONA_DEFAULT.items()
    }

# Migrasi dari format lama (het: int) ke format baru (het: dict)
for _zn, _zd in st.session_state["het_zona_config"].items():
    if not isinstance(_zd.get("het"), dict):
        _zd["het"] = {}

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _hex_to_rgba(hex_color: str, alpha: float = 0.12) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _get_het(zona_data: dict, komoditas: str) -> int:
    """Ambil nilai HET untuk zona+komoditas tertentu (default 0)."""
    return int(zona_data.get("het", {}).get(komoditas, 0))


def _get_all_komoditas() -> list[str]:
    catalog = D.discover_files()
    return sorted(catalog["komoditas"].unique())


# ---------------------------------------------------------------------------
# Tab utama
# ---------------------------------------------------------------------------
tab_het, tab1, tab2, tab3 = st.tabs([
    "🏷️ HET per Zona & Komoditas",
    "📋 Data terfilter",
    "🔍 Kualitas data",
    "📁 Katalog berkas",
])

# ===========================================================================
# TAB HET PER ZONA & KOMODITAS
# ===========================================================================
with tab_het:
    st.markdown(
        "Tetapkan **Harga Eceran Tertinggi (HET)** per zona wilayah **dan** per komoditas. "
        "Nilai HET yang diisi di sini akan otomatis muncul sebagai garis patokan di "
        "halaman **Tren Harga** (grafik Moving Average & HET)."
    )

    all_prov_data = sorted(full["provinsi"].unique())
    semua_komoditas = _get_all_komoditas()

    # -----------------------------------------------------------------------
    # Panel konfigurasi zona
    # -----------------------------------------------------------------------
    with st.expander("⚙️ Konfigurasi Zona, Provinsi & HET", expanded=True):
        config = st.session_state["het_zona_config"]

        col_add, col_reset = st.columns([3, 1])
        with col_add:
            nama_zona_baru = st.text_input(
                "Nama zona baru",
                placeholder="misal: Zona Khusus Kepulauan",
                key="new_zona_name",
            )
        with col_reset:
            st.write("")
            st.write("")
            if st.button("🔄 Reset ke default", use_container_width=True):
                st.session_state["het_zona_config"] = {
                    nama: {"provinsi": list(prov), "het": {}}
                    for nama, prov in ZONA_DEFAULT.items()
                }
                st.rerun()

        if nama_zona_baru and st.button("➕ Tambah zona baru", key="btn_add_zona"):
            if nama_zona_baru not in st.session_state["het_zona_config"]:
                st.session_state["het_zona_config"][nama_zona_baru] = {
                    "provinsi": [], "het": {}
                }
                st.rerun()
            else:
                st.warning("Nama zona sudah ada.")

        st.divider()

        zona_to_delete = None
        for zona_nama in list(st.session_state["het_zona_config"].keys()):
            zona_data = st.session_state["het_zona_config"][zona_nama]
            color = ZONA_COLORS.get(zona_nama, "#6b7280")

            with st.container():
                col_title, col_del = st.columns([5, 1])
                with col_title:
                    st.markdown(
                        f'<span style="display:inline-block;width:12px;height:12px;'
                        f'border-radius:50%;background:{color};margin-right:8px;'
                        f'vertical-align:middle;"></span>'
                        f'<strong>{zona_nama}</strong>',
                        unsafe_allow_html=True,
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_{zona_nama}", help=f"Hapus {zona_nama}"):
                        zona_to_delete = zona_nama

                # Provinsi anggota zona
                prov_zona = st.multiselect(
                    "Provinsi dalam zona",
                    all_prov_data,
                    default=[p for p in zona_data["provinsi"] if p in all_prov_data],
                    key=f"prov_{zona_nama}",
                )
                st.session_state["het_zona_config"][zona_nama]["provinsi"] = prov_zona

                # HET per komoditas: tampilkan sebagai grid kolom
                st.caption("🏷️ HET per komoditas (Rp/kg) — isi 0 untuk menyembunyikan garis")
                het_dict = zona_data.get("het", {})
                n_cols = 4
                kom_cols = [semua_komoditas[i:i+n_cols] for i in range(0, len(semua_komoditas), n_cols)]
                for row_kom in kom_cols:
                    cols_k = st.columns(n_cols)
                    for ci, kom in enumerate(row_kom):
                        with cols_k[ci]:
                            val = st.number_input(
                                kom,
                                min_value=0,
                                value=int(het_dict.get(kom, 0)),
                                step=500,
                                key=f"het_{zona_nama}__{kom}",
                            )
                            st.session_state["het_zona_config"][zona_nama]["het"][kom] = val

                st.markdown("---")

        if zona_to_delete:
            del st.session_state["het_zona_config"][zona_to_delete]
            st.rerun()

    # -----------------------------------------------------------------------
    # Tentukan zona yang RELEVAN berdasarkan provinsi yang dipilih di sidebar
    # -----------------------------------------------------------------------
    config = st.session_state["het_zona_config"]

    provinsi_dipilih: set = set(f["provinsi"])
    # Gunakan checkbox session_state "all_prov" sebagai sumber kebenaran,
    # bukan perbandingan set (yang bisa gagal jika data tidak lengkap di
    # rentang tanggal tertentu).
    pilih_semua_provinsi: bool = bool(st.session_state.get("all_prov", True))

    def _zona_relevan(cfg: dict, prov_terpilih: set, semua: bool) -> list[str]:
        """
        Kembalikan nama-nama zona yang memiliki ≥1 provinsi beririsan
        dengan prov_terpilih. Jika semua=True, kembalikan semua zona.
        """
        if semua:
            return list(cfg.keys())
        return [
            zn for zn, zd in cfg.items()
            if prov_terpilih & set(zd.get("provinsi", []))
        ]

    zona_relevan_list = _zona_relevan(config, provinsi_dipilih, pilih_semua_provinsi)

    if not pilih_semua_provinsi:
        if zona_relevan_list:
            st.info(
                f"📍 Provinsi yang dipilih di sidebar termasuk dalam "
                f"**{len(zona_relevan_list)} zona**: "
                + ", ".join(z.split("—")[0].strip() for z in zona_relevan_list)
                + ". Zona lain disembunyikan dari grafik."
            )
        else:
            st.warning(
                "Tidak ada zona yang cocok dengan provinsi yang dipilih di sidebar. "
                "Pilih provinsi lain atau aktifkan 'Semua provinsi'."
            )

    # -----------------------------------------------------------------------
    # Kontrol grafik
    # -----------------------------------------------------------------------
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns(4)
    with col_ctrl1:
        het_level = st.selectbox(
            "Level pasar",
            D.LEVEL_ORDER,
            index=1,
            key="het_zona_level",
        )
    with col_ctrl2:
        # Komoditas untuk grafik — default ke pilihan sidebar
        komoditas_grafik = st.selectbox(
            "Komoditas (grafik)",
            semua_komoditas,
            index=semua_komoditas.index(komoditas_aktif) if komoditas_aktif in semua_komoditas else 0,
            key="het_kom_grafik",
        )
    with col_ctrl3:
        ma_window_het = st.slider(
            "Moving average (hari)",
            1, 30, 7,
            key="ma_het_zona",
        )
    with col_ctrl4:
        zona_aktif = st.multiselect(
            "Tampilkan zona",
            list(config.keys()),
            default=zona_relevan_list,   # ← otomatis sesuai provinsi terpilih
            key="zona_aktif",
        )

    # -----------------------------------------------------------------------
    # Muat data komoditas yang dipilih untuk grafik
    # -----------------------------------------------------------------------
    df_grafik_full = D.load_commodity(komoditas_grafik)

    # Terapkan filter tanggal dari sidebar
    date_range = f["date_range"]
    if date_range and len(date_range) == 2 and all(date_range):
        start_ts = pd.Timestamp(date_range[0])
        end_ts   = pd.Timestamp(date_range[1])
        df_grafik = df_grafik_full[
            (df_grafik_full["tanggal"] >= start_ts) &
            (df_grafik_full["tanggal"] <= end_ts)
        ]
    else:
        df_grafik = df_grafik_full.copy()

    sub_level = df_grafik[df_grafik["level"] == het_level].copy()

    # -----------------------------------------------------------------------
    # Grafik tren harga per zona dengan garis HET
    # -----------------------------------------------------------------------
    st.subheader(f"Tren Harga per Zona · {komoditas_grafik} · Level {het_level}")

    fig_zona = go.Figure()
    has_any_data = False

    for zona_nama in zona_aktif:
        zona_data = config[zona_nama]
        prov_zona = [p for p in zona_data["provinsi"] if p in df_grafik_full["provinsi"].unique()]
        if not prov_zona:
            continue

        color = ZONA_COLORS.get(zona_nama, "#6b7280")
        sub_zona = sub_level[sub_level["provinsi"].isin(prov_zona)]
        if sub_zona.empty:
            continue

        zona_daily = (
            sub_zona.groupby("tanggal")["harga"]
            .mean()
            .reset_index()
            .sort_values("tanggal")
        )
        zona_daily["harga_ma"] = zona_daily["harga"].rolling(ma_window_het, min_periods=1).mean()
        has_any_data = True

        # Pita rentang min–maks harga dalam zona
        zona_band = (
            sub_zona.groupby("tanggal")["harga"]
            .agg(["min", "max"])
            .reset_index()
            .sort_values("tanggal")
        )
        fig_zona.add_trace(go.Scatter(
            x=zona_band["tanggal"], y=zona_band["max"],
            mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig_zona.add_trace(go.Scatter(
            x=zona_band["tanggal"], y=zona_band["min"],
            mode="lines", fill="tonexty",
            fillcolor=_hex_to_rgba(color, 0.11),
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))

        # Garis MA zona
        fig_zona.add_trace(go.Scatter(
            x=zona_daily["tanggal"],
            y=zona_daily["harga_ma"],
            name=zona_nama,
            mode="lines",
            line=dict(color=color, width=2.4),
            hovertemplate=(
                f"<b>{zona_nama}</b><br>"
                f"%{{x|%d %b %Y}}<br>Rp%{{y:,.0f}}"
                f"<extra>MA{ma_window_het}h · {', '.join(prov_zona[:3])}"
                f"{'...' if len(prov_zona) > 3 else ''}</extra>"
            ),
        ))

        # Garis HET untuk komoditas yang dipilih
        het_val = _get_het(zona_data, komoditas_grafik)
        if het_val > 0:
            breach_zona = zona_daily[zona_daily["harga"] > het_val]
            if not breach_zona.empty:
                fig_zona.add_trace(go.Scatter(
                    x=breach_zona["tanggal"],
                    y=breach_zona["harga"],
                    mode="markers",
                    marker=dict(color=color, size=5, symbol="x"),
                    showlegend=False,
                    hovertemplate=(
                        f"⚠️ Harga melewati HET<br>"
                        f"%{{x|%d %b %Y}}<br>"
                        f"Rp%{{y:,.0f}}<extra>{zona_nama}</extra>"
                    ),
                ))
            fig_zona.add_hline(
                y=het_val,
                line_dash="dash",
                line_color=color,
                line_width=1.6,
                annotation_text=(
                    f"HET {zona_nama.split('—')[0].strip()}: {D.format_rupiah(het_val)}"
                ),
                annotation_position="top right",
                annotation_font_color=color,
                annotation_font_size=10,
            )

    if not has_any_data:
        st.info("Tidak ada data untuk zona dan filter yang dipilih.")
    else:
        fig_zona.update_layout(
            height=520,
            hovermode="x unified",
            plot_bgcolor="white",
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            yaxis=dict(title="Harga rata-rata zona (Rp/kg)", gridcolor="#eeece7"),
            xaxis=dict(gridcolor="#f5f4f1"),
            title=dict(
                text=(
                    f"Tren Harga per Zona — {komoditas_grafik} · "
                    f"{het_level} · MA{ma_window_het} hari"
                ),
                font=dict(size=13), x=0,
            ),
        )
        st.plotly_chart(fig_zona, **ui.STRETCH)

        # -----------------------------------------------------------------------
        # Kartu status HET per zona (hanya zona yang punya HET untuk komoditas ini)
        # -----------------------------------------------------------------------
        zona_dengan_het = [
            (z, config[z])
            for z in zona_aktif
            if _get_het(config[z], komoditas_grafik) > 0 and config[z].get("provinsi")
        ]

        if zona_dengan_het:
            st.subheader(f"Status HET per Zona · {komoditas_grafik} · Periode Terpilih")
            cols_status = st.columns(min(len(zona_dengan_het), 3))

            for idx, (zona_nama, zona_data) in enumerate(zona_dengan_het):
                prov_zona = [p for p in zona_data["provinsi"] if p in df_grafik_full["provinsi"].unique()]
                if not prov_zona:
                    continue

                sub_z = sub_level[sub_level["provinsi"].isin(prov_zona)]
                if sub_z.empty:
                    continue

                zona_daily_s = sub_z.groupby("tanggal")["harga"].mean().reset_index()
                het_val = _get_het(zona_data, komoditas_grafik)
                harga_terkini = float(zona_daily_s["harga"].iloc[-1])
                breach_days = int((zona_daily_s["harga"] > het_val).sum())
                total_days = len(zona_daily_s)
                pct_breach = breach_days / total_days * 100 if total_days else 0
                color = ZONA_COLORS.get(zona_nama, "#6b7280")
                kondisi = harga_terkini > het_val

                with cols_status[idx % 3]:
                    tanda = "⚠️" if kondisi else "✅"
                    warna_bg = "#fff5f5" if kondisi else "#f0fdf4"
                    warna_border = "#c0392b" if kondisi else "#1e8e5a"
                    keterangan = "DI ATAS HET" if kondisi else "di bawah HET"
                    st.markdown(
                        f"""
                        <div style="border:1.5px solid {warna_border};border-radius:10px;
                                    padding:0.9rem 1rem;background:{warna_bg};margin-bottom:0.5rem;">
                          <div style="font-size:.8rem;color:#6b7280;margin-bottom:.2rem;">
                            <span style="display:inline-block;width:10px;height:10px;
                                         border-radius:50%;background:{color};margin-right:6px;
                                         vertical-align:middle;"></span>
                            {zona_nama}
                          </div>
                          <div style="font-size:1.3rem;font-weight:650;line-height:1.3;">
                            {tanda} {D.format_rupiah(harga_terkini)}
                          </div>
                          <div style="font-size:.82rem;color:{warna_border};font-weight:600;">
                            {keterangan} · HET {D.format_rupiah(het_val)}
                          </div>
                          <div style="font-size:.78rem;color:#6b7280;margin-top:.3rem;">
                            Melewati HET: <strong>{breach_days} dari {total_days} hari
                            ({pct_breach:.1f}%)</strong>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # -----------------------------------------------------------------------
        # Tabel ringkasan semua zona untuk komoditas yang dipilih
        # -----------------------------------------------------------------------
        st.subheader(f"Ringkasan Rata-rata Harga per Zona · {komoditas_grafik}")

        rows_summary = []
        for zona_nama in zona_aktif:
            zona_data = config[zona_nama]
            prov_zona = [p for p in zona_data["provinsi"] if p in df_grafik_full["provinsi"].unique()]
            if not prov_zona:
                continue
            sub_z = sub_level[sub_level["provinsi"].isin(prov_zona)]
            if sub_z.empty:
                continue
            rata_zona = sub_z["harga"].mean()
            het_val = _get_het(zona_data, komoditas_grafik)
            status = (
                "–" if not het_val
                else ("⚠️ DI ATAS HET" if rata_zona > het_val else "✅ Normal")
            )
            rows_summary.append({
                "Zona": zona_nama,
                "Provinsi": len(prov_zona),
                "Rata-rata Harga (Rp/kg)": round(rata_zona, 0),
                "HET (Rp/kg)": het_val if het_val else "–",
                "Selisih thd HET": round(rata_zona - het_val, 0) if het_val else "–",
                "Status": status,
            })

        if rows_summary:
            st.dataframe(pd.DataFrame(rows_summary), **ui.STRETCH, hide_index=True)

        ui.insight(
            f"Garis HET per zona untuk <b>{komoditas_grafik}</b> membantu identifikasi "
            "wilayah dengan tekanan harga tertinggi. Zona dengan harga di atas HET "
            "perlu mendapat prioritas intervensi kebijakan seperti operasi pasar atau "
            "subsidi distribusi. Nilai HET ini juga tampil otomatis di halaman "
            "<b>Tren Harga</b> pada grafik Moving Average & HET."
        )

    # -----------------------------------------------------------------------
    # Tabel rekap HET semua komoditas untuk semua zona (view lintas komoditas)
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Rekap HET — Semua Komoditas × Semua Zona")
    st.caption(
        "Tabel ini merangkum seluruh nilai HET yang telah diisi. "
        "Kolom = zona, baris = komoditas."
    )
    zona_names_all = list(config.keys())
    rekap_rows = []
    for kom in semua_komoditas:
        row = {"Komoditas": kom}
        for zn in zona_names_all:
            val = _get_het(config[zn], kom)
            row[zn] = D.format_rupiah(val) if val > 0 else "–"
        rekap_rows.append(row)
    st.dataframe(pd.DataFrame(rekap_rows), **ui.STRETCH, hide_index=True)


# ===========================================================================
# TAB DATA TERFILTER
# ===========================================================================
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


# ===========================================================================
# TAB KUALITAS DATA
# ===========================================================================
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


# ===========================================================================
# TAB KATALOG BERKAS
# ===========================================================================
with tab3:
    st.subheader("Berkas sumber yang terdeteksi")
    katalog = D.discover_files()
    st.dataframe(
        katalog[["komoditas", "level", "path"]],
        **ui.STRETCH, hide_index=True,
    )
    st.caption(f"Total {len(katalog)} berkas CSV ditemukan.")