import streamlit as st
import streamlit.components.v1 as components
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

from streamlit_cookies_controller import CookieController
controller = CookieController()

def require_login():
    if "authenticated" not in st.session_state:
        cookie_email = controller.get("ghn_b2b_email")
        if cookie_email:
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = cookie_email
            return True

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
                if email.endswith("@ghn.vn") or email in ALLOWED_EMAILS:
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = email
                    # Lưu cookie trong 30 ngày (86400 * 30 = 2592000 giây)
                    controller.set("ghn_b2b_email", email, max_age=2592000)
                    st.query_params.clear()
                    return True

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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.link_button("🔐 ĐĂNG NHẬP BẰNG GOOGLE", url, use_container_width=True)
        st.caption("Sau khi đăng nhập xong, có thể đóng tab cũ.")
        st.markdown(f"<p style='text-align:center;font-size:12px;'>Nếu nút không hoạt động, <a href='{url}' target='_blank'>bấm vào đây</a></p>", unsafe_allow_html=True)
    return False

if not require_login():
    st.stop()

# ==================== LOAD DATA ====================
@st.cache_data(ttl=600)
def load_data():
    url = st.secrets.get("SHEET_URL", "")
    df = pd.DataFrame()
    source_used = ""
    try:
        if url:
            df = pd.read_csv(url)
            source_used = "Google Sheets"
    except Exception:
        pass
        
    if df.empty:
        local_file = 'data_b2b.xlsx'
        if os.path.exists(local_file):
            try:
                df = pd.read_excel(local_file)
                if len(df.columns) > 0 and str(df.columns[0]).startswith('Unnamed:'):
                    for i in range(min(5, len(df))):
                        if 'NgayNhap' in df.iloc[i].values:
                            df.columns = df.iloc[i]
                            df = df[i+1:].reset_index(drop=True)
                            break
                source_used = local_file
            except Exception as e:
                return pd.DataFrame(), f"Error reading {local_file}: {str(e)}"
        else:
            return pd.DataFrame(), "Không tìm thấy dữ liệu"
            
    if not df.empty:
        dt_columns = ['ThoiGianNhap', 'InsideThoiGianGanNhat', 'NgayNhap']
        for col in dt_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
    return df, source_used

df_raw, master_file_path = load_data()
if df_raw.empty:
    st.error(f"Lỗi tải dữ liệu: {master_file_path}")
    st.stop()

st.title("B2B DELIVERY REPORTING DASHBOARD")

df = df_raw.copy()

# ========== CHỌN THỜI GIAN VÀ BỘ LỌC (TOÀN CỤC) ==========
col1, col2, col3, col4 = st.columns(4)
with col1:
    time_freq = st.selectbox("⏰ NHÓM THEO THỜI GIAN:", options=['Ngày (D)', 'Tuần (W)', 'Tháng (M)'], index=0)
with col2:
    if 'NgayNhap' in df.columns and not df['NgayNhap'].dropna().empty:
        min_date = df['NgayNhap'].dropna().min().date()
        max_date = df['NgayNhap'].dropna().max().date()
    else:
        min_date = (datetime.today() - timedelta(days=30)).date()
        max_date = datetime.today().date()
    date_range = st.date_input("📅 TỪ NGÀY - ĐẾN NGÀY:", value=(min_date, max_date))
with col3:
    user_email = st.session_state.get("user_email", "")
    allowed_khos = ['Tất cả', 'B2B Đài Tư', 'B2B Hưng Yên']
    
    try:
        if "rbac" in st.secrets:
            user_role = st.secrets["rbac"].get(user_email)
            if user_role == "B2B Đài Tư":
                allowed_khos = ['B2B Đài Tư']
            elif user_role == "B2B Hưng Yên":
                allowed_khos = ['B2B Hưng Yên']
    except Exception:
        pass
        
    kho_nhap_filter = st.selectbox("🏭 KHO NHẬP:", options=allowed_khos)
with col4:
    if 'Client_ID' in df.columns:
        clients = st.multiselect("🎯 BỘ LỌC KHÁCH HÀNG:", options=df['Client_ID'].dropna().unique())
    else:
        clients = []

