import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
import requests
import urllib.parse

# Set a large max_elements just in case, but we will mostly format manually
pd.set_option("styler.render.max_elements", 5000000)

st.set_page_config(page_title="B2B Delivery Dashboard", layout="wide", initial_sidebar_state="expanded")

CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = "https://b2b-dashboard-dsgkivhypxmlqtjujsic2d.streamlit.app/"

def require_login():
    if st.session_state.get("authenticated", False):
        return True
        
    st.markdown("<h3 style='text-align: center; color: #ff4b4b;'>Bảo mật Hệ thống GHN B2B</h3>", unsafe_allow_html=True)
    
    # Lấy mã phản hồi từ Google sau khi đăng nhập thành công
    query_params = st.query_params
    code = query_params.get("code")
    
    if code:
        # Gửi mã (code) đi đổi lấy Token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        res = requests.post(token_url, data=data)
        if res.status_code == 200:
            access_token = res.json().get("access_token")
            # Dùng Token để gọi API lấy thông tin Profile (Email)
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            user_res = requests.get(user_info_url, headers=headers)
            if user_res.status_code == 200:
                email = user_res.json().get("email", "")
                if email.endswith("@ghn.vn"):
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = email
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Truy cập bị từ chối. Email '{email}' không thuộc tên miền nội bộ @ghn.vn.")
                    st.query_params.clear()
            else:
                st.error("Lỗi khi lấy thông tin người dùng từ Google.")
        else:
            st.error("Lỗi xác thực mã từ Google. Vui lòng thử đăng nhập lại.")
            st.query_params.clear()

    # Giao diện Nút đăng nhập
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    st.markdown(f'''
    <div style="display: flex; justify-content: center; margin-top: 30px;">
        <a href="{url}" target="_top" style="text-decoration: none;">
            <div style="background-color: #4285F4; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; font-family: sans-serif; display: flex; align-items: center; gap: 10px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" width="20" style="background-color: white; padding: 5px; border-radius: 3px;">
                Đăng nhập bằng Google (Chỉ dành cho @ghn.vn)
            </div>
        </a>
    </div>
    ''', unsafe_allow_html=True)
    
    return False

if not require_login():
    st.stop()
    
# Hiển thị email đang đăng nhập trên Sidebar
st.sidebar.success(f"👤 Đăng nhập bởi: {st.session_state.get('user_email', '')}")

@st.cache_data(ttl=600)
def load_data():
    master_file = 'master_data.csv'
    if not os.path.exists(master_file):
        st.error(f"Không tìm thấy file {master_file}. Vui lòng chờ hệ thống tải dữ liệu...")
        return pd.DataFrame()
    
    st.sidebar.info(f"Đang đọc dữ liệu tổng hợp từ: {master_file}")
    df = pd.read_csv(master_file)
    
    dt_columns = ['ThoiGianTao', 'ThoiGianLayThanhCong', 'ThoiGianXuatKienDauTien', 'ThoiGianGiaoThanhCong']
    for col in dt_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
            
    return df

df = load_data()

if df.empty:
    st.stop()

st.title("B2B Delivery Reporting Dashboard")

# --- Global Filters ---
st.sidebar.header("Bộ lọc toàn cục")
clients = st.sidebar.multiselect("Khách hàng", options=df['client_name'].dropna().unique())

df_filtered = df.copy()
if clients:
    df_filtered = df_filtered[df_filtered['client_name'].isin(clients)]

tab1, tab2, tab3 = st.tabs(["1. Sản lượng & Vùng giao", "2. Ontime Xuất Hàng", "3. Giao trong ngày (Concung)"])

