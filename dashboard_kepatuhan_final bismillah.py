
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# =======================#
# Fungsi bantu
# =======================#
def normalize_col(col):
    col = col.strip().lower()
    aliases = {
        "upppd": ["upppd", "unit", "nm unit"],
        "klasifikasi": ["kategori", "jenis", "jenis hiburan", "klasifikasi hiburan"],
        "tmt": ["tmt"],
        "status": ["status"],
    }
    for key, values in aliases.items():
        if col in values:
            return key
    return col

def extract_bulan_cols(df):
    bulan_cols = []
    for col in df.columns:
        col_clean = col.strip().lower()
        if any(b in col_clean for b in ["jan", "feb", "mar", "apr", "mei", "may", "jun", "jul", "agu", "aug", "sep", "okt", "oct", "nov", "des", "dec"]):
            bulan_cols.append(col)
        else:
            try:
                dt = pd.to_datetime(col_clean, errors="coerce", dayfirst=True)
                if not pd.isna(dt) and 1 <= dt.month <= 12:
                    bulan_cols.append(col)
            except:
                pass
    return bulan_cols

def hitung_bulan_aktif(tmt, tahun_pajak):
    if pd.isna(tmt):
        return 0
    try:
        tmt = pd.to_datetime(tmt)
        if tmt.year < tahun_pajak:
            return 12
        elif tmt.year == tahun_pajak:
            return max(13 - tmt.month, 0)
        else:
            return 0
    except:
        return 0

def klasifikasi_kepatuhan(aktif, bayar):
    selisih = aktif - bayar
    if aktif == 0:
        return "Tidak Aktif"
    elif selisih <= 0:
        return "Patuh"
    elif 1 <= selisih <= 3:
        return "Kurang Patuh"
    else:
        return "Tidak Patuh"

# =======================#
# Halaman Utama Streamlit
# =======================#
st.title("📊 Dashboard Kepatuhan Pajak")

st.markdown("Silakan upload file Excel berisi data setoran masa pajak.")

with st.expander("📄 Panduan Format"):
    st.markdown("""
    - Kolom **TMT**, **STATUS**, dan **nama unit** (`UPPPD`, `unit`, `nm unit`) wajib ada.
    - Kolom klasifikasi (`kategori`, `jenis`, dll) hanya wajib untuk pajak **HIBURAN**.
    - Kolom pembayaran bisa berformat:
        - Nama bulan: `JAN`, `FEB`, dll.
        - Tanggal: `1/1/2024`, `Jan 24`, `01-2024`, dll.
    - Kolom seperti `TOTAL 2024` akan otomatis diabaikan.
    """)

uploaded_file = st.file_uploader("Upload file Excel", type=["xlsx"])
if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheet = st.selectbox("Pilih sheet", xl.sheet_names)
    df = xl.parse(sheet)

    df.columns = [normalize_col(str(c)) for c in df.columns]
    jenis_pajak = st.selectbox("Pilih jenis pajak", ["MAKAN MINUM", "HIBURAN"])
    tahun_pajak = st.number_input("Pilih Tahun Pajak", min_value=2000, max_value=2100, value=2024)

    bulan_cols = extract_bulan_cols(df)
    pembayaran_df = df[bulan_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["total_pembayaran"] = pembayaran_df.sum(axis=1)
    df["bulan_pembayaran"] = pembayaran_df.gt(0).sum(axis=1)
    df["bulan_aktif"] = df["tmt"].apply(lambda x: hitung_bulan_aktif(x, tahun_pajak))
    df["kepatuhan_%"] = (df["bulan_pembayaran"] / df["bulan_aktif"].replace(0, np.nan)) * 100
    df["kepatuhan_%"] = df["kepatuhan_%"].fillna(0)
    df["tingkat_kepatuhan"] = df.apply(lambda row: klasifikasi_kepatuhan(row["bulan_aktif"], row["bulan_pembayaran"]), axis=1)
    df["rata_rata_per_bulan"] = df.apply(lambda row: row["total_pembayaran"]/row["bulan_pembayaran"] if row["bulan_pembayaran"] > 0 else 0, axis=1)

    # Filter
    unit_options = df["upppd"].dropna().unique()
    unit = st.multiselect("Pilih Unit", unit_options, default=unit_options)

    if jenis_pajak == "HIBURAN":
        klasifikasi_col = "klasifikasi"
        klasifikasi_options = df[klasifikasi_col].dropna().unique() if klasifikasi_col in df.columns else []
        klasifikasi = st.multiselect("Pilih Klasifikasi", klasifikasi_options, default=klasifikasi_options)
    else:
        klasifikasi = None

    status_options = df["status"].dropna().unique()
    status = st.multiselect("Pilih STATUS", status_options, default=status_options)

    filtered_df = df[
        df["upppd"].isin(unit) &
        df["status"].isin(status)
    ]

    if jenis_pajak == "HIBURAN" and klasifikasi:
        filtered_df = filtered_df[filtered_df["klasifikasi"].isin(klasifikasi)]

    st.markdown("### 📈 Visualisasi Data")
    st.bar_chart(filtered_df.groupby("tingkat_kepatuhan").size())

    pembayaran_bulanan = pembayaran_df.loc[filtered_df.index]
    st.line_chart(pembayaran_bulanan.sum())

    top5 = filtered_df.nlargest(5, "total_pembayaran")[["upppd", "total_pembayaran"]]
    st.table(top5.rename(columns={"upppd": "Unit", "total_pembayaran": "Total Pembayaran"}))

    st.markdown("### 🧾 Data Ringkasan")
    st.dataframe(filtered_df[[
        "upppd", "status", "tmt", "total_pembayaran", "bulan_aktif", "bulan_pembayaran",
        "kepatuhan_%", "tingkat_kepatuhan", "rata_rata_per_bulan"
    ]])