freq_map = {'Ngày (D)': 'D', 'Tuần (W)': 'W', 'Tháng (M)': 'M'}
nperiod_map = {'D': 30, 'W': 6, 'M': 3}
freq = freq_map[time_freq]
n_periods = nperiod_map[freq]

df_filtered = df.copy()

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
    if 'NgayNhap' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['NgayNhap'].dt.date >= start_d) & (df_filtered['NgayNhap'].dt.date <= end_d)]
elif isinstance(date_range, tuple) and len(date_range) == 1:
    start_d = date_range[0]
    if 'NgayNhap' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['NgayNhap'].dt.date >= start_d]

if kho_nhap_filter == 'B2B Đài Tư':
    if 'KhoNhap' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['KhoNhap'].str.contains('Đài Tư', case=False, na=False)]
elif kho_nhap_filter == 'B2B Hưng Yên':
    if 'KhoNhap' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['KhoNhap'].str.contains('Hưng Yên', case=False, na=False)]

if clients and 'Client_ID' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['Client_ID'].isin(clients)]

def get_period(dt_series, f):
    if f == 'D': return dt_series.dt.to_period('D').dt.start_time
    elif f == 'W': return dt_series.dt.to_period('W').dt.start_time
    elif f == 'M': return dt_series.dt.to_period('M').dt.start_time

def get_period_str(dt_series, f):
    if f == 'D': 
        weekday = (dt_series.dt.weekday + 2).astype(str).replace('8', 'CN')
        return dt_series.dt.strftime('%Y-%m-%d') + ' - Thứ ' + weekday
    elif f == 'W': return dt_series.dt.strftime('%Y/%W')
    elif f == 'M': return dt_series.dt.strftime('%Y/%m')

if 'NgayNhap' in df_filtered.columns:
    df_filtered['Period'] = get_period(df_filtered['NgayNhap'], freq)
    df_filtered['Period_Str'] = get_period_str(df_filtered['NgayNhap'], freq)

def display_dataframe(df_to_show):
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. SẢN LƯỢNG NHẬP KHO", "2. ONTIME XUẤT HÀNG", "3. GIAO TRONG NGÀY (CONCUNG)", "4. QUẢN LÝ NETWORK (DB)", "5. PHÂN TÍCH SORT CODE"])

