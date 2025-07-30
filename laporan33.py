import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURASI HALAMAN DAN JUDUL UTAMA ---
st.set_page_config(layout="wide", page_title="Dashboard Kepatuhan Satker")
st.title("📊 Dashboard Kepatuhan LK, LPJ, dan SHR")
st.markdown("Dasbor terpusat untuk memonitor progres dan kinerja Satuan Kerja.")

# Trik CSS untuk kustomisasi sidebar
st.markdown(
    """
    <style>
    button[data-testid="stSidebarNavViewButton"] > svg,
    button[data-testid="stSidebarNavCollapseButton"] > svg { display: none; }
    button[data-testid="stSidebarNavViewButton"]::after { content: "☰ Filter"; font-size: 16px; color: #333; font-weight: bold; padding: 5px; }
    button[data-testid="stSidebarNavCollapseButton"]::after { content: "ᐊ"; font-size: 20px; color: #333; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- FUNGSI UNTUK MEMUAT DAN MEMPROSES DATA ---
@st.cache_data(ttl=600)
def load_and_process_data(sheet_id):
    """Memuat data mentah dan data deadline, lalu memprosesnya."""
    # PERUBAHAN: Menambahkan 'DEADLINE' ke daftar sheet
    sheet_names = ["LK", "LPJ", "SHR", "DEADLINE"]
    dataframes_raw = {}
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    st.info("Memuat data terbaru dari Google Sheets...")
    for name in sheet_names:
        try:
            url = base_url + name
            dataframes_raw[name] = pd.read_csv(url, dtype=str).fillna('')
        except Exception as e:
            st.error(f"Gagal memuat sheet '{name}': {e}")
            dataframes_raw[name] = pd.DataFrame()

    # --- Bagian pemrosesan data laporan (TIDAK DIUBAH) ---
    processed_data = {}
    if "LK" in dataframes_raw:
        processed_data["LK"] = dataframes_raw["LK"].copy()
    if "SHR" in dataframes_raw:
        processed_data["SHR"] = dataframes_raw["SHR"].copy()

    df_lpj = dataframes_raw.get("LPJ", pd.DataFrame()).copy()
    if not df_lpj.empty:
        if 'Jenis LPJ dan Nama Satker' in df_lpj.columns:
            def standardize_lpj_type(lpj_type_str):
                lpj_type_str = str(lpj_type_str).upper()
                if "PENGELUARAN" in lpj_type_str: return "BENDAHARA PENGELUARAN"
                if "PEMASUKAN" in lpj_type_str: return "BENDAHARA PEMASUKAN"
                if "BADAN LAYANAN UMUM" in lpj_type_str: return "BADAN LAYANAN UMUM"
                return "TIDAK DIKETAHUI"
            df_lpj['Jenis LPJ'] = df_lpj['Jenis LPJ dan Nama Satker'].apply(standardize_lpj_type)
        else:
            st.warning("Kolom 'Jenis LPJ dan Nama Satker' tidak ditemukan di sheet LPJ.")
            df_lpj['Jenis LPJ'] = "TIDAK DIKETAHUI"
        processed_data["LPJ"] = df_lpj

    # --- PERUBAHAN: Memproses sheet DEADLINE menjadi dictionary ---
    deadlines_dict = {}
    df_deadline = dataframes_raw.get("DEADLINE")
    if df_deadline is not None and not df_deadline.empty:
        st.success("Konfigurasi deadline berhasil dimuat.")
        deadlines_dict = pd.Series(
            df_deadline['Tanggal Deadline'].values,
            index=df_deadline['Jenis Laporan']
        ).to_dict()
    else:
        st.warning("Sheet 'DEADLINE' tidak ditemukan. Pengecekan deadline tidak akan akurat.")

    # PERUBAHAN: Mengembalikan dua objek: data laporan dan dictionary deadline
    return processed_data, deadlines_dict

# --- FUNGSI UNTUK MEMBUAT TAB FILTER DATA (TIDAK DIUBAH) ---
def create_date_filter_tab(df, date_col, name_col, header_text):
    st.header(header_text)
    if df.empty or date_col not in df.columns or name_col not in df.columns:
        st.warning(f"Data atau kolom yang diperlukan tidak tersedia.")
        return
    df_copy = df.copy()
    df_copy[f'{date_col}_dt'] = pd.to_datetime(df_copy[date_col], format='%d/%m/%Y', errors='coerce')
    df_copy.dropna(subset=[f'{date_col}_dt'], inplace=True)
    if df_copy.empty:
        st.warning(f"Tidak ada data tanggal yang valid untuk difilter.")
        return
    min_date, max_date = df_copy[f'{date_col}_dt'].min().date(), df_copy[f'{date_col}_dt'].max().date()
    selected_date = st.date_input("Pilih tanggal:", value=max_date, min_value=min_date, max_value=max_date, key=f"date_filter_{date_col}")
    if selected_date:
        mask = (df_copy[f'{date_col}_dt'].dt.date == pd.to_datetime(selected_date).date())
        filtered_df = df_copy[mask]
        st.info(f"Menampilkan **{len(filtered_df)} data** pada **{selected_date.strftime('%d-%m-%Y')}**.")
        st.dataframe(filtered_df[['Kode Satker', name_col, date_col]], use_container_width=True, hide_index=True)


# --- FUNGSI UNTUK MENAMPILKAN HASIL PENCARIAN DETAIL ---
# PERUBAHAN: Menambahkan 'deadlines' sebagai parameter
def display_search_results(kode_input, all_data, selected_reports, deadlines):
    df_lk = all_data.get("LK", pd.DataFrame())
    df_lpj = all_data.get("LPJ", pd.DataFrame())
    df_shr = all_data.get("SHR", pd.DataFrame())

    lk_data = df_lk[df_lk['Kode Satker'] == kode_input]
    lpj_data = df_lpj[df_lpj['Kode Satker'] == kode_input]
    shr_data = df_shr[df_shr['Kode Satker'] == kode_input]

    if lk_data.empty and lpj_data.empty and shr_data.empty:
        st.warning(f"Kode Satker '{kode_input}' tidak ditemukan.")
        return

    nama_satker = lk_data.iloc[0]['Nama Satker'] if not lk_data.empty else (shr_data.iloc[0]['Nama Satker'] if not shr_data.empty else "Nama Satker dari LPJ")
    st.subheader(f"Detail untuk: {nama_satker}")
    st.text(f"Kode Satker: {kode_input}")
    
    # PERUBAHAN: Fungsi get_status baru yang membandingkan tanggal penuh
    def get_deadline_status(submission_date_str, deadline_date_str):
        if not submission_date_str or not isinstance(submission_date_str, str) or not deadline_date_str:
            return "-", "off"
        try:
            submission_dt = datetime.strptime(submission_date_str, '%d/%m/%Y')
            deadline_dt = datetime.strptime(deadline_date_str, '%d/%m/%Y')
            return ("✅ Tepat Waktu", "normal") if submission_dt.date() <= deadline_dt.date() else ("❌ Terlambat", "inverse")
        except (TypeError, ValueError):
            return "-", "off"

    # PERUBAHAN: Ambil tanggal deadline dari dictionary
    lk_deadline = deadlines.get('LK')
    shr_deadline = deadlines.get('SHR')
    lpj_deadline = deadlines.get('LPJ')
    
    st.caption(f"Deadline Saat Ini: LK ({lk_deadline or 'N/A'}), LPJ ({lpj_deadline or 'N/A'}), SHR ({shr_deadline or 'N/A'})")

    if "LK" in selected_reports:
        st.markdown("---")
        st.subheader("Detail Laporan Keuangan (LK)")
        lk_date = lk_data.iloc[0]['LK terupload'] if not lk_data.empty else None
        # PERUBAHAN: Panggil fungsi status yang baru dengan deadline dari dictionary
        status, delta_color = get_deadline_status(lk_date, lk_deadline)
        st.metric(label="Tanggal Upload", value=lk_date or "N/A", delta=status, delta_color=delta_color)

    if "SHR" in selected_reports:
        st.markdown("---")
        st.subheader("Detail Tutup Periode (SHR)")
        shr_date = shr_data.iloc[0]['Tanggal Tutup Periode'] if not shr_data.empty else None
        # PERUBAHAN: Panggil fungsi status yang baru dengan deadline dari dictionary
        status, delta_color = get_deadline_status(shr_date, shr_deadline)
        st.metric(label="Tanggal Tutup Periode", value=shr_date or "N/A", delta=status, delta_color=delta_color)

    if "LPJ" in selected_reports:
        st.markdown("---")
        st.subheader("Detail Status Laporan Pertanggungjawaban (LPJ)")
        if 'Jenis LPJ' not in lpj_data.columns:
            st.error("Gagal memproses kolom 'Jenis LPJ'. Periksa struktur data sheet LPJ.")
            return
        lpj_types = {"Bendahara Pemasukan": "BENDAHARA PEMASUKAN", "Bendahara Pengeluaran": "BENDAHARA PENGELUARAN", "BLU": "BLU"}
        lpj_cols = st.columns(3)
        for i, (display_name, internal_name) in enumerate(lpj_types.items()):
            with lpj_cols[i]:
                lpj_row = lpj_data[lpj_data['Jenis LPJ'] == internal_name]
                lpj_date = lpj_row.iloc[0]['Tanggal Validasi LPJ'] if not lpj_row.empty else None
                # PERUBAHAN: Panggil fungsi status yang baru dengan deadline dari dictionary
                status, delta_color = get_deadline_status(lpj_date, lpj_deadline)
                st.metric(label=display_name, value=lpj_date or "N/A", delta=status, delta_color=delta_color)

# --- EKSEKUSI UTAMA APLIKASI ---
SHEET_ID = "1WIvE_yZDfeH_lD5z6sboMfMnSL0Gy9vEQJcxvA91BVk"
# PERUBAHAN: Unpack data laporan dan dictionary deadlines
all_data, deadlines = load_and_process_data(SHEET_ID)

# --- SIDEBAR KONTROL (TIDAK DIUBAH) ---
st.sidebar.header("Filter Laporan")
report_options = {"Laporan Keuangan (LK)": "LK", "Laporan Pertanggungjawaban (LPJ)": "LPJ", "SHR": "SHR"}
selected_reports_display = st.sidebar.multiselect("Pilih laporan:", options=list(report_options.keys()), default=list(report_options.keys()))
selected_reports = [report_options[report] for report in selected_reports_display]

# --- BUAT TAB SECARA DINAMIS (TIDAK DIUBAH) ---
if selected_reports:
    tab_titles = []
    if "LK" in selected_reports: tab_titles.append("🗓️ Laporan Keuangan")
    if "LPJ" in selected_reports: tab_titles.append("🗓️ Laporan Pertanggungjawaban")
    if "SHR" in selected_reports: tab_titles.append("🗓️ Filter Data SHR")
    tab_titles.extend(["🏆 Peringkat Terbaik", "🔍 Pencarian Satker"])
    tabs = st.tabs(tab_titles)
    tab_index = 0

    if "LK" in selected_reports:
        with tabs[tab_index]:
            create_date_filter_tab(df=all_data.get("LK"), date_col='LK terupload', name_col='Nama Satker', header_text="Filter Data Upload LK")
        tab_index += 1
    if "LPJ" in selected_reports:
        with tabs[tab_index]:
            create_date_filter_tab(df=all_data.get("LPJ"), date_col='Tanggal Validasi LPJ', name_col='Jenis LPJ dan Nama Satker', header_text="Filter Data Validasi LPJ")
        tab_index += 1
    if "SHR" in selected_reports:
        with tabs[tab_index]:
            create_date_filter_tab(df=all_data.get("SHR"), date_col='Tanggal Tutup Periode', name_col='Nama Satker', header_text="Filter Data Tutup Periode SHR")
        tab_index += 1

    with tabs[tab_index]:
        st.header("🏆 Peringkat Satker Tercepat")
        st.markdown("Peringkat menampilkan hingga 5 besar tercepat, di mana satker pada hari yang sama mendapat peringkat yang sama.")
        
        def create_ranking_table(df, date_col, name_col):
            if df.empty or date_col not in df.columns or name_col not in df.columns:
                st.warning("Data tidak cukup untuk membuat peringkat.")
                return
            
            df_copy = df.copy()
            df_copy[f'{date_col}_dt'] = pd.to_datetime(df_copy[date_col], format='%d/%m/%Y', errors='coerce')
            df_copy.dropna(subset=[f'{date_col}_dt'], inplace=True)
            
            if df_copy.empty:
                st.info("Belum ada laporan yang masuk untuk kategori ini.")
                return
            
            df_copy['Peringkat'] = df_copy[f'{date_col}_dt'].dt.date.rank(method='dense').astype(int)
            ranked_df = df_copy.sort_values(by=[f'{date_col}_dt', name_col])
            top_5_ranks = ranked_df[ranked_df['Peringkat'] <= 5]
            
            if not top_5_ranks.empty:
                st.dataframe(
                    top_5_ranks[['Peringkat', name_col, date_col]],
                    use_container_width=True,
                    hide_index=True
                )
                st.success(f"Menampilkan {len(top_5_ranks)} satker dalam peringkat teratas.")
            else:
                st.info("Tidak ada data peringkat untuk ditampilkan.")

        if "LK" in selected_reports:
            st.subheader("LK Tercepat")
            create_ranking_table(all_data.get("LK"), 'LK terupload', 'Nama Satker')
            st.markdown("---")
        
        if "LPJ" in selected_reports:
            st.subheader("LPJ Tercepat")
            create_ranking_table(all_data.get("LPJ"), 'Tanggal Validasi LPJ', 'Jenis LPJ dan Nama Satker')
            st.markdown("---")

        if "SHR" in selected_reports:
            st.subheader("SHR Tercepat")
            create_ranking_table(all_data.get("SHR"), 'Tanggal Tutup Periode', 'Nama Satker')
        
        tab_index += 1

    with tabs[tab_index]:
        st.header("🔍 Cek Status Kepatuhan per Satker")
        kode_input = st.text_input("Masukkan Kode Satker:", placeholder="Contoh: 527123")
        if kode_input:
            # PERUBAHAN: Teruskan dictionary 'deadlines' ke fungsi pencarian
            display_search_results(kode_input, all_data, selected_reports, deadlines)
else:
    st.info("Silakan pilih minimal satu laporan dari filter di sidebar untuk menampilkan data.")