# ----------------- TAB 1 -----------------
with tab1:
    st.header("Báo cáo Sản lượng (Đơn tạo & Lấy thành công)")
    
    col1, col2 = st.columns(2)
    with col1:
        time_freq = st.selectbox("Nhóm theo thời gian:", options=['Ngày (D)', 'Tuần (W)', 'Tháng (M)'], index=0)
    
    freq_map = {'Ngày (D)': 'D', 'Tuần (W)': 'W', 'Tháng (M)': 'M'}
    freq = freq_map[time_freq]
    
    df_tao = df_filtered.dropna(subset=['ThoiGianTao']).copy()
    df_lay = df_filtered.dropna(subset=['ThoiGianLayThanhCong']).copy()
    
    def get_period(dt_series, freq):
        if freq == 'D': return dt_series.dt.to_period('D').dt.start_time
        elif freq == 'W': return dt_series.dt.to_period('W').dt.start_time
        elif freq == 'M': return dt_series.dt.to_period('M').dt.start_time

    df_tao['Period'] = get_period(df_tao['ThoiGianTao'], freq)
    df_lay['Period'] = get_period(df_lay['ThoiGianLayThanhCong'], freq)
    
    def get_period_str(dt_series, freq):
        if freq == 'D': return dt_series.dt.strftime('%d/%m/%Y')
        elif freq == 'W': return 'Tuần ' + dt_series.dt.strftime('%W-%Y')
        elif freq == 'M': return 'Tháng ' + dt_series.dt.strftime('%m-%Y')
        
    df_tao['Period_Str'] = get_period_str(df_tao['ThoiGianTao'], freq)
    df_lay['Period_Str'] = get_period_str(df_lay['ThoiGianLayThanhCong'], freq)
    
    weight_col = 'weight' if 'weight' in df.columns else 'KL_TinhCuoc'
    if weight_col not in df.columns:
        df_tao[weight_col] = 0
        df_lay[weight_col] = 0
        
    agg_tao = df_tao.groupby(['Period', 'Period_Str', 'client_name', 'VungGiao', 'TinhGiao']).agg(
        DonTao=('order_code', 'count'),
        CanNangTao=(weight_col, 'sum')
    ).reset_index()
    
    agg_lay = df_lay.groupby(['Period', 'Period_Str', 'client_name', 'VungGiao', 'TinhGiao']).agg(
        DonLayThanhCong=('order_code', 'count'),
        CanNangLay=(weight_col, 'sum')
    ).reset_index()
    
    report1 = pd.merge(agg_tao, agg_lay, on=['Period', 'Period_Str', 'client_name', 'VungGiao', 'TinhGiao'], how='outer').fillna(0)
    
    if not report1.empty:
        sorted_periods = report1[['Period', 'Period_Str']].drop_duplicates().sort_values('Period', ascending=False)['Period_Str'].tolist()
        
        # Nhận xét nhanh cho Khách Hàng
        latest_period = sorted_periods[0] if len(sorted_periods) > 0 else None
        prev_period = sorted_periods[1] if len(sorted_periods) > 1 else None

        st.info("💡 **Nhận xét tình hình Sản Lượng Khách Hàng:**")
        if latest_period:
            latest_tao = report1[report1['Period_Str'] == latest_period]['DonTao'].sum()
            latest_lay = report1[report1['Period_Str'] == latest_period]['DonLayThanhCong'].sum()
            
            if prev_period:
                prev_tao = report1[report1['Period_Str'] == prev_period]['DonTao'].sum()
                diff_tao = latest_tao - prev_tao
                trend = "tăng" if diff_tao >= 0 else "giảm"
                st.markdown(f"- 📈 **Biến động:** Lượng đơn tạo ở {latest_period} đạt **{latest_tao:,.0f}** đơn, **{trend} {abs(diff_tao):,.0f}** đơn so với {prev_period}.")
            else:
                st.markdown(f"- 📈 **Biến động:** Lượng đơn tạo ở {latest_period} đạt **{latest_tao:,.0f}** đơn.")
                
            not_lay = latest_tao - latest_lay
            if not_lay > 0:
                st.markdown(f"- ⚠️ **Đang làm chưa tốt:** Có tới **{not_lay:,.0f}** đơn tạo ở {latest_period} nhưng chưa được lấy thành công.")
            else:
                st.markdown(f"- ✅ **Điểm sáng:** 100% đơn tạo ở {latest_period} đều đã lấy thành công.")
        
        st.subheader("Bảng chi tiết Sản lượng theo Khách Hàng")
        pivot_detail = report1.pivot_table(
            index=['client_name'],
            columns='Period_Str',
            values=['DonTao', 'DonLayThanhCong', 'CanNangLay'],
            aggfunc='sum',
            fill_value=0
        )
        pivot_detail = pivot_detail.swaplevel(0, 1, axis=1)
        pivot_detail = pivot_detail.rename(columns={'DonTao': 'Đơn tạo', 'DonLayThanhCong': 'Đơn lấy thành công', 'CanNangLay': 'Cân nặng (gr)'})
        pivot_detail.index.names = ['Tên khách hàng']
        
        metrics_order = ['Đơn tạo', 'Đơn lấy thành công', 'Cân nặng (gr)']
        new_cols = pd.MultiIndex.from_product([sorted_periods, metrics_order])
        pivot_detail = pivot_detail.reindex(columns=new_cols).fillna(0)
        
        # Thêm hàng tổng cộng ở dưới cùng (dùng .values để tránh lỗi NaN do lệch index)
        pivot_detail.loc['Tổng cộng', :] = pivot_detail.sum(numeric_only=True).values
        
        # Hàm format string để tránh dùng Styler khi bảng lớn
        def format_integer(val):
            return f"{val:,.0f}" if isinstance(val, (int, float)) else val
            
        pivot_detail_formatted = pivot_detail.map(format_integer)
        st.dataframe(pivot_detail_formatted, use_container_width=True)
        
        # Nhận xét nhanh cho Vùng/Tỉnh Giao
        st.info("💡 **Nhận xét tình hình Vùng / Tỉnh Giao:**")
        if latest_period:
            latest_vung = report1[report1['Period_Str'] == latest_period].groupby('VungGiao')[['DonTao', 'DonLayThanhCong']].sum()
            if not latest_vung.empty:
                best_vung_name = latest_vung['DonTao'].idxmax()
                best_vung_val = latest_vung['DonTao'].max()
                
                latest_vung['DonChuaLay'] = latest_vung['DonTao'] - latest_vung['DonLayThanhCong']
                worst_vung_name = latest_vung['DonChuaLay'].idxmax()
                worst_vung_val = latest_vung['DonChuaLay'].max()
                
                st.markdown(f"- 🌟 **Cao nhất:** Vùng **{best_vung_name}** có lượng đơn tạo nhiều nhất ({best_vung_val:,.0f} đơn).")
                if worst_vung_val > 0:
                    st.markdown(f"- ⚠️ **Đang làm chưa tốt:** Vùng **{worst_vung_name}** đang tồn nhiều đơn chưa lấy nhất ({worst_vung_val:,.0f} đơn). Cần đôn đốc xử lý sớm.")
                else:
                    st.markdown(f"- ✅ **Điểm sáng:** Tất cả các vùng đều đã lấy thành công 100% đơn hàng.")

        st.subheader("Bảng tổng hợp theo Vùng / Tỉnh Giao")
        pivot_summary = report1.pivot_table(
            index=['VungGiao', 'TinhGiao'],
            columns='Period_Str',
            values=['DonTao', 'DonLayThanhCong', 'CanNangLay'],
            aggfunc='sum',
            fill_value=0
        )
        pivot_summary = pivot_summary.swaplevel(0, 1, axis=1)
        pivot_summary = pivot_summary.rename(columns={'DonTao': 'Đơn tạo', 'DonLayThanhCong': 'Đơn lấy thành công', 'CanNangLay': 'Cân nặng (gr)'})
        pivot_summary.index.names = ['Vùng Giao', 'Tỉnh Giao']
        pivot_summary = pivot_summary.reindex(columns=new_cols).fillna(0)
        
        # Thêm hàng tổng cộng ở dưới cùng (dùng .values để tránh lỗi NaN do lệch index)
        pivot_summary.loc[('Tổng cộng', ''), :] = pivot_summary.sum(numeric_only=True).values
        
        pivot_summary_formatted = pivot_summary.map(format_integer)
        st.dataframe(pivot_summary_formatted, use_container_width=True)
        
        st.subheader("Biểu đồ Tổng quan Sản Lượng")
        chart_data = report1.groupby(['Period', 'Period_Str'])[['DonTao', 'DonLayThanhCong']].sum().reset_index()
        chart_data = chart_data.sort_values('Period', ascending=True)
        fig = px.bar(
            chart_data, x='Period_Str', y=['DonTao', 'DonLayThanhCong'], barmode='group',
            labels={'value': 'Số lượng', 'Period_Str': 'Thời gian', 'variable': 'Chỉ số', 'DonTao': 'Đơn tạo', 'DonLayThanhCong': 'Đơn lấy thành công'}
        )
        fig.update_xaxes(categoryorder='array', categoryarray=chart_data['Period_Str'].tolist())
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu")

