import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
import urllib.parse
from datetime import datetime, timedelta

pd.set_option("styler.render.max_elements", 5000000)

st.set_page_config(page_title="B2B DELIVERY DASHBOARD", layout="wide", initial_sidebar_state="expanded")

CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "https://b2b-dashboard-dsgkivhypxmlqtjujsic2d.streamlit.app/")

# Lấy danh sách email được phép (cách nhau bằng dấu phẩy) từ secrets
ALLOWED_EMAILS = [e.strip().lower() for e in st.secrets.get("ALLOWED_EMAILS", "").split(",") if e.strip()]
ADMIN_EMAILS = [e.strip().lower() for e in st.secrets.get("ADMIN_EMAILS", "admin@ghn.vn").split(",") if e.strip()]

def require_login():
    if st.session_state.get("authenticated", False):
        return True
    st.markdown("<h3 style='text-align: center; color: #ff4b4b;'>BẢO MẬT HỆ THỐNG GHN B2B</h3>", unsafe_allow_html=True)
    query_params = st.query_params
    code = query_params.get("code")
    if code:
        token_url = "https://oauth2.googleapis.com/token"
        data = {"code": code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"}
        res = requests.post(token_url, data=data)
        if res.status_code == 200:
            access_token = res.json().get("access_token")
            user_res = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"})
            if user_res.status_code == 200:
                email = user_res.json().get("email", "").lower()
                # Cho phép nếu là mail @ghn.vn HOẶC nằm trong danh sách ALLOWED_EMAILS
                if email.endswith("@ghn.vn") or email in ALLOWED_EMAILS:
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = email
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Truy cập bị từ chối. Email '{email}' không có quyền truy cập.")
                    st.query_params.clear()
            else:
                st.error("Lỗi khi lấy thông tin người dùng từ Google.")
        else:
            st.error("Lỗi xác thực mã từ Google. Vui lòng thử đăng nhập lại.")
            st.query_params.clear()
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {"client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": "openid email profile", "access_type": "offline", "prompt": "select_account"}
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    st.markdown(f'''
    <div style="display: flex; justify-content: center; margin-top: 30px;">
        <a href="{url}" target="_top" style="text-decoration: none;">
            <div style="background-color: #4285F4; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; font-family: sans-serif; display: flex; align-items: center; gap: 10px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" width="20" style="background-color: white; padding: 5px; border-radius: 3px;">
                ĐĂNG NHẬP BẰNG GOOGLE
            </div>
        </a>
    </div>
    ''', unsafe_allow_html=True)
    return False

if not require_login():
    st.stop()

# ==================== LOAD DATA ====================
@st.cache_data(ttl=600)
def load_data():
    master_file = 'master_data.csv'
    if not os.path.exists(master_file):
        return pd.DataFrame(), master_file
    df = pd.read_csv(master_file)
    dt_columns = ['ThoiGianTao', 'ThoiGianLayThanhCong', 'ThoiGianXuatKienDauTien', 'ThoiGianGiaoThanhCong', 'ThoiGianNhanKienDauTien']
    for col in dt_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
    weight_col = 'KL_TinhCuoc_kg'
    if weight_col in df.columns:
        df[weight_col] = pd.to_numeric(df[weight_col], errors='coerce').fillna(0)
    else:
        df[weight_col] = 0
    return df, master_file

df_raw, master_file_path = load_data()
if df_raw.empty:
    st.error(f"Không tìm thấy file {master_file_path}.")
    st.stop()

st.title("B2B DELIVERY REPORTING DASHBOARD")

# Lọc bỏ ngày hiện tại (chỉ lấy đến hôm qua)
today = datetime.now().date()
# Tạo một DataFrame mới chỉ chứa dữ liệu đến D-1 dựa trên ThoiGianTao và ThoiGianLayThanhCong
# Ta sẽ không xóa hẳn data, nhưng khi tính toán báo cáo sẽ chỉ lấy các sự kiện xảy ra < today
df = df_raw.copy()

# ========== CHỌN THỜI GIAN VÀ BỘ LỌC (TOÀN CỤC) ==========
col1, col2 = st.columns(2)
with col1:
    time_freq = st.selectbox("⏰ NHÓM THEO THỜI GIAN:", options=['Ngày (D)', 'Tuần (W)', 'Tháng (M)'], index=0)
with col2:
    clients = st.multiselect("🎯 BỘ LỌC KHÁCH HÀNG (TOÀN CỤC):", options=df['client_name'].dropna().unique())

freq_map = {'Ngày (D)': 'D', 'Tuần (W)': 'W', 'Tháng (M)': 'M'}
nperiod_map = {'D': 30, 'W': 6, 'M': 3}
freq = freq_map[time_freq]
n_periods = nperiod_map[freq]

df_filtered = df.copy()
if clients:
    df_filtered = df_filtered[df_filtered['client_name'].isin(clients)]

WEIGHT_COL = 'KL_TinhCuoc_kg'

def get_period(dt_series, f):
    if f == 'D': return dt_series.dt.to_period('D').dt.start_time
    elif f == 'W': return dt_series.dt.to_period('W').dt.start_time
    elif f == 'M': return dt_series.dt.to_period('M').dt.start_time

def get_period_str(dt_series, f):
    if f == 'D': return dt_series.dt.strftime('%d/%m/%Y')
    elif f == 'W': return 'W' + dt_series.dt.strftime('%W-%Y')
    elif f == 'M': return 'T' + dt_series.dt.strftime('%m-%Y')

# Hàm hiển thị DataFrame dùng Styler để format số nguyên, giữ nguyên type số để sort
def display_dataframe(df_to_show):
    # Định dạng các cột số theo format {:,.0f} (vd 1,234)
    # Tách dòng TỔNG CỘNG ra một bảng riêng để không bị lẫn khi sort
    if isinstance(df_to_show.index, pd.MultiIndex):
        total_idx = ('TỔNG CỘNG', '')
    else:
        total_idx = 'TỔNG CỘNG'
        
    if total_idx in df_to_show.index:
        df_total = df_to_show.loc[[total_idx]]
        df_main = df_to_show.drop(index=total_idx)
        
        st.markdown("📊 **TỔNG CỘNG** *(Cố định)*")
        st.dataframe(df_total.style.format("{:,.0f}", na_rep=""), use_container_width=True)
        
        st.markdown("📝 **CHI TIẾT** *(Bấm vào tiêu đề cột để sắp xếp)*")
        st.dataframe(df_main.style.format("{:,.0f}", na_rep=""), use_container_width=True)
    else:
        st.dataframe(df_to_show.style.format("{:,.0f}", na_rep=""), use_container_width=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. ĐƠN LẤY & VÙNG GIAO", "2. ONTIME XUẤT HÀNG", "3. GIAO TRONG NGÀY (CONCUNG)", "4. QUẢN LÝ NETWORK (DB)", "5. PHÂN TÍCH SORT CODE"])

# ==================== TAB 1 ====================
with tab1:
    st.header("BÁO CÁO SẢN LƯỢNG (ĐƠN TẠO & LẤY THÀNH CÔNG)")

    df_tao_all = df_filtered.dropna(subset=['ThoiGianTao']).copy()
    df_lay_all = df_filtered.dropna(subset=['ThoiGianLayThanhCong']).copy()

    # Lọc bỏ ngày N (hôm nay) cho đơn lấy và tạo
    df_tao_all = df_tao_all[df_tao_all['ThoiGianTao'].dt.date < today]
    df_lay_all = df_lay_all[df_lay_all['ThoiGianLayThanhCong'].dt.date < today]

    # Flag đơn nhảy BC: KhoGiao không chứa từ "Kho"
    if 'KhoGiao' in df_tao_all.columns:
        df_tao_all['IsBC'] = ~df_tao_all['KhoGiao'].fillna('').str.contains('Kho', case=False)
    else:
        df_tao_all['IsBC'] = False
    if 'KhoGiao' in df_lay_all.columns:
        df_lay_all['IsBC'] = ~df_lay_all['KhoGiao'].fillna('').str.contains('Kho', case=False)
    else:
        df_lay_all['IsBC'] = False

    # Tính Period
    df_tao_all['Period'] = get_period(df_tao_all['ThoiGianTao'], freq)
    df_lay_all['Period'] = get_period(df_lay_all['ThoiGianLayThanhCong'], freq)
    df_tao_all['Period_Str'] = get_period_str(df_tao_all['ThoiGianTao'], freq)
    df_lay_all['Period_Str'] = get_period_str(df_lay_all['ThoiGianLayThanhCong'], freq)

    agg_tao = df_tao_all.groupby(['Period', 'Period_Str', 'client_name', 'VungGiao', 'TinhGiao']).agg(
        DonTao=('order_code', 'count'), CanNang=(WEIGHT_COL, 'sum'), DonBC=('IsBC', 'sum')
    ).reset_index()

    agg_lay = df_lay_all.groupby(['Period', 'Period_Str', 'client_name', 'VungGiao', 'TinhGiao']).agg(
        DonLayTC=('order_code', 'count'), CanNangLay=(WEIGHT_COL, 'sum')
    ).reset_index()

    report1 = pd.merge(agg_tao, agg_lay, on=['Period', 'Period_Str', 'client_name', 'VungGiao', 'TinhGiao'], how='outer').fillna(0)

    # Giới hạn số kỳ
    all_periods = report1[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)
    keep_periods = all_periods.head(n_periods)['Period'].tolist()
    report1 = report1[report1['Period'].isin(keep_periods)]
    sorted_periods = report1[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)['Period_Str'].tolist()

    if not report1.empty and len(sorted_periods) > 0:
        latest_p = sorted_periods[0]
        prev_p = sorted_periods[1] if len(sorted_periods) > 1 else None
        latest_data = report1[report1['Period_Str'] == latest_p]

        # ---- NHẬN XÉT ----
        st.info(f"💡 **NHẬN XÉT ({time_freq}):**")

        latest_tao = latest_data['DonTao'].sum()
        latest_lay = latest_data['DonLayTC'].sum()
        if prev_p:
            prev_tao = report1[report1['Period_Str'] == prev_p]['DonTao'].sum()
            diff = latest_tao - prev_tao
            trend = "tăng" if diff >= 0 else "giảm"
            st.markdown(f"- 📈 **Biến động:** Đơn tạo {latest_p} đạt **{latest_tao:,.0f}** đơn, **{trend} {abs(diff):,.0f}** so với {prev_p}.")

        don_bc = latest_data['DonBC'].sum()
        if don_bc > 0:
            st.markdown(f"- ⚠️ **Đơn nhảy BC:** Có **{don_bc:,.0f}** đơn đang nhảy về BC.")
        else:
            st.markdown(f"- ✅ Không có đơn nào nhảy về BC.")

        top_tinh = latest_data.groupby('TinhGiao')['CanNang'].sum().nlargest(5)
        if not top_tinh.empty:
            top_str = ", ".join([f"**{t}** ({v:,.1f} kg)" for t, v in top_tinh.items()])
            st.markdown(f"- 📦 **TOP 5 TỈNH KHỐI LƯỢNG LỚN NHẤT:** {top_str}")

        if freq in ('W', 'M'):
            top5_kh = latest_data.groupby('client_name')['DonTao'].sum().nlargest(5)
            if not top5_kh.empty:
                top5_str = ", ".join([f"**{k}** ({v:,.0f} đơn)" for k, v in top5_kh.items()])
                st.markdown(f"- 🏆 **TOP 5 KH VOL LỚN NHẤT:** {top5_str}")
            kh_bc = latest_data.groupby('client_name')['DonBC'].sum().nlargest(1)
            if not kh_bc.empty and kh_bc.values[0] > 0:
                st.markdown(f"- ⚠️ **KH NHẢY BC NHIỀU NHẤT:** **{kh_bc.index[0]}** với {kh_bc.values[0]:,.0f} đơn.")

        not_lay = latest_tao - latest_lay
        if not_lay > 0:
            st.markdown(f"- ⚠️ **Đang làm chưa tốt:** Có **{not_lay:,.0f}** đơn tạo nhưng chưa lấy thành công.")

        client_rates = latest_data.groupby('client_name').agg(DonTao=('DonTao', 'sum'), DonLayTC=('DonLayTC', 'sum'))
        client_rates['Rate'] = (client_rates['DonLayTC'] / client_rates['DonTao'] * 100).fillna(0)
        low_rate = client_rates[(client_rates['DonTao'] > 0) & (client_rates['Rate'] < 80)].sort_values('Rate')
        if not low_rate.empty:
            st.markdown(f"- 🚨 **CẢNH BÁO:** Các KH có tỷ lệ Lấy thành công thấp (<80%):")
            for kh, row in low_rate.iterrows():
                st.markdown(f"  - **{kh}**: {row['Rate']:.1f}% ({row['DonLayTC']:,.0f}/{row['DonTao']:,.0f} đơn)")

        # ---- BẢNG KHÁCH HÀNG ----
        st.subheader("BẢNG CHI TIẾT SẢN LƯỢNG THEO KHÁCH HÀNG")
        metrics = ['Đơn tạo', 'Đơn lấy TC', 'Cân nặng (kg)']
        pivot_detail = report1.pivot_table(index=['client_name'], columns='Period_Str',
            values=['DonTao', 'DonLayTC', 'CanNang'], aggfunc='sum', fill_value=0)
        pivot_detail = pivot_detail.swaplevel(0, 1, axis=1)
        pivot_detail = pivot_detail.rename(columns={'DonTao': 'Đơn tạo', 'DonLayTC': 'Đơn lấy TC', 'CanNang': 'Cân nặng (kg)'})
        pivot_detail.index.names = ['TÊN KHÁCH HÀNG']
        new_cols = pd.MultiIndex.from_product([sorted_periods, metrics])
        pivot_detail = pivot_detail.reindex(columns=new_cols).fillna(0)
        
        # Ẩn KH có 0 đơn toàn bộ kỳ
        zero_mask = (pivot_detail == 0).all(axis=1)
        pivot_detail = pivot_detail[~zero_mask]
        
        pivot_detail.loc['TỔNG CỘNG', :] = pivot_detail.sum(numeric_only=True).values
        display_dataframe(pivot_detail)

        # ---- BẢNG VÙNG GIAO ----
        st.subheader("BẢNG TỔNG HỢP THEO VÙNG / TỈNH GIAO")
        pivot_vung = report1.pivot_table(index=['VungGiao', 'TinhGiao'], columns='Period_Str',
            values=['DonTao', 'DonLayTC', 'CanNang'], aggfunc='sum', fill_value=0)
        pivot_vung = pivot_vung.swaplevel(0, 1, axis=1)
        pivot_vung = pivot_vung.rename(columns={'DonTao': 'Đơn tạo', 'DonLayTC': 'Đơn lấy TC', 'CanNang': 'Cân nặng (kg)'})
        pivot_vung.index.names = ['VÙNG GIAO', 'TỈNH GIAO']
        pivot_vung = pivot_vung.reindex(columns=new_cols).fillna(0)
        pivot_vung.loc[('TỔNG CỘNG', ''), :] = pivot_vung.sum(numeric_only=True).values
        display_dataframe(pivot_vung)

        # ---- BIỂU ĐỒ ----
        st.subheader("BIỂU ĐỒ TỔNG QUAN SẢN LƯỢNG")
        chart_data = report1.groupby(['Period', 'Period_Str'])[['DonTao', 'DonLayTC']].sum().reset_index()
        chart_data = chart_data.sort_values('Period', ascending=True)
        fig = px.bar(chart_data, x='Period_Str', y=['DonTao', 'DonLayTC'], barmode='group',
            labels={'value': 'Số lượng', 'Period_Str': 'Thời gian', 'variable': 'Chỉ số', 'DonTao': 'Đơn tạo', 'DonLayTC': 'Đơn lấy TC'})
        fig.update_xaxes(categoryorder='array', categoryarray=chart_data['Period_Str'].tolist())
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("XEM CHI TIẾT CÁC ĐƠN NHẢY VỀ BƯU CỤC (BC)"):
            df_bc = df_tao_all[df_tao_all['IsBC']]
            if not df_bc.empty:
                cols_show = ['order_code', 'client_name', 'KhoLay', 'TinhGiao', WEIGHT_COL, 'ThoiGianTao']
                cols_show = [c for c in cols_show if c in df_bc.columns]
                st.dataframe(df_bc[cols_show].sort_values('ThoiGianTao', ascending=False))
            else:
                st.info("Không có đơn nhảy về BC.")
    else:
        st.info("Không có dữ liệu")

# ==================== TAB 2 ====================
with tab2:
    st.header("BÁO CÁO ONTIME XUẤT HÀNG")
    st.markdown("Quy định: \n- Lấy thành công **trước 20h ngày N** → phải xuất kiện **trước 6h sáng ngày N+1**.\n- Lấy thành công **sau 20h ngày N** → phải xuất kiện **trước 20h ngày N+1**.\n*(Loại trừ đơn giao tại kho B2B Đài Tư)*")

    df_ontime = df_filtered.dropna(subset=['ThoiGianLayThanhCong']).copy()

    # Lọc bỏ ngày N (hôm nay)
    df_ontime = df_ontime[df_ontime['ThoiGianLayThanhCong'].dt.date < today]

    # Loại trừ đơn có KhoGiao chứa "Đài Tư"
    if 'KhoGiao' in df_ontime.columns:
        df_ontime = df_ontime[~df_ontime['KhoGiao'].fillna('').str.contains('Đài Tư', case=False)]

    df_ontime['NgayLay'] = df_ontime['ThoiGianLayThanhCong'].dt.date
    df_ontime['GioLay'] = df_ontime['ThoiGianLayThanhCong'].dt.hour
    
    import numpy as np
    base_date = pd.to_datetime(df_ontime['NgayLay'])
    df_ontime['DeadlineXuat'] = np.where(
        df_ontime['GioLay'] < 20,
        base_date + pd.Timedelta(days=1, hours=6),
        base_date + pd.Timedelta(days=1, hours=20)
    )

    def check_ontime(row):
        if pd.isna(row['ThoiGianXuatKienDauTien']): return False
        return row['ThoiGianXuatKienDauTien'] <= row['DeadlineXuat']

    df_ontime['Is_Ontime'] = df_ontime.apply(check_ontime, axis=1)

    # Tính Period cho Ontime
    df_ontime['Period'] = get_period(df_ontime['ThoiGianLayThanhCong'], freq)
    df_ontime['Period_Str'] = get_period_str(df_ontime['ThoiGianLayThanhCong'], freq)

    ontime_summary = df_ontime.groupby(['Period', 'Period_Str', 'client_name']).agg(
        TongDon=('order_code', 'count'),
        Ontime=('Is_Ontime', 'sum')
    ).reset_index()
    ontime_summary['TyLe_Ontime (%)'] = (ontime_summary['Ontime'] / ontime_summary['TongDon'] * 100).round(2)

    # Giới hạn số kỳ
    all_p_ontime = ontime_summary[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)
    keep_p_ontime = all_p_ontime.head(n_periods)['Period'].tolist()
    ontime_summary = ontime_summary[ontime_summary['Period'].isin(keep_p_ontime)]
    sorted_p_ontime = ontime_summary[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)['Period_Str'].tolist()

    if not ontime_summary.empty:
        latest_p_ot = sorted_p_ontime[0] if sorted_p_ontime else None
        prev_p_ot = sorted_p_ontime[1] if len(sorted_p_ontime) > 1 else None

        if latest_p_ot:
            latest_ot_data = ontime_summary[ontime_summary['Period_Str'] == latest_p_ot]
            latest_pct = (latest_ot_data['Ontime'].sum() / latest_ot_data['TongDon'].sum() * 100) if latest_ot_data['TongDon'].sum() > 0 else 0

            prev_pct = None
            if prev_p_ot:
                prev_ot_data = ontime_summary[ontime_summary['Period_Str'] == prev_p_ot]
                prev_pct = (prev_ot_data['Ontime'].sum() / prev_ot_data['TongDon'].sum() * 100) if prev_ot_data['TongDon'].sum() > 0 else 0

            st.info("💡 **NHẬN XÉT TÌNH HÌNH ONTIME:**")
            comp = ""
            if prev_pct is not None:
                diff_pct = latest_pct - prev_pct
                comp = f"(**{'tăng' if diff_pct >= 0 else 'giảm'} {abs(diff_pct):.1f}%** so với kỳ trước)"
            st.markdown(f"- 📈 **Biến động:** Tỷ lệ Ontime kỳ {latest_p_ot} đạt **{latest_pct:.1f}%** {comp}")

            if not latest_ot_data.empty:
                worst_client = latest_ot_data.sort_values('TyLe_Ontime (%)').iloc[0]
                not_ontime = worst_client['TongDon'] - worst_client['Ontime']
                if not_ontime > 0:
                    st.markdown(f"- ⚠️ **Đang làm chưa tốt:** KH **{worst_client['client_name']}** Ontime thấp nhất (**{worst_client['TyLe_Ontime (%)']}%**) với {not_ontime:,.0f} đơn trễ.")

        # Pivot với 3 cột: Tổng đơn, Đơn Ontime, Tỷ lệ
        pivot_ontime = ontime_summary.pivot_table(
            index='client_name', columns='Period_Str',
            values=['TongDon', 'Ontime', 'TyLe_Ontime (%)'],
            aggfunc='sum', fill_value=0)
        pivot_ontime = pivot_ontime.swaplevel(0, 1, axis=1)
        pivot_ontime = pivot_ontime.rename(columns={'TongDon': 'Tổng đơn', 'Ontime': 'Đơn Ontime', 'TyLe_Ontime (%)': 'Tỷ lệ Ontime (%)'})
        pivot_ontime.index.names = ['TÊN KHÁCH HÀNG']
        new_cols_ot = pd.MultiIndex.from_product([sorted_p_ontime, ['Tổng đơn', 'Đơn Ontime', 'Tỷ lệ Ontime (%)']])
        pivot_ontime = pivot_ontime.reindex(columns=new_cols_ot).fillna(0)

        zero_mask_ot = (pivot_ontime.xs('Tổng đơn', level=1, axis=1) == 0).all(axis=1)
        pivot_ontime = pivot_ontime[~zero_mask_ot]

        total_row = pivot_ontime.sum(numeric_only=True)
        for p in sorted_p_ontime:
            t_don = total_row[(p, 'Tổng đơn')]
            t_ot = total_row[(p, 'Đơn Ontime')]
            total_row[(p, 'Tỷ lệ Ontime (%)')] = (t_ot / t_don * 100) if t_don > 0 else 0
        pivot_ontime.loc['TỔNG CỘNG', :] = total_row

        st.subheader("BẢNG CHI TIẾT SỐ ĐƠN VÀ TỶ LỆ ONTIME (%)")
        df_total_ot = pivot_ontime.loc[['TỔNG CỘNG']]
        df_main_ot = pivot_ontime.drop(index='TỔNG CỘNG')
        
        st.markdown("📊 **TỔNG CỘNG** *(Cố định)*")
        st.dataframe(df_total_ot.style.format(na_rep="", formatter="{:,.0f}", subset=pd.IndexSlice[:, (sorted_p_ontime, ['Tổng đơn', 'Đơn Ontime'])]).format(na_rep="", formatter="{:,.2f}%", subset=pd.IndexSlice[:, (sorted_p_ontime, ['Tỷ lệ Ontime (%)'])]), use_container_width=True)
        st.markdown("📝 **CHI TIẾT** *(Bấm vào tiêu đề cột để sắp xếp)*")
        st.dataframe(df_main_ot.style.format(na_rep="", formatter="{:,.0f}", subset=pd.IndexSlice[:, (sorted_p_ontime, ['Tổng đơn', 'Đơn Ontime'])]).format(na_rep="", formatter="{:,.2f}%", subset=pd.IndexSlice[:, (sorted_p_ontime, ['Tỷ lệ Ontime (%)'])]), use_container_width=True)

        st.subheader("BIỂU ĐỒ TỶ LỆ ONTIME XUẤT HÀNG")
        chart_data_2 = ontime_summary.sort_values('Period', ascending=True)
        fig2 = px.line(chart_data_2, x='Period_Str', y='TyLe_Ontime (%)', color='client_name', markers=True,
            labels={'Period_Str': 'Thời gian', 'TyLe_Ontime (%)': 'Tỷ lệ Ontime (%)', 'client_name': 'Tên khách hàng'})
        fig2.update_xaxes(categoryorder='array', categoryarray=chart_data_2['Period_Str'].drop_duplicates().tolist())
        fig2.update_layout(xaxis_title="Thời gian")
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("XEM CHI TIẾT CÁC ĐƠN BỊ TRỄ (LATE)"):
        late_orders = df_ontime[~df_ontime['Is_Ontime']]
        cols_show = ['order_code', 'client_name', 'KhoGiao', 'ThoiGianLayThanhCong', 'ThoiGianXuatKienDauTien', 'DeadlineXuat']
        cols_show = [c for c in cols_show if c in late_orders.columns]
        st.dataframe(late_orders[cols_show].sort_values('ThoiGianLayThanhCong', ascending=False))

# ==================== TAB 3 ====================
with tab3:
    st.header("BÁO CÁO GIAO TRONG NGÀY - SAMEDAY (CONCUNG)")
    st.markdown("Quy định: Đơn Concung **lấy thành công** tại HN, Bắc Ninh, Hải Dương, Hưng Yên phải **giao thành công trong cùng ngày lấy**.")

    df_concung = df_filtered[df_filtered['client_name'].str.contains('Concung|Con Cưng', case=False, na=False)].copy()
    tinh_giao_hop_le = ['Hà Nội', 'Hưng Yên', 'Bắc Ninh', 'Hải Dương']
    df_concung = df_concung[df_concung['TinhGiao'].isin(tinh_giao_hop_le)]
    # Chỉ tính đơn đã lấy thành công
    df_concung = df_concung.dropna(subset=['ThoiGianLayThanhCong'])

    # Lọc bỏ ngày N (hôm nay)
    df_concung = df_concung[df_concung['ThoiGianLayThanhCong'].dt.date < today]

    df_concung['NgayLay_DT'] = df_concung['ThoiGianLayThanhCong'].dt.date

    def check_giao_trong_ngay_lay(row):
        """Đơn lấy trong ngày phải giao xong trong ngày"""
        if pd.isna(row['ThoiGianGiaoThanhCong']): return False
        return row['ThoiGianGiaoThanhCong'].date() == row['NgayLay_DT']

    df_concung['GiaoTrongNgayLay'] = df_concung.apply(check_giao_trong_ngay_lay, axis=1)

    # Tính Period cho Concung
    df_concung['Period'] = get_period(df_concung['ThoiGianLayThanhCong'], freq)
    df_concung['Period_Str'] = get_period_str(df_concung['ThoiGianLayThanhCong'], freq)

    concung_summary = df_concung.groupby(['Period', 'Period_Str']).agg(
        TongDonLay=('order_code', 'count'),
        DonGiaoTrongNgay=('GiaoTrongNgayLay', 'sum')
    ).reset_index()

    # Giới hạn số kỳ
    all_p_cc = concung_summary[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)
    keep_p_cc = all_p_cc.head(n_periods)['Period'].tolist()
    concung_summary = concung_summary[concung_summary['Period'].isin(keep_p_cc)]

    if not concung_summary.empty:
        concung_summary['TyLe_Sameday (%)'] = (concung_summary['DonGiaoTrongNgay'] / concung_summary['TongDonLay'] * 100).round(2)
        concung_summary = concung_summary.sort_values('Period', ascending=False)

        sorted_p_cc = concung_summary[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)['Period_Str'].tolist()
        latest_p_cc = sorted_p_cc[0] if sorted_p_cc else None
        prev_p_cc = sorted_p_cc[1] if len(sorted_p_cc) > 1 else None

        if latest_p_cc:
            latest_cc = concung_summary[concung_summary['Period_Str'] == latest_p_cc]
            t_lay = latest_cc['TongDonLay'].sum()
            t_giao = latest_cc['DonGiaoTrongNgay'].sum()
            latest_pct = (t_giao / t_lay * 100) if t_lay > 0 else 0

            prev_pct = None
            if prev_p_cc:
                prev_cc = concung_summary[concung_summary['Period_Str'] == prev_p_cc]
                t_lay_prev = prev_cc['TongDonLay'].sum()
                t_giao_prev = prev_cc['DonGiaoTrongNgay'].sum()
                prev_pct = (t_giao_prev / t_lay_prev * 100) if t_lay_prev > 0 else 0

            st.info("💡 **NHẬN XÉT GIAO HÀNG SAMEDAY CONCUNG:**")
            comp = ""
            if prev_pct is not None:
                diff_pct = latest_pct - prev_pct
                comp = f"(**{'tăng' if diff_pct >= 0 else 'giảm'} {abs(diff_pct):.1f}%** so với kỳ trước)"
            st.markdown(f"- 📈 **Biến động:** Kỳ {latest_p_cc}, tỷ lệ sameday đạt **{latest_pct:.1f}%** ({t_giao:,.0f}/{t_lay:,.0f} đơn) {comp}")

            not_done = t_lay - t_giao
            if not_done > 0:
                st.markdown(f"- ⚠️ **Đang làm chưa tốt:** Còn **{not_done:,.0f}** đơn lấy rồi nhưng chưa giao trong ngày.")
            else:
                st.markdown(f"- ✅ **Điểm sáng:** 100% đơn lấy kỳ {latest_p_cc} đã giao thành công trong ngày.")

        df_display_cc = concung_summary.drop(columns=['Period']).rename(columns={
            'Period_Str': 'Thời gian', 'TongDonLay': 'Đơn lấy',
            'DonGiaoTrongNgay': 'Giao trong ngày', 'TyLe_Sameday (%)': 'Tỷ lệ sameday (%)'
        })
        st.dataframe(df_display_cc.style.format(na_rep="", formatter="{:,.0f}", subset=['Đơn lấy', 'Giao trong ngày']).format(na_rep="", formatter="{:,.2f}%", subset=['Tỷ lệ sameday (%)']), use_container_width=True)

        st.subheader("ĐỒ THỊ TÌNH HÌNH XỬ LÝ SAMEDAY")
        chart_cc = concung_summary.groupby(['Period', 'Period_Str'])[['TongDonLay', 'DonGiaoTrongNgay']].sum().reset_index()
        chart_cc = chart_cc.sort_values('Period', ascending=True)
        fig3 = px.bar(chart_cc, x='Period_Str', y=['TongDonLay', 'DonGiaoTrongNgay'], barmode='group',
            title="TÌNH HÌNH LẤY - GIAO TRONG NGÀY",
            labels={'Period_Str': 'Thời gian', 'value': 'Số lượng', 'variable': 'Chỉ số', 'TongDonLay': 'Đơn lấy', 'DonGiaoTrongNgay': 'Giao trong ngày'})
        fig3.update_xaxes(categoryorder='array', categoryarray=chart_cc['Period_Str'].tolist())
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Không có dữ liệu đơn Concung tại 4 tỉnh sameday.")

    with st.expander("XEM CHI TIẾT ĐƠN CHƯA GIAO TRONG NGÀY"):
        not_delivered = df_concung[~df_concung['GiaoTrongNgayLay']]
        cols_cc = ['order_code', 'TinhGiao', 'TrangThaiHienTai', 'ThoiGianLayThanhCong', 'ThoiGianGiaoThanhCong']
        cols_cc = [c for c in cols_cc if c in not_delivered.columns]
        st.dataframe(not_delivered[cols_cc])

# ==================== TAB 4 ====================
with tab4:
    st.header("QUẢN LÝ NETWORK B2B (DATABASE)")
    st.markdown("Thay đổi dữ liệu tại đây sẽ cập nhật trực tiếp vào cơ sở dữ liệu hệ thống.")
    
    from sqlalchemy import create_engine, text
    import sqlite3

    DATABASE_URL = st.secrets.get("DATABASE_URL", "")
    
    def get_engine():
        if DATABASE_URL:
            return create_engine(DATABASE_URL)
        else:
            return create_engine("sqlite:///b2b_network.db")

    def init_cloud_db():
        engine = get_engine()
        with engine.connect() as conn:
            if DATABASE_URL:
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS provinces_mapping (
                        id SERIAL PRIMARY KEY,
                        province TEXT UNIQUE,
                        level1_code TEXT,
                        level2_code TEXT,
                        fixed_route TEXT
                    )
                '''))
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS routes_schedule (
                        id SERIAL PRIMARY KEY,
                        route_code TEXT,
                        hub TEXT,
                        departure_time TEXT
                    )
                '''))
            else:
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS provinces_mapping (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        province TEXT UNIQUE,
                        level1_code TEXT,
                        level2_code TEXT,
                        fixed_route TEXT
                    )
                '''))
                conn.execute(text('''
                    CREATE TABLE IF NOT EXISTS routes_schedule (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        route_code TEXT,
                        hub TEXT,
                        departure_time TEXT
                    )
                '''))
            conn.commit()

    init_cloud_db()

    def load_db_data(table_name):
        try:
            engine = get_engine()
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", engine)
            return df
        except Exception as e:
            st.error(f"Lỗi kết nối DB: {e}")
            return pd.DataFrame()
            
    def save_db_data(df, table_name):
        try:
            engine = get_engine()
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {table_name}"))
                conn.commit()
            df.to_sql(table_name, engine, if_exists='append', index=False)
            st.success(f"✅ Đã lưu thay đổi vào bảng {table_name}!")
        except Exception as e:
            st.error(f"Lỗi khi lưu DB: {e}")

    if DATABASE_URL:
        st.caption("🟢 Đang kết nối: **Cloud Database (Supabase)**")
    else:
        st.caption("🟡 Đang kết nối: **Local SQLite** (chưa cấu hình DATABASE_URL trong Secrets)")

    st.subheader("1. Bản Đồ Phân Bổ Tỉnh Thành")
    df_prov_db = load_db_data('provinces_mapping')
    if not df_prov_db.empty:
        if st.session_state.get("user_email") in ADMIN_EMAILS:
            edited_prov = st.data_editor(df_prov_db, num_rows="dynamic", key="editor_prov", use_container_width=True)
            if st.button("💾 Lưu Bản Đồ Tỉnh Thành"):
                save_db_data(edited_prov, 'provinces_mapping')
        else:
            st.dataframe(df_prov_db, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu. Hãy bấm nút bên dưới để nạp dữ liệu mẫu (nếu bạn là Admin).")
            
    st.subheader("2. Lịch Trình Xuất Bến (KTC Hưng Yên & Đài Tư)")
    df_routes_db = load_db_data('routes_schedule')
    if not df_routes_db.empty:
        if st.session_state.get("user_email") in ADMIN_EMAILS:
            edited_routes = st.data_editor(df_routes_db, num_rows="dynamic", key="editor_routes", use_container_width=True)
            if st.button("💾 Lưu Lịch Trình"):
                save_db_data(edited_routes, 'routes_schedule')
        else:
            st.dataframe(df_routes_db, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu lịch trình.")
# ==================== TAB 5 ====================
with tab5:
    st.header("PHÂN TÍCH SORT CODE & TUYẾN TẢI CHUNG")
    st.markdown("Xác định các mã sort code đang được phân bổ chung cho nhiều Tỉnh Giao để từ đó ghép chung tuyến xe tải.")
    
    st.subheader("1. Dữ liệu Sort Code")
    sort_file = st.file_uploader("Tải lên file phân tích Sort Code (Excel/CSV)", type=['xlsx', 'xls', 'csv'])
    
    if sort_file is None:
        import glob
        local_files = glob.glob('sqllab_*.xlsx') + glob.glob('sort_code*.xlsx')
        if local_files:
            sort_file = local_files[0]
            st.info(f"Đang sử dụng file nội bộ: `{sort_file}`")
            
    if sort_file is not None:
        try:
            if isinstance(sort_file, str):
                if sort_file.endswith('.csv'):
                    df_sort = pd.read_csv(sort_file)
                else:
                    df_sort = pd.read_excel(sort_file)
            else:
                if sort_file.name.endswith('.csv'):
                    df_sort = pd.read_csv(sort_file)
                else:
                    df_sort = pd.read_excel(sort_file)
                    
            if 'sort_code' not in df_sort.columns or 'TinhGiao' not in df_sort.columns or 'SoLuongDon' not in df_sort.columns:
                st.error("File tải lên không đúng định dạng. Cần có các cột: `sort_code`, `TinhGiao`, `SoLuongDon`.")
            else:
                st.subheader("2. Lọc & Phân tích")
                col1, col2 = st.columns([1, 2])
                with col1:
                    min_orders = st.slider("Bỏ qua các mã sort có số lượng đơn dưới:", min_value=10, max_value=5000, value=500, step=10)
                
                # Gom nhóm
                df_grouped = df_sort.groupby(['sort_code', 'TinhGiao'])['SoLuongDon'].sum().reset_index()
                df_grouped = df_grouped[df_grouped['SoLuongDon'] >= min_orders]
                
                # Tìm mã sort dùng chung
                sort_counts = df_grouped.groupby('sort_code')['TinhGiao'].nunique().reset_index()
                shared_sorts = sort_counts[sort_counts['TinhGiao'] > 1]['sort_code'].tolist()
                
                df_shared = df_grouped[df_grouped['sort_code'].isin(shared_sorts)].copy()
                
                if df_shared.empty:
                    st.warning(f"Không có mã sort nào dùng chung cho từ 2 tỉnh trở lên (với điều kiện SL đơn >= {min_orders}).")
                else:
                    # Bảng tổng hợp
                    summary = df_shared.groupby('sort_code').agg(
                        TinhGiao=('TinhGiao', lambda x: ", ".join(x)),
                        SoTinh=('TinhGiao', 'count'),
                        TongSoDon=('SoLuongDon', 'sum')
                    ).reset_index().sort_values('TongSoDon', ascending=False)
                    
                    st.markdown(f"**Kết quả:** Tìm thấy **{len(summary)}** mã sort được dùng chung cho nhiều tỉnh.")
                    st.dataframe(summary.rename(columns={'sort_code': 'Mã Sort', 'TinhGiao': 'Các Tỉnh Giao', 'SoTinh': 'Số lượng Tỉnh', 'TongSoDon': 'Tổng Số Đơn'}).style.format("{:,.0f}", subset=['Tổng Số Đơn']), use_container_width=True)
                    
                    st.subheader("3. Chi tiết phân bổ theo Tỉnh")
                    st.dataframe(df_shared.rename(columns={'sort_code': 'Mã Sort', 'TinhGiao': 'Tỉnh Giao', 'SoLuongDon': 'Số lượng Đơn'}).sort_values(['sort_code', 'Số lượng Đơn'], ascending=[True, False]).style.format("{:,.0f}", subset=['Số lượng Đơn']), use_container_width=True)
                    
        except Exception as e:
            st.error(f"Lỗi khi đọc file: {e}")


# Di chuyển thông tin sidebar xuống dưới cùng
st.sidebar.markdown("---")
st.sidebar.info(f"Đang đọc dữ liệu từ:\n\n`{master_file_path}`")
st.sidebar.success(f"👤 Đăng nhập bởi:\n\n{st.session_state.get('user_email', '')}")
