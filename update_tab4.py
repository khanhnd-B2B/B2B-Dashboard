import sys

with open(r'd:\LophocAI\quanlyB2B\app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_mode = False

for line in lines:
    if 'tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs' in line:
        new_lines.append('tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. ĐƠN LẤY & VÙNG GIAO", "2. ONTIME XUẤT HÀNG", "3. GIAO TRONG NGÀY (CONCUNG)", "4. QUẢN LÝ NETWORK (DB)", "5. PHÂN TÍCH SORT CODE"])\n')
        continue
    
    if '# ==================== TAB 4 ====================' in line:
        skip_mode = True
        new_lines.append('# ==================== TAB 4 ====================\n')
        new_lines.append('with tab4:\n')
        new_lines.append('    st.header("QUẢN LÝ NETWORK B2B (DATABASE)")\n')
        new_lines.append('    st.markdown("Thay đổi dữ liệu tại đây sẽ cập nhật trực tiếp vào cơ sở dữ liệu hệ thống.")\n')
        new_lines.append('    \n')
        new_lines.append('    import sqlite3\n')
        new_lines.append("    db_path = r'd:\\LophocAI\\quanlyB2B\\b2b_network.db'\n")
        new_lines.append('    \n')
        new_lines.append('    def load_db_data(table_name):\n')
        new_lines.append('        try:\n')
        new_lines.append('            conn = sqlite3.connect(db_path)\n')
        new_lines.append('            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)\n')
        new_lines.append('            conn.close()\n')
        new_lines.append('            return df\n')
        new_lines.append('        except Exception as e:\n')
        new_lines.append('            st.error(f"Lỗi kết nối DB: {e}")\n')
        new_lines.append('            return pd.DataFrame()\n')
        new_lines.append('            \n')
        new_lines.append('    def save_db_data(df, table_name):\n')
        new_lines.append('        try:\n')
        new_lines.append('            conn = sqlite3.connect(db_path)\n')
        new_lines.append('            cursor = conn.cursor()\n')
        new_lines.append('            cursor.execute(f"DELETE FROM {table_name}")\n')
        new_lines.append("            if 'id' in df.columns:\n")
        new_lines.append("                df = df.drop(columns=['id'])\n")
        new_lines.append("            df.to_sql(table_name, conn, if_exists='append', index=False)\n")
        new_lines.append('            conn.commit()\n')
        new_lines.append('            conn.close()\n')
        new_lines.append('            st.success(f"Đã lưu thay đổi vào bảng {table_name}!")\n')
        new_lines.append('        except Exception as e:\n')
        new_lines.append('            st.error(f"Lỗi khi lưu DB: {e}")\n')
        new_lines.append('\n')
        new_lines.append('    st.subheader("1. Bản Đồ Phân Bổ Tỉnh Thành")\n')
        new_lines.append("    df_prov_db = load_db_data('provinces_mapping')\n")
        new_lines.append('    if not df_prov_db.empty:\n')
        new_lines.append('        edited_prov = st.data_editor(df_prov_db, num_rows="dynamic", key="editor_prov", use_container_width=True)\n')
        new_lines.append('        if st.button("💾 Lưu Bản Đồ Tỉnh Thành"):\n')
        new_lines.append("            save_db_data(edited_prov, 'provinces_mapping')\n")
        new_lines.append('            \n')
        new_lines.append('    st.subheader("2. Lịch Trình Xuất Bến (KTC Hưng Yên & Đài Tư)")\n')
        new_lines.append("    df_routes_db = load_db_data('routes_schedule')\n")
        new_lines.append('    if not df_routes_db.empty:\n')
        new_lines.append('        edited_routes = st.data_editor(df_routes_db, num_rows="dynamic", key="editor_routes", use_container_width=True)\n')
        new_lines.append('        if st.button("💾 Lưu Lịch Trình"):\n')
        new_lines.append("            save_db_data(edited_routes, 'routes_schedule')\n")
        continue

    if skip_mode and '# ==================== TAB 5 ====================' in line:
        skip_mode = False

    if not skip_mode:
        if '# ==================== TAB 6 ====================' in line:
            break
        new_lines.append(line)

new_lines.append('\n# Di chuyển thông tin sidebar xuống dưới cùng\n')
new_lines.append('st.sidebar.markdown("---")\n')
new_lines.append('st.sidebar.info(f"Đang đọc dữ liệu từ:\\n\\n`{master_file_path}`")\n')
new_lines.append('st.sidebar.success(f"👤 Đăng nhập bởi:\\n\\n{st.session_state.get(\'user_email\', \'\')}")\n')

with open(r'd:\LophocAI\quanlyB2B\app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Updated app.py successfully!")
