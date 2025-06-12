import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURASI HALAMAN DAN JUDUL UTAMA ---
st.set_page_config(layout="wide", page_title="Dashboard Kepatuhan Satker")
st.title("📊 Dashboard Kepatuhan LK, LPJ, dan SHR")
st.markdown("Dasbor terpusat untuk memonitor progres dan kinerja Satuan Kerja.")

# --- FUNGSI UNTUK MEMUAT DATA (DENGAN CACHING) ---
@st.cache_data
def load_all_data(sheet_id):
    """Memuat data dari semua sheet yang relevan (LK, LPJ, SHR) ke dalam dictionary."""
    sheet_names = ["LK", "LPJ", "SHR"]
    dataframes = {}
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="

    for name in sheet_names:
        try:
            url = base_url + name
            dataframes[name] = pd.read_csv(url, dtype=str)
        except Exception as e:
            st.error(f"Gagal memuat sheet '{name}': {e}")
            dataframes[name] = pd.DataFrame()
    return dataframes

# --- FUNGSI UNTUK MEMBUAT TAB FILTER DATA BERDASARKAN TANGGAL TUNGGAL ---
def create_date_filter_tab(df, date_col, header_text):
    """Fungsi untuk membuat UI filter tanggal tunggal dan menampilkan data yang difilter."""
    st.header(header_text)

    if df.empty or date_col not in df.columns:
        st.warning(f"Data atau kolom '{date_col}' tidak tersedia.")
        return

    df_copy = df.copy()
    # Buat kolom datetime baru untuk filtering
    df_copy[f'{date_col}_dt'] = pd.to_datetime(df_copy[date_col], format='%d/%m/%Y', errors='coerce')
    df_copy.dropna(subset=[f'{date_col}_dt'], inplace=True)

    if df_copy.empty:
        st.warning(f"Tidak ada data tanggal yang valid untuk difilter.")
        return

    min_date = df_copy[f'{date_col}_dt'].min().date()
    max_date = df_copy[f'{date_col}_dt'].max().date()

    selected_date = st.date_input(
        "Pilih tanggal untuk ditampilkan:",
        value=max_date,  # Default ke tanggal terakhir yang ada data
        min_value=min_date,
        max_value=max_date,
        key=f"date_filter_{date_col}"
    )

    if selected_date:
        # Konversi tanggal yang dipilih ke datetime untuk perbandingan yang akurat
        selected_datetime = pd.to_datetime(selected_date)

        # Filter dataframe untuk tanggal yang sama dengan yang dipilih
        mask = (df_copy[f'{date_col}_dt'].dt.date == selected_datetime.date())
        filtered_df = df_copy[mask]

        st.info(f"Menampilkan **{len(filtered_df)} data** pada tanggal **{selected_date.strftime('%d-%m-%Y')}**.")

        # Tampilkan data yang sudah difilter
        st.dataframe(filtered_df[['Kode Satker', 'Nama Satker', date_col]], use_container_width=True, hide_index=True)


# --- EKSEKUSI UTAMA APLIKASI ---
SHEET_ID = "1WIvE_yZDfeH_lD5z6sboMfMnSL0Gy9vEQJcxvA91BVk"
all_data = load_all_data(SHEET_ID)

# --- FILTER UTAMA UNTUK MEMILIH LAPORAN ---
st.sidebar.header("Filter Laporan")
report_options = {
    "Laporan Keuangan (LK)": "LK",
    "Laporan Pertanggungjawaban (LPJ)": "LPJ",
    "SHR": "SHR"
}
selected_reports_display = st.sidebar.multiselect(
    "Pilih laporan yang ingin ditampilkan:",
    options=list(report_options.keys()),
    default=list(report_options.keys())
)
selected_reports = [report_options[report] for report in selected_reports_display]