# ==================== TAB 1 ====================
with tab1:
    st.header("BÁO CÁO SẢN LƯỢNG NHẬP KHO")
    
    df_daitu = df_filtered[df_filtered['KhoNhap'].str.contains('Đài Tư', case=False, na=False)] if 'KhoNhap' in df_filtered.columns else pd.DataFrame()
    df_hungyen = df_filtered[df_filtered['KhoNhap'].str.contains('Hưng Yên', case=False, na=False)] if 'KhoNhap' in df_filtered.columns else pd.DataFrame()

    st.markdown("<h3 style='color: #004b8b; text-decoration: underline;'>A. Overview</h3>", unsafe_allow_html=True)
    
    if 'ThoiGianLayThanhCong' in df_filtered.columns and 'ThoiGianTao' in df_filtered.columns:
        df_filtered['Leadtime_Lay_Tao'] = (df_filtered['ThoiGianLayThanhCong'] - df_filtered['ThoiGianTao']).dt.total_seconds() / 3600
        
    if 'NgayNhap' in df_filtered.columns and not df_filtered.empty:
        df_ltc = df_filtered[df_filtered['ThoiGianLayThanhCong'].notna()] if 'ThoiGianLayThanhCong' in df_filtered.columns else df_filtered
        ltc_counts = df_ltc.groupby('Period_Str')['MaDonGoc'].nunique() if 'MaDonGoc' in df_ltc.columns else df_ltc.groupby('Period_Str').size()
        kg_sums = df_filtered.groupby('Period_Str')['KhoiLuongKG'].sum() if 'KhoiLuongKG' in df_filtered.columns else pd.Series(dtype=float)
        leadtime_means = df_filtered.groupby('Period_Str')['Leadtime_Lay_Tao'].mean() if 'Leadtime_Lay_Tao' in df_filtered.columns else pd.Series(dtype=float)
        
        overview_group = pd.DataFrame({
            'Tổng đơn LTC': ltc_counts,
            'Tổng khối lượng (KG)': kg_sums,
            'Leadtime Lấy - Tạo (hour)': leadtime_means
        }).fillna(0)
        
        period_map = df_filtered.set_index('Period_Str')['Period'].to_dict()
        overview_group['Period'] = overview_group.index.map(period_map)
        overview_group = overview_group.sort_values('Period', ascending=False).drop(columns=['Period']).head(15).T
        overview_group.index.name = 'Thời gian'
        
        for col in overview_group.columns:
            overview_group[col] = [
                f"{overview_group.loc['Tổng đơn LTC', col]:,.0f}".replace(',', '.'),
                f"{overview_group.loc['Tổng khối lượng (KG)', col]:,.0f}".replace(',', '.'),
                f"{overview_group.loc['Leadtime Lấy - Tạo (hour)', col]:,.2f}".replace('.', ',')
            ]
            
        st.dataframe(overview_group, use_container_width=True)
    else:
        st.info("Không có dữ liệu tổng quan.")
    
    metric_view = st.radio("Hiển thị biểu đồ theo:", ["Số đơn", "Khối lượng (kg)"], horizontal=True)
    
    sub1, sub2, sub3 = st.tabs(['📊 Tổng hợp', '🏭 B2B Đài Tư', '🏭 B2B Hưng Yên'])
    
    with sub1:
        if 'NgayNhap' in df_filtered.columns:
            df_chart1 = df_filtered.copy()
            df_chart1['Ngày'] = df_chart1['Period_Str']
            
            if 'KhoNhap' in df_chart1.columns:
                grouped_date_kho = df_chart1.groupby(['Period', 'Ngày', 'KhoNhap']).agg(Số_đơn=('MaDonGoc', 'nunique'), Tổng_KG=('KhoiLuongKG', 'sum')).reset_index()
                grouped_date_kho['Kho'] = grouped_date_kho['KhoNhap'].apply(lambda x: 'Đài Tư' if 'Đài Tư' in str(x) else ('Hưng Yên' if 'Hưng Yên' in str(x) else 'Khác'))
                grouped_date_kho = grouped_date_kho[grouped_date_kho['Kho'].isin(['Đài Tư', 'Hưng Yên'])]
                grouped_date_kho = grouped_date_kho.groupby(['Period', 'Ngày', 'Kho']).agg({'Số_đơn': 'sum', 'Tổng_KG': 'sum'}).reset_index().sort_values('Period')
                
                if not grouped_date_kho.empty:
                    y_col = 'Số_đơn' if metric_view == 'Số đơn' else 'Tổng_KG'
                    title = "Số đơn nhập theo thời gian" if metric_view == 'Số đơn' else "Khối lượng nhập theo thời gian"
                    fig1 = px.line(grouped_date_kho, x='Ngày', y=y_col, color='Kho', markers=True, title=title, custom_data=['Số_đơn', 'Tổng_KG'])
                    fig1.update_xaxes(categoryorder='array', categoryarray=grouped_date_kho['Ngày'].unique())
                    fig1.update_traces(hovertemplate="%{fullData.name}<br>%{x}<br>%{customdata[0]:,.0f} đơn - %{customdata[1]:,.0f} kg")
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.info("Không có dữ liệu cho biểu đồ số đơn nhập theo thời gian.")
                    
            if 'NguonNhap' in df_chart1.columns:
                grouped_nguon = df_chart1.groupby(['Period', 'Ngày', 'NguonNhap']).agg(Số_đơn=('MaDonGoc', 'nunique'), Tổng_KG=('KhoiLuongKG', 'sum')).reset_index().sort_values('Period')
                if not grouped_nguon.empty:
                    y_col = 'Số_đơn' if metric_view == 'Số đơn' else 'Tổng_KG'
                    fig2 = px.bar(grouped_nguon, x='Ngày', y=y_col, color='NguonNhap', barmode='stack', title="Nguồn nhập theo thời gian", labels={'NguonNhap': ''}, custom_data=['Số_đơn', 'Tổng_KG'])
                    fig2.update_xaxes(categoryorder='array', categoryarray=grouped_nguon['Ngày'].unique())
                    fig2.update_traces(hovertemplate="%{fullData.name}<br>%{x}<br>%{customdata[0]:,.0f} đơn - %{customdata[1]:,.0f} kg")
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Không có dữ liệu cho biểu đồ nguồn nhập.")
                    
    def render_warehouse_tab(df_wh, wh_name):
        st.subheader(f"CHI TIẾT KHO {wh_name}")
        if df_wh.empty:
            st.info(f"Không có dữ liệu cho kho {wh_name}")
            return
            
        total_don = df_wh['MaDonGoc'].nunique() if 'MaDonGoc' in df_wh.columns else len(df_wh)
        total_kg = df_wh['KhoiLuongKG'].sum() if 'KhoiLuongKG' in df_wh.columns else 0
        
        df_tulay = df_wh[df_wh['NguonNhap'].str.contains('Tự kho lấy', case=False, na=False)] if 'NguonNhap' in df_wh.columns else pd.DataFrame()
        tu_lay_don = df_tulay['MaDonGoc'].nunique() if 'MaDonGoc' in df_tulay.columns else len(df_tulay)
        tu_lay_kg = df_tulay['KhoiLuongKG'].sum() if 'KhoiLuongKG' in df_tulay.columns else 0
        
        df_khac = df_wh[df_wh['NguonNhap'].str.contains('Nhập từ kho khác', case=False, na=False)] if 'NguonNhap' in df_wh.columns else pd.DataFrame()
        khac_don = df_khac['MaDonGoc'].nunique() if 'MaDonGoc' in df_khac.columns else len(df_khac)
        khac_kg = df_khac['KhoiLuongKG'].sum() if 'KhoiLuongKG' in df_khac.columns else 0
        
        c1, c2, c3 = st.columns(3)
        if metric_view == 'Số đơn':
            c1.metric("Tổng nhập", f"{total_don:,.0f} đơn")
            c2.metric("Tự lấy", f"{tu_lay_don:,.0f} đơn")
            c3.metric("Nhập từ kho khác", f"{khac_don:,.0f} đơn")
        else:
            c1.metric("Tổng nhập", f"{total_kg:,.0f} kg")
            c2.metric("Tự lấy", f"{tu_lay_kg:,.0f} kg")
            c3.metric("Nhập từ kho khác", f"{khac_kg:,.0f} kg")
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            if 'NguonNhap' in df_wh.columns:
                pie_data = df_wh.groupby('NguonNhap').agg(Số_đơn=('MaDonGoc', 'nunique'), Tổng_KG=('KhoiLuongKG', 'sum')).reset_index()
                pie_data.columns = ['Nguồn nhập', 'Số đơn', 'Tổng KG']
                pie_data = pie_data.fillna(0)
                if not pie_data.empty:
                    pie_data['hover_text'] = pie_data.apply(lambda r: f"{r['Số đơn']:,.0f} đơn - {r['Tổng KG']:,.0f} kg", axis=1)
                    val_col = 'Số đơn' if metric_view == 'Số đơn' else 'Tổng KG'
                    fig_pie = px.pie(pie_data, values=val_col, names='Nguồn nhập', title="Tỷ lệ nguồn nhập", custom_data=['hover_text'])
                    fig_pie.update_traces(hovertemplate="%{label}<br>%{customdata[0]}")
                    st.plotly_chart(fig_pie, use_container_width=True)
        with col_chart2:
            if 'TinhGiao' in df_wh.columns and 'KhoiLuongKG' in df_wh.columns:
                val_col_tinh = 'Số_đơn' if metric_view == 'Số đơn' else 'Tổng_KG'
                top_tinh = df_wh.groupby('TinhGiao').agg(Số_đơn=('MaDonGoc', 'nunique'), Tổng_KG=('KhoiLuongKG', 'sum')).nlargest(15, val_col_tinh).reset_index()
                top_tinh.columns = ['Tỉnh giao', 'Số đơn', 'Tổng KG']
                top_tinh = top_tinh.fillna(0)
                if not top_tinh.empty:
                    top_tinh['hover_text'] = top_tinh.apply(lambda r: f"{r['Số đơn']:,.0f} đơn - {r['Tổng KG']:,.0f} kg", axis=1)
                    y_col_tinh = 'Số đơn' if metric_view == 'Số đơn' else 'Tổng KG'
                    fig_bar = px.bar(top_tinh, x='Tỉnh giao', y=y_col_tinh, title="Top 15 Tỉnh giao", custom_data=['hover_text'])
                    fig_bar.update_traces(hovertemplate="%{x}<br>%{customdata[0]}")
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
        col_tbl1, col_tbl2 = st.columns(2)
        with col_tbl1:
            st.markdown("**Chi tiết theo Client_ID**")
            if 'Client_ID' in df_wh.columns and 'KhoiLuongKG' in df_wh.columns and 'MaDonGoc' in df_wh.columns:
                tbl_client = df_wh.groupby('Client_ID').agg(
                    Số_đơn=('MaDonGoc', 'nunique'),
                    Tổng_KG=('KhoiLuongKG', 'sum')
                ).reset_index().sort_values('Số_đơn', ascending=False)
                st.dataframe(tbl_client.style.format({'Tổng_KG': '{:,.0f}'}), use_container_width=True)
                
        with col_tbl2:
            st.markdown("**Chi tiết theo Tỉnh giao**")
            if 'TinhGiao' in df_wh.columns and 'KhoiLuongKG' in df_wh.columns and 'MaDonGoc' in df_wh.columns:
                tbl_tinh = df_wh.groupby('TinhGiao').agg(
                    Số_đơn=('MaDonGoc', 'nunique'),
                    Tổng_KG=('KhoiLuongKG', 'sum')
                ).reset_index().sort_values('Số_đơn', ascending=False)
                st.dataframe(tbl_tinh.style.format({'Tổng_KG': '{:,.0f}'}), use_container_width=True)

    with sub2:
        render_warehouse_tab(df_daitu, "B2B ĐÀI TƯ")
        
    with sub3:
        render_warehouse_tab(df_hungyen, "B2B HƯNG YÊN")

