import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import holidays
import io

# 1. 頁面配置
st.set_page_config(page_title="加班費統計系統", layout="wide")
st.title("🕒 雲端加班費統計系統")

# 2. 資料庫設定
DATA_FILE = "overtime_db.csv"
columns = ["日期", "密鑰", "類型", "總時數", "時薪", "A時段(1.33)", "B時段(1.66)", "C時段(2.0)", "總加班費"]

if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=columns).to_csv(DATA_FILE, index=False)

# 3. 側邊欄：身份驗證
st.sidebar.header("🔑 帳號登入")
user_key = st.sidebar.text_input("輸入您的個人密鑰 (Key)", type="password")

if not user_key:
    st.sidebar.warning("👈 請輸入密鑰以存取您的資料。")
    st.stop()

# 讀取資料
all_data = pd.read_csv(DATA_FILE)
all_data["日期"] = pd.to_datetime(all_data["日期"]).dt.date
df = all_data[all_data["密鑰"] == str(user_key)].copy()

# --- 側邊欄：薪資週期篩選 (21號 - 20號) ---
st.sidebar.divider()
today = datetime.now()
period_options = []
for i in range(12):
    d = today - timedelta(days=i*25)
    p_year, p_month = d.year, d.month
    prev_m = (p_month - 2) % 12 + 1
    label = f"{p_year}年 {p_month}月期 ({prev_m:02d}/21 - {p_month:02d}/20)"
    if (p_year, p_month, label) not in period_options:
        period_options.append((p_year, p_month, label))

selected_p = st.sidebar.selectbox("選擇計薪月份", period_options, format_func=lambda x: x[2])
sel_year, sel_month = selected_p[0], selected_p[1]

end_date = datetime(sel_year, sel_month, 20).date()
start_date = (datetime(sel_year, sel_month, 1) - timedelta(days=15)).replace(day=21).date()
filtered_df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)].copy()

# 備份功能
if not df.empty:
    st.sidebar.divider()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 下載我的 Excel 備份", buffer.getvalue(), file_name=f"backup_{user_key}.xlsx")

# 4. 主要介面
col_main, col_stats = st.columns([0.65, 0.35])

with col_main:
    st.subheader("📝 數據登記")
    f_col1, f_col2 = st.columns(2)
    date = f_col1.date_input("加班日期", datetime.now())
    
    tw_holidays = holidays.Taiwan()
    is_weekend = date.weekday() >= 5
    is_pub_holiday = date in tw_holidays
    default_type_idx = 1 if (is_weekend or is_pub_holiday) else 0
    is_holiday = f_col2.selectbox("日期性質", ["平日", "假日 (倍率 2.0)"], index=default_type_idx)
    
    # --- 時間選取區塊 ---
    t_col1, t_col2 = st.columns(2)
    st_time = t_col1.time_input("開始時間", datetime.strptime("17:00", "%H:%M"), step=1800)
    en_time = t_col2.time_input("結束時間", datetime.strptime("19:00", "%H:%M"), step=1800)
    
    # 自動計算時數
    dt1 = datetime.combine(date, st_time)
    dt2 = datetime.combine(date, en_time)
    if dt2 <= dt1: dt2 += timedelta(days=1)
    calc_hours = float((dt2 - dt1).total_seconds() / 3600.0)
    st.info(f"⏱️ 自動計算時數： {calc_hours:.1f} 小時")

    with st.form("overtime_form", clear_on_submit=True):
        f_wage = st.number_input("您的基本時薪", min_value=0, value=218, step=1)
        
        if st.form_submit_button("確認儲存"):
            a_h, b_h, c_h = 0.0, 0.0, 0.0
            if "假日" in is_holiday:
                c_h, type_label = calc_hours, "假日"
            else:
                type_label, a_h = "平日", min(calc_hours, 2.0)
                b_h = max(0.0, calc_hours - 2.0)
            
            total_pay = round((a_h * 1.33 + b_h * 1.66 + c_h * 2.0) * f_wage, 0)
            
            new_entry = pd.DataFrame([[date, user_key, type_label, calc_hours, f_wage, a_h, b_h, c_h, total_pay]], columns=columns)
            all_data = pd.concat([all_data, new_entry], ignore_index=True)
            all_data.to_csv(DATA_FILE, index=False)
            st.success("✅ 已儲存！")
            st.rerun()

    st.divider()
    st.subheader(f"📜 您的明細 ({sel_year}/{sel_month}期)")
    st.dataframe(filtered_df.drop(columns=["密鑰"]), use_container_width=True)

with col_stats:
    st.subheader("📊 週期統計")
    if not filtered_df.empty:
        st.metric("本期應領金額", f"${filtered_df['總加班費'].sum():,.0f}")
        st.metric("本期時數", f"{filtered_df['總時數'].sum():.1f} H")