# ----------------- TAB 2 -----------------
with tab2:
    st.header("Báo cáo Ontime Xuất Hàng")
    st.markdown("Quy định: Các đơn lấy thành công **trước 20h ngày N** phải có log xuất kiện đầu tiên **trước 6h sáng ngày N+1**.")
    
    df_ontime = df_filtered.dropna(subset=['ThoiGianLayThanhCong']).copy()
    df_ontime['NgayLay'] = df_ontime['ThoiGianLayThanhCong'].dt.date
    df_ontime['NgayLay_Str'] = pd.to_datetime(df_ontime['NgayLay']).dt.strftime('%d/%m/%Y')
    df_ontime['GioLay'] = df_ontime['ThoiGianLayThanhCong'].dt.hour
    
    df_ontime = df_ontime[df_ontime['GioLay'] < 20]
    df_ontime['DeadlineXuat'] = pd.to_datetime(df_ontime['NgayLay']) + pd.Timedelta(days=1, hours=6)
    
    def check_ontime(row):
        if pd.isna(row['ThoiGianXuatKienDauTien']): return False
        return row['ThoiGianXuatKienDauTien'] <= row['DeadlineXuat']
        
    df_ontime['Is_Ontime'] = df_ontime.apply(check_ontime, axis=1)
    
    ontime_summary = df_ontime.groupby(['NgayLay', 'NgayLay_Str', 'client_name']).agg(
        TongDon=('order_code', 'count'),
        Ontime=('Is_Ontime', 'sum')
    ).reset_index()
    ontime_summary['TyLe_Ontime (%)'] = (ontime_summary['Ontime'] / ontime_summary['TongDon'] * 100).round(2)
    
    if not ontime_summary.empty:
        latest_date = ontime_summary['NgayLay'].max()
        yesterday = latest_date - pd.Timedelta(days=1)
        last_week_day = latest_date - pd.Timedelta(days=7)
        
        latest_data = ontime_summary[ontime_summary['NgayLay'] == latest_date]
        yesterday_data = ontime_summary[ontime_summary['NgayLay'] == yesterday]
        last_week_data = ontime_summary[ontime_summary['NgayLay'] == last_week_day]
        
        def get_ontime_pct(data_df):
            if data_df.empty: return None
            t_on = data_df['Ontime'].sum()
            t_don = data_df['TongDon'].sum()
            return (t_on / t_don * 100) if t_don > 0 else 0
            
        latest_pct = get_ontime_pct(latest_data)
        yest_pct = get_ontime_pct(yesterday_data)
        lw_pct = get_ontime_pct(last_week_data)
        
        st.info("💡 **Nhận xét tình hình Ontime:**")
        if latest_pct is not None:
            comp_yest = f"(tăng {(latest_pct - yest_pct):.1f}% so với hôm qua)" if yest_pct and latest_pct >= yest_pct else (f"(giảm {(yest_pct - latest_pct):.1f}% so với hôm qua)" if yest_pct else "")
            comp_lw = f"(tăng {(latest_pct - lw_pct):.1f}% so với tuần trước)" if lw_pct and latest_pct >= lw_pct else (f"(giảm {(lw_pct - latest_pct):.1f}% so với tuần trước)" if lw_pct else "")
            
            st.markdown(f"- 📈 **Biến động:** Tỷ lệ Ontime tổng ngày {latest_date.strftime('%d/%m/%Y')} đạt **{latest_pct:.1f}%** {comp_yest}. {comp_lw}")
            
            if not latest_data.empty:
                worst_client = latest_data.sort_values('TyLe_Ontime (%)').iloc[0]
                not_ontime = worst_client['TongDon'] - worst_client['Ontime']
                if not_ontime > 0:
                    st.markdown(f"- ⚠️ **Đang làm chưa tốt:** Khách hàng **{worst_client['client_name']}** đang có tỷ lệ Ontime thấp nhất (**{worst_client['TyLe_Ontime (%)']}%**) với {not_ontime:,.0f} đơn trễ.")
                else:
                    st.markdown(f"- ✅ **Điểm sáng:** 100% đơn hàng xuất ontime đúng hạn.")
        
        sorted_days = ontime_summary[['NgayLay', 'NgayLay_Str']].drop_duplicates().sort_values('NgayLay', ascending=False)['NgayLay_Str'].tolist()
        
        pivot_ontime = ontime_summary.pivot_table(
            index='client_name',
            columns='NgayLay_Str',
            values=['Ontime', 'TyLe_Ontime (%)'],
            aggfunc='sum',
            fill_value=0
        )
        pivot_ontime = pivot_ontime.swaplevel(0, 1, axis=1)
        pivot_ontime = pivot_ontime.rename(columns={'Ontime': 'Đơn Ontime', 'TyLe_Ontime (%)': 'Tỷ lệ Ontime (%)'})
        pivot_ontime.index.names = ['Tên khách hàng']
        new_cols_ontime = pd.MultiIndex.from_product([sorted_days, ['Đơn Ontime', 'Tỷ lệ Ontime (%)']])
        pivot_ontime = pivot_ontime.reindex(columns=new_cols_ontime)
        
        def format_ontime_cols(col_name, val):
            if pd.isna(val): return ""
            if 'Tỷ lệ' in str(col_name): return f"{val:.2f}%"
            return f"{val:,.0f}"
            
        pivot_ontime_formatted = pivot_ontime.copy()
        for col in pivot_ontime_formatted.columns:
            pivot_ontime_formatted[col] = pivot_ontime_formatted[col].map(lambda x: format_ontime_cols(col, x))
            
        st.subheader("Bảng chi tiết Số đơn và Tỷ lệ Ontime (%)")
        st.dataframe(pivot_ontime_formatted, use_container_width=True)
        
        st.subheader("Tỷ lệ Ontime Xuất Hàng")
        chart_data_2 = ontime_summary.sort_values('NgayLay', ascending=True)
        fig2 = px.line(
            chart_data_2, x='NgayLay', y='TyLe_Ontime (%)', color='client_name', markers=True,
            labels={'NgayLay': 'Ngày Lấy Hàng', 'TyLe_Ontime (%)': 'Tỷ lệ Ontime (%)', 'client_name': 'Tên khách hàng'}
        )
        fig2.update_layout(xaxis_title="Ngày Lấy Hàng")
        st.plotly_chart(fig2, use_container_width=True)
    
    with st.expander("Xem chi tiết các đơn bị trễ (Late)"):
        late_orders = df_ontime[~df_ontime['Is_Ontime']]
        st.dataframe(late_orders[['order_code', 'client_name', 'ThoiGianLayThanhCong', 'ThoiGianXuatKienDauTien', 'DeadlineXuat']])

