# Dashboard Harga Komoditas Pangan Indonesia (2022–2026)

Dashboard Business Intelligence berbasis Streamlit untuk menganalisis harga
10 komoditas pangan pokok di tiga level rantai pasok (produsen, pasar
tradisional, pasar modern) pada 34 provinsi.

## Struktur proyek

```
dashboard_pangan/
├── app.py                        Halaman utama — ringkasan eksekutif
├── core/
│   ├── data.py                   Pemuatan data, cache, transformasi analitik
│   └── ui.py                     Tema, CSS, sidebar filter, kartu KPI
├── pages/
│   ├── 1_Tren_Harga.py           Tren, moving average, pola musiman
│   ├── 2_Margin_Rantai_Pasok.py  Margin produsen → pasar, markup persentase
│   ├── 3_Volatilitas.py          Boxplot kuartal, CV per provinsi
│   ├── 4_Antarprovinsi.py        Heatmap, disparitas, perbandingan 2 provinsi
│   └── 5_Data_Explorer.py        Data mentah, kualitas data, outlier IQR
├── data/
│   └── data_komoditas_pangan/    Dataset CSV (dari Kaggle)
├── .streamlit/config.toml        Tema warna aplikasi
└── requirements.txt
```

## Cara menjalankan

```bash
# 1. Buat virtual environment (opsional tapi disarankan)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Pastikan dataset ada di folder data/
#    Struktur yang diharapkan:
#    data/data_komoditas_pangan/produsen/Cleaned_After_Imputation/*.csv
#    data/data_komoditas_pangan/pasar_tradisional/Cleaned_After_Imputation/*.csv
#    data/data_komoditas_pangan/pasar_modern/Cleaned_After_Imputation/*.csv

# 4. Jalankan
streamlit run app.py
```

Aplikasi terbuka otomatis di `http://localhost:8501`.

## Catatan desain

**Arsitektur.** Logika data (`core/data.py`) dipisah dari logika tampilan
(`core/ui.py`) dan dari tiap halaman. Menambah komoditas baru cukup dengan
menaruh CSV di folder yang sesuai — katalog dibaca otomatis lewat pola nama
berkas, tanpa mengubah kode.

**Format data.** CSV aslinya berbentuk lebar (satu kolom per provinsi).
Aplikasi mengubahnya ke format panjang `tanggal | provinsi | level | harga`
agar mudah difilter, dikelompokkan, dan digabung lintas level pasar.

**Performa.** `discover_files()` dan `load_commodity()` dibungkus
`@st.cache_data`, sehingga pergantian filter tidak memicu pembacaan ulang CSV.

**Prinsip UI.**
- Satu sumber filter di sidebar, konsisten di semua halaman.
- Setiap halaman menjawab satu pertanyaan analitik, tidak dicampur.
- KPI di atas, grafik utama di tengah, detail dan tabel di bawah.
- Kotak insight berwarna menerjemahkan grafik ke kalimat — berguna saat
  presentasi, karena penguji tidak perlu menebak maksud visualisasinya.

## Peta analisis ke halaman

| Pertanyaan bisnis | Halaman | Visualisasi |
|---|---|---|
| Bagaimana tren harga secara nasional? | Ringkasan, Tren harga | Line chart 3 level |
| Kapan harga paling tertekan? | Tren harga | Heatmap tahun × bulan |
| Seberapa besar marjin perantara? | Margin rantai pasok | Bar chart kuartal, markup % |
| Seberapa fluktuatif harganya? | Volatilitas | Boxplot, ranking CV |
| Wilayah mana yang paling mahal? | Antarprovinsi | Heatmap provinsi × kuartal |
| Apakah pasar antarwilayah terintegrasi? | Antarprovinsi | Korelasi dua provinsi |
| Apakah datanya bersih? | Data explorer | Cakupan, deteksi outlier IQR |

## Kemungkinan pengembangan

- Peta choropleth Indonesia (butuh berkas GeoJSON batas provinsi).
- Forecasting sederhana dengan Prophet atau SARIMA pada halaman tren.
- Deteksi anomali harga otomatis dengan ambang batas z-score.
- Ekspor laporan ke PDF untuk kebutuhan presentasi.