# ==================== TAB 2 ====================
with tab2:
    st.header("BÁO CÁO ONTIME XUẤT HÀNG")
    
    import numpy as np
    df_ot = df_filtered.copy()
    if 'NgayNhap' in df_ot.columns:
        today_date = pd.to_datetime('today').normalize()
        df_ot = df_ot[pd.to_datetime(df_ot['NgayNhap']).dt.normalize() < today_date]
        
    if 'KhoGiao' in df_ot.columns:
        df_ot = df_ot[~df_ot['KhoGiao'].fillna('').str.contains('Đài Tư', case=False)]
    
    # Loại bỏ đơn có KhoLay = KhoGiao (đơn giao tại chính kho lấy)
    if 'KhoLay_ID' in df_ot.columns and 'KhoGiao_ID' in df_ot.columns:
        df_ot = df_ot[df_ot['KhoLay_ID'] != df_ot['KhoGiao_ID']]
        
    if not df_ot.empty and 'ThoiGianNhap' in df_ot.columns and 'KhoNhap_ID' in df_ot.columns and 'KhoHienTai_ID' in df_ot.columns and 'TrangThaiViTriInside' in df_ot.columns and 'InsideThaoTacGanNhat' in df_ot.columns and 'InsideThoiGianGanNhat' in df_ot.columns:
        df_ot['GioNhap'] = df_ot['ThoiGianNhap'].dt.hour
        base_date = pd.to_datetime(df_ot['NgayNhap']).dt.normalize()
        
        df_ot['DeadlineXuat'] = np.where(
            df_ot['GioNhap'] < 20,
            base_date + pd.Timedelta(days=1, hours=6),
            base_date + pd.Timedelta(days=1, hours=20)
        )
        
        is_exported = (df_ot['KhoHienTai_ID'] != df_ot['KhoNhap_ID']) | (df_ot['TrangThaiViTriInside'] == 'Đã xuất khỏi kho thao tác gần nhất')
        df_ot['DaXuat'] = is_exported
        
        export_time = np.where(
            df_ot['InsideThaoTacGanNhat'] == 'export',
            df_ot['InsideThoiGianGanNhat'],
            df_ot['InsideThoiGianGanNhat']
        )
        df_ot['ThoiGianXuat'] = pd.to_datetime(export_time)
        
        df_ot['Ontime'] = df_ot['DaXuat'] & (df_ot['ThoiGianXuat'] <= df_ot['DeadlineXuat'])
        
        total_ot = len(df_ot)
        ontime_count = df_ot['Ontime'].sum()
        ontime_rate = (ontime_count / total_ot * 100) if total_ot > 0 else 0
        
        df_ot_dt = df_ot[df_ot['KhoNhap'].str.contains('Đài Tư', case=False, na=False)] if 'KhoNhap' in df_ot.columns else pd.DataFrame()
        dt_ot = len(df_ot_dt)
        dt_ontime_count = df_ot_dt['Ontime'].sum() if dt_ot > 0 else 0
        dt_rate = (dt_ontime_count / dt_ot * 100) if dt_ot > 0 else 0
        
        df_ot_hy = df_ot[df_ot['KhoNhap'].str.contains('Hưng Yên', case=False, na=False)] if 'KhoNhap' in df_ot.columns else pd.DataFrame()
        hy_ot = len(df_ot_hy)
        hy_ontime_count = df_ot_hy['Ontime'].sum() if hy_ot > 0 else 0
        hy_rate = (hy_ontime_count / hy_ot * 100) if hy_ot > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng Ontime Rate", f"{ontime_rate:.1f}%", f"{ontime_count:,.0f}/{total_ot:,.0f} đơn")
        m2.metric("Đài Tư Ontime Rate", f"{dt_rate:.1f}%", f"{dt_ontime_count:,.0f}/{dt_ot:,.0f} đơn")
        m3.metric("Hưng Yên Ontime Rate", f"{hy_rate:.1f}%", f"{hy_ontime_count:,.0f}/{hy_ot:,.0f} đơn")
        
        sub1, sub2, sub3 = st.tabs(['📊 Tổng hợp', '🏭 B2B Đài Tư', '🏭 B2B Hưng Yên'])
        
        with sub1:
            df_ot['Ngày'] = df_ot['Period_Str']
            
            if 'KhoNhap' in df_ot.columns:
                df_ot['Kho'] = df_ot['KhoNhap'].apply(lambda x: 'Đài Tư' if 'Đài Tư' in str(x) else ('Hưng Yên' if 'Hưng Yên' in str(x) else 'Khác'))
                grouped_ot = df_ot[df_ot['Kho'].isin(['Đài Tư', 'Hưng Yên'])].groupby(['Period', 'Ngày', 'Kho']).agg(
                    Tong=('NgayNhap', 'size'),
                    Ontime=('Ontime', 'sum')
                ).reset_index().sort_values('Period')
                grouped_ot['Rate'] = (grouped_ot['Ontime'] / grouped_ot['Tong'] * 100).round(1)
                
                if not grouped_ot.empty:
                    fig_ot = px.line(grouped_ot, x='Ngày', y='Rate', color='Kho', markers=True, title="Tỷ lệ Ontime xuất hàng theo thời gian")
                    fig_ot.update_xaxes(categoryorder='array', categoryarray=grouped_ot['Ngày'].unique())
                    st.plotly_chart(fig_ot, use_container_width=True)
                    
            summary_table = df_ot.groupby('Ngày').agg(
                Tổng_đơn=('NgayNhap', 'size'),
                Đã_xuất=('DaXuat', 'sum'),
                Ontime=('Ontime', 'sum')
            ).reset_index()
            summary_table['Tỷ_lệ_Ontime'] = (summary_table['Ontime'] / summary_table['Tổng_đơn'] * 100).round(1)
            st.dataframe(summary_table.style.format({'Tỷ_lệ_Ontime': '{:.1f}%'}), use_container_width=True)
            
        def render_ontime_wh(df_wh_ot, name):
            if df_wh_ot.empty:
                st.info(f"Không có dữ liệu ontime cho {name}")
                return
                
            t_don = len(df_wh_ot)
            t_on = df_wh_ot['Ontime'].sum()
            t_rate = (t_on / t_don * 100) if t_don > 0 else 0
            
            st.markdown(f"**Tỷ lệ Ontime {name}: {t_rate:.1f}%** ({t_on}/{t_don} đơn)")
            
            df_wh_ot['Ngày'] = df_wh_ot['Period_Str']
            chart_data = df_wh_ot.groupby(['Period', 'Ngày']).agg(
                Ontime=('Ontime', 'sum'),
                Late=('Ontime', lambda x: (~x).sum())
            ).reset_index().sort_values('Period')
            
            if not chart_data.empty:
                fig_bar = px.bar(chart_data, x='Ngày', y=['Ontime', 'Late'], title=f"Ontime vs Late - {name}", barmode='group')
                fig_bar.update_xaxes(categoryorder='array', categoryarray=chart_data['Ngày'].unique())
                st.plotly_chart(fig_bar, use_container_width=True)
                
            cols_show = ['NgayNhap', 'MaDonGoc', 'ThoiGianNhap', 'DeadlineXuat', 'DaXuat', 'ThoiGianXuat', 'Ontime']
            cols_show = [c for c in cols_show if c in df_wh_ot.columns]
            st.dataframe(df_wh_ot[cols_show].sort_values('NgayNhap', ascending=False), use_container_width=True)
            
        with sub2:
            render_ontime_wh(df_ot_dt, "B2B ĐÀI TƯ")
        with sub3:
            render_ontime_wh(df_ot_hy, "B2B HƯNG YÊN")
            
        with st.expander("❌ XEM CHI TIẾT ĐƠN XUẤT LATE (CHƯA XUẤT HOẶC XUẤT TRỄ)"):
            late_orders = df_ot[~df_ot['Ontime']].copy()
            if not late_orders.empty:
                cols_late = ['NgayNhap', 'KhoNhap', 'MaDonGoc', 'ThoiGianNhap', 'DeadlineXuat', 'DaXuat', 'ThoiGianXuat']
                cols_late = [c for c in cols_late if c in late_orders.columns]
                st.dataframe(late_orders[cols_late].sort_values('NgayNhap', ascending=False), use_container_width=True)
            else:
                st.success("Tuyệt vời! Không có đơn nào xuất trễ.")
    else:
        st.info("Không đủ dữ liệu hoặc thiếu cột cần thiết để tính Ontime.")