# --- BUAT TAB SECARA DINAMIS ---
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
            create_date_filter_tab(df=all_data.get("LK"), date_col='LK terupload', header_text="Filter Data Upload Laporan Keuangan (LK)")
        tab_index += 1

    if "LPJ" in selected_reports:
        with tabs[tab_index]:
            create_date_filter_tab(df=all_data.get("LPJ"), date_col='Tanggal Validasi LPJ', header_text="Filter Data Validasi Laporan Pertanggungjawaban (LPJ)")
        tab_index += 1

    if "SHR" in selected_reports:
        with tabs[tab_index]:
            create_date_filter_tab(df=all_data.get("SHR"), date_col='Tanggal Tutup Periode', header_text="Filter Data Tutup Periode (SHR)")
        tab_index += 1

    with tabs[tab_index]:
        st.header("🏆 Peringkat 5 Satker Tercepat")
        st.markdown("Peringkat hanya menampilkan laporan yang Anda pilih di filter.")

        cols = st.columns(len(selected_reports) or 1)
        col_index = 0

        def create_ranking_table(df, date_col):
            df_copy = df.copy()
            if not df_copy.empty and date_col in df_copy.columns:
                df_copy[f'{date_col}_dt'] = pd.to_datetime(df_copy[date_col], format='%d/%m/%Y', errors='coerce')
                df_copy.dropna(subset=[f'{date_col}_dt'], inplace=True)

                terbaik_df = df_copy.sort_values(by=f'{date_col}_dt').head(5).reset_index(drop=True)
                terbaik_df.insert(0, 'Peringkat', range(1, 1 + len(terbaik_df)))

                st.dataframe(
                    terbaik_df[['Peringkat', 'Nama Satker', date_col]],
                    use_container_width=True,
                    hide_index=True
                )

        if "LK" in selected_reports:
            with cols[col_index]:
                st.subheader("LK Tercepat")
                create_ranking_table(all_data.get("LK"), 'LK terupload')
            col_index += 1

        if "LPJ" in selected_reports:
            with cols[col_index]:
                st.subheader("LPJ Tercepat")
                create_ranking_table(all_data.get("LPJ"), 'Tanggal Validasi LPJ')
            col_index += 1

        if "SHR" in selected_reports:
            with cols[col_index]:
                st.subheader("SHR Tercepat")
                create_ranking_table(all_data.get("SHR"), 'Tanggal Tutup Periode')
        tab_index += 1

    with tabs[tab_index]:
        st.header("🔍 Cek Status Kepatuhan per Satker")

        df_lk_simple = all_data.get("LK", pd.DataFrame()).get(['Kode Satker', 'Nama Satker', 'LK terupload'], pd.DataFrame())
        df_lpj_simple = all_data.get("LPJ", pd.DataFrame()).get(['Kode Satker', 'Nama Satker', 'Tanggal Validasi LPJ'], pd.DataFrame())
        df_shr_simple = all_data.get("SHR", pd.DataFrame()).get(['Kode Satker', 'Nama Satker', 'Tanggal Tutup Periode'], pd.DataFrame())

        if not df_lk_simple.empty:
            df_master = pd.merge(df_lk_simple, df_lpj_simple, on=['Kode Satker', 'Nama Satker'], how='outer')
            df_master = pd.merge(df_master, df_shr_simple, on=['Kode Satker', 'Nama Satker'], how='outer')
        else:
            df_master = pd.DataFrame()

        kode_input = st.text_input("Masukkan Kode Satker untuk melihat detail:", placeholder="Contoh: 527123")

        if kode_input:
            satker_data_row = df_master[df_master['Kode Satker'].astype(str) == kode_input]

            if not satker_data_row.empty:
                satker_data = satker_data_row.iloc[0]

                st.subheader(f"Detail untuk: {satker_data['Nama Satker']}")
                st.text(f"Kode Satker: {satker_data['Kode Satker']}")

                search_cols = st.columns(len(selected_reports) or 1)
                search_col_index = 0

                def get_status(date_str, deadline_day):
                    try:
                        dt = datetime.strptime(str(date_str), '%d/%m/%Y')
                        return ("✅ Tepat Waktu", "normal") if dt.day <= deadline_day else ("❌ Terlambat", "inverse")
                    except (TypeError, ValueError):
                        return "Belum Upload", "off"

                if "LK" in selected_reports:
                    with search_cols[search_col_index]:
                        status, delta_color = get_status(satker_data.get('LK terupload'), 15)
                        st.metric(label="Upload LK", value=satker_data.get('LK terupload', "N/A"), delta=status, delta_color=delta_color)
                    search_col_index += 1

                if "LPJ" in selected_reports:
                    with search_cols[search_col_index]:
                        status, delta_color = get_status(satker_data.get('Tanggal Validasi LPJ'), 15)
                        st.metric(label="Validasi LPJ", value=satker_data.get('Tanggal Validasi LPJ', "N/A"), delta=status, delta_color=delta_color)
                    search_col_index += 1

                if "SHR" in selected_reports:
                    with search_cols[search_col_index]:
                        status, delta_color = get_status(satker_data.get('Tanggal Tutup Periode'), 20)
                        st.metric(label="Tutup Periode", value=satker_data.get('Tanggal Tutup Periode', "N/A"), delta=status, delta_color=delta_color)
            else:
                st.warning(f"Kode Satker '{kode_input}' tidak ditemukan. Mohon periksa kembali.")
else:
    st.info("Silakan pilih minimal satu laporan dari filter di sidebar untuk menampilkan data.")