# ----------------- TAB 3 -----------------
with tab3:
    st.header("Báo cáo Giao Trong Ngày (Khách hàng Concung)")
    st.markdown("Quy định: Các đơn Concung thuộc Hà Nội, Hưng Yên, Bắc Ninh, Hải Dương phải **Lấy trong ngày** và **Giao trong ngày** tính từ Thời gian Tạo.")
    
    df_concung = df_filtered[df_filtered['client_name'].str.contains('Concung|Con Cưng', case=False, na=False)].copy()
    
    tinh_giao_hop_le = ['Hà Nội', 'Hưng Yên', 'Bắc Ninh', 'Hải Dương']
    df_concung = df_concung[df_concung['TinhGiao'].isin(tinh_giao_hop_le)]
    df_concung = df_concung.dropna(subset=['ThoiGianTao'])
    
    df_concung['NgayTao_Str'] = df_concung['ThoiGianTao'].dt.strftime('%d/%m/%Y')
    df_concung['NgayTao_DT'] = df_concung['ThoiGianTao'].dt.date
    
    def check_lay_trong_ngay(row):
        if pd.isna(row['ThoiGianLayThanhCong']): return False
        return row['ThoiGianLayThanhCong'].date() == row['NgayTao_DT']
        
    def check_giao_trong_ngay(row):
        if pd.isna(row['ThoiGianGiaoThanhCong']): return False
        return row['ThoiGianGiaoThanhCong'].date() == row['NgayTao_DT']
        
    df_concung['LayTrongNgay'] = df_concung.apply(check_lay_trong_ngay, axis=1)
    df_concung['GiaoTrongNgay'] = df_concung.apply(check_giao_trong_ngay, axis=1)
    df_concung['LayVaGiaoTrongNgay'] = df_concung['LayTrongNgay'] & df_concung['GiaoTrongNgay']
    
    concung_summary = df_concung.groupby(['NgayTao_DT', 'NgayTao_Str', 'TinhGiao']).agg(
        TongDonTao=('order_code', 'count'),
        DonLayTrongNgay=('LayTrongNgay', 'sum'),
        DonGiaoTrongNgay=('GiaoTrongNgay', 'sum'),
        DatYeuCau=('LayVaGiaoTrongNgay', 'sum')
    ).reset_index()
    
    if not concung_summary.empty:
        concung_summary['TyLe_DatYeuCau (%)'] = (concung_summary['DatYeuCau'] / concung_summary['TongDonTao'] * 100).round(2)
        concung_summary = concung_summary.sort_values('NgayTao_DT', ascending=False)
        
        latest_date = concung_summary['NgayTao_DT'].max()
        yesterday = latest_date - pd.Timedelta(days=1)
        last_week_day = latest_date - pd.Timedelta(days=7)
        
        latest_data = concung_summary[concung_summary['NgayTao_DT'] == latest_date]
        yesterday_data = concung_summary[concung_summary['NgayTao_DT'] == yesterday]
        last_week_data = concung_summary[concung_summary['NgayTao_DT'] == last_week_day]
        
        def get_concung_pct(data_df):
            if data_df.empty: return None
            t_dat = data_df['DatYeuCau'].sum()
            t_don = data_df['TongDonTao'].sum()
            return (t_dat / t_don * 100) if t_don > 0 else 0
            
        latest_pct = get_concung_pct(latest_data)
        yest_pct = get_concung_pct(yesterday_data)
        lw_pct = get_concung_pct(last_week_data)
        
        st.info("💡 **Nhận xét giao hàng Concung:**")
        if latest_pct is not None:
            comp_yest = f"(tăng {(latest_pct - yest_pct):.1f}% so với hôm qua)" if yest_pct and latest_pct >= yest_pct else (f"(giảm {(yest_pct - latest_pct):.1f}% so với hôm qua)" if yest_pct else "")
            comp_lw = f"(tăng {(latest_pct - lw_pct):.1f}% so với tuần trước)" if lw_pct and latest_pct >= lw_pct else (f"(giảm {(lw_pct - latest_pct):.1f}% so với tuần trước)" if lw_pct else "")
            
            st.markdown(f"- 📈 **Biến động:** Ngày {latest_date.strftime('%d/%m/%Y')}, tỷ lệ đạt yêu cầu là **{latest_pct:.1f}%** {comp_yest}. {comp_lw}")
            
            not_done = latest_data['TongDonTao'].sum() - latest_data['DatYeuCau'].sum()
            if not_done > 0:
                st.markdown(f"- ⚠️ **Đang làm chưa tốt:** Còn **{not_done:,.0f}** đơn chưa đạt chuẩn lấy/giao trong ngày. Cần tập trung xử lý dứt điểm.")
            else:
                st.markdown(f"- ✅ **Điểm sáng:** Tuyệt vời, 100% đơn tạo ngày {latest_date.strftime('%d/%m/%Y')} đã đạt chuẩn lấy và giao trong ngày.")

        st.dataframe(concung_summary.drop(columns=['NgayTao_DT']).rename(columns={
            'NgayTao_Str': 'Ngày Tạo',
            'TinhGiao': 'Tỉnh Giao',
            'TongDonTao': 'Đơn tạo',
            'DonLayTrongNgay': 'Đơn lấy trong ngày',
            'DonGiaoTrongNgay': 'Đơn giao trong ngày',
            'DatYeuCau': 'Đạt yêu cầu',
            'TyLe_DatYeuCau (%)': 'Tỷ lệ đạt (%)'
        }), use_container_width=True)
        
        st.subheader("Đồ thị tình hình xử lý")
        chart_data_concung = concung_summary.groupby(['NgayTao_DT', 'NgayTao_Str'])[['TongDonTao', 'DonLayTrongNgay', 'DonGiaoTrongNgay']].sum().reset_index()
        chart_data_concung = chart_data_concung.sort_values('NgayTao_DT', ascending=True)
        fig3 = px.bar(
            chart_data_concung, x='NgayTao_Str', y=['TongDonTao', 'DonLayTrongNgay', 'DonGiaoTrongNgay'], barmode='group', title="Tình hình Tạo - Lấy - Giao trong ngày",
            labels={'NgayTao_Str': 'Ngày tạo', 'value': 'Số lượng', 'variable': 'Chỉ số', 'TongDonTao': 'Đơn tạo', 'DonLayTrongNgay': 'Đơn lấy trong ngày', 'DonGiaoTrongNgay': 'Đơn giao trong ngày'}
        )
        fig3.update_xaxes(categoryorder='array', categoryarray=chart_data_concung['NgayTao_Str'].tolist())
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Không có dữ liệu đơn Concung tại 4 tỉnh này.")
        
    with st.expander("Chi tiết đơn chưa đạt yêu cầu (chưa lấy hoặc chưa giao trong ngày)"):
        not_delivered = df_concung[~df_concung['LayVaGiaoTrongNgay']]
        st.dataframe(not_delivered[['order_code', 'TinhGiao', 'TrangThaiHienTai', 'ThoiGianTao', 'ThoiGianLayThanhCong', 'ThoiGianGiaoThanhCong']])