# ==================== TAB 3 ====================
with tab3:
    st.header("BÁO CÁO GIAO TRONG NGÀY - SAMEDAY (CONCUNG)")
    st.markdown("Quy định: Đơn Concung **lấy thành công** tại HN, Bắc Ninh, Hải Dương, Hưng Yên phải **giao thành công trong cùng ngày lấy**.")

    client_name_col = next((c for c in df_filtered.columns if c.lower() == 'client_name'), None)
    if client_name_col:
        df_concung = df_filtered[df_filtered[client_name_col].str.contains('Concung|Con Cưng', case=False, na=False)].copy()
    else:
        df_concung = pd.DataFrame()
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

    try:
        init_cloud_db()
    except Exception as db_init_err:
        st.warning(f"⚠️ Không thể kết nối Cloud DB (có thể project Supabase đang tạm dừng). Đang dùng Local SQLite fallback. Lỗi: {db_init_err}")
        DATABASE_URL = ""  # Fallback về SQLite

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

    # --- BẢNG 1: TỈNH THÀNH ---
    st.subheader("1. Bản Đồ Phân Bổ Tỉnh Thành")
    df_prov_db = load_db_data('provinces_mapping')
    if not df_prov_db.empty:
        # Ẩn cột id, đổi tên cột
        df_prov_display = df_prov_db.drop(columns=['id'], errors='ignore')
        col_rename_prov = {'province': 'Tỉnh', 'level1_code': 'Mã chữ', 'level2_code': 'Mã số', 'fixed_route': 'Mã tuyến cố định'}
        df_prov_display = df_prov_display.rename(columns=col_rename_prov)
        prov_height = (len(df_prov_display) + 1) * 35 + 3
        
        if st.session_state.get("user_email") in ADMIN_EMAILS:
            edited_prov = st.data_editor(df_prov_display, num_rows="dynamic", key="editor_prov", use_container_width=True, height=prov_height)
            if st.button("💾 Lưu Bản Đồ Tỉnh Thành"):
                col_reverse_prov = {v: k for k, v in col_rename_prov.items()}
                save_db_data(edited_prov.rename(columns=col_reverse_prov), 'provinces_mapping')
        else:
            st.dataframe(df_prov_display, use_container_width=True, height=prov_height)
    else:
        st.info("Chưa có dữ liệu. Hãy thêm dữ liệu nếu bạn là Admin.")
            
    # --- BẢNG 2: LỊCH TRÌNH THEO CUNG GIỜ ---
    st.subheader("2. Lịch Trình Xuất Bến Theo Cung Giờ")
    df_routes_db = load_db_data('routes_schedule')
    if not df_routes_db.empty:
        import math
        df_r = df_routes_db.copy()
        df_r['hour'] = df_r['departure_time'].apply(lambda x: int(str(x).split(':')[0]) if pd.notna(x) and ':' in str(x) else -1)
        df_r = df_r[df_r['hour'] >= 0]
        
        time_slots = []
        for h in range(24):
            h_next = (h + 1) % 24
            slot_label = f"{h:02d}:00 - {h_next:02d}:00"
            hy_routes = sorted(df_r[(df_r['hour'] == h) & (df_r['hub'] == 'HY')]['route_code'].unique().tolist())
            hn_routes = sorted(df_r[(df_r['hour'] == h) & (df_r['hub'] == 'HN')]['route_code'].unique().tolist())
            if hy_routes or hn_routes:
                time_slots.append({
                    'Cung Giờ': slot_label,
                    'KTC Hưng Yên (HY01)': '\n'.join(hy_routes) if hy_routes else '-',
                    'KTC Đài Tư (HN02)': '\n'.join(hn_routes) if hn_routes else '-'
                })
        
        df_schedule = pd.DataFrame(time_slots)
        if not df_schedule.empty:
            # Hiển thị bằng markdown table để nhìn hết nội dung
            md_table = "| Cung Giờ | KTC Hưng Yên (HY01) | KTC Đài Tư (HN02) |\n|---|---|---|\n"
            for _, row in df_schedule.iterrows():
                hy_cell = row['KTC Hưng Yên (HY01)'].replace('\n', '<br>')
                hn_cell = row['KTC Đài Tư (HN02)'].replace('\n', '<br>')
                md_table += f"| **{row['Cung Giờ']}** | {hy_cell} | {hn_cell} |\n"
            st.markdown(md_table, unsafe_allow_html=True)
        else:
            st.info("Không có dữ liệu lịch trình.")
        
        # Expander cho bảng raw data (admin edit)
        if st.session_state.get("user_email") in ADMIN_EMAILS:
            with st.expander("⚙️ Chỉnh sửa dữ liệu gốc (Raw Data)", expanded=False):
                df_routes_display = df_routes_db.drop(columns=['id'], errors='ignore')
                df_routes_display = df_routes_display.rename(columns={'route_code': 'Mã tuyến', 'hub': 'KTC', 'departure_time': 'Giờ xuất bến'})
                routes_height = (len(df_routes_display) + 1) * 35 + 3
                edited_routes = st.data_editor(df_routes_display, num_rows="dynamic", key="editor_routes", use_container_width=True, height=min(routes_height, 1500))
                if st.button("💾 Lưu Lịch Trình"):
                    col_reverse_routes = {'Mã tuyến': 'route_code', 'KTC': 'hub', 'Giờ xuất bến': 'departure_time'}
                    save_db_data(edited_routes.rename(columns=col_reverse_routes), 'routes_schedule')
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
