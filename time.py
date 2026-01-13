import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time
import holidays
import io

# 1. 頁面配置與美化樣式
st.set_page_config(page_title="加班費助手", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* --- Tabs 分頁美化 --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #f0f2f6;
        padding: 8px 15px 0px 15px;
        border-radius: 15px 15px 0 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 10px 10px 0 0;
        gap: 1px;
        padding: 10px 25px;
        font-weight: 600;
        color: #555;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #ffffff;
        color: #007bff;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #007bff !important;
        border-bottom: 3px solid #007bff !important;
    }

    /* --- 卡片容器樣式 --- */
    .stat-container {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 20px;
    }
    .stat-card {
        flex: 1;
        min-width: 200px;
        padding: 20px;
        border-radius: 15px;
        background: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-left: 5px solid #007bff;
        text-align: left;
    }
    .card-label { font-size: 0.9rem; color: #666; margin-bottom: 5px; }
    .card-value { font-size: 1.6rem; font-weight: bold; color: #31333F; }
    
    .money { border-left-color: #FFD700; }
    .hours { border-left-color: #007bff; }
    .days  { border-left-color: #28a745; }

    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        height: 3em; 
        background-color: #007bff; 
        color: white; 
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料庫設定
DATA_FILE = "overtime_db.csv"
columns = ["日期", "密鑰", "類型", "總時數", "時薪", "A時段(1.33)", "B時段(1.66)", "C時段(2.0)", "總加班費"]

if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=columns).to_csv(DATA_FILE, index=False)

# 3. 側邊欄：帳號與週期管理
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/time-machine.png", width=80)
    st.title("加班管理中心")
    user_key = st.text_input("🔑 個人密鑰", type="password")
    
    if not user_key:
        st.info("請輸入密鑰開始使用")
        st.stop()
    
    st.success(f"已登入")
    
    st.divider()
    today = datetime.now()
    period_options = []
    for i in range(12):
        d = today - timedelta(days=i*25)
        p_year, p_month = d.year, d.month
        prev_m = (p_month - 2) % 12 + 1
        label = f"📅 {p_year}年 {p_month}月期"
        if (p_year, p_month, label) not in period_options:
            period_options.append((p_year, p_month, label))

    selected_p = st.selectbox("切換統計週期", period_options, format_func=lambda x: x[2])
    sel_year, sel_month = selected_p[0], selected_p[1]

# 讀取資料
all_data = pd.read_csv(DATA_FILE)
all_data["日期"] = pd.to_datetime(all_data["日期"]).dt.date
df = all_data[all_data["密鑰"] == str(user_key)].copy()

end_date = datetime(sel_year, sel_month, 20).date()
start_date = (datetime(sel_year, sel_month, 1) - timedelta(days=15)).replace(day=21).date()
filtered_df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)].sort_values("日期", ascending=False)

# 4. 主要分頁介面 (套用美化樣式)
tab1, tab2 = st.tabs(["➕ 新增登記", "📊 數據報表"])

with tab1:
    col_input, col_info = st.columns([1, 1])
    
    with col_input:
        st.subheader("📝 加班明細錄入")
        date = st.date_input("加班日期", datetime.now())
        
        tw_holidays = holidays.Taiwan()
        is_weekend = date.weekday() >= 5
        is_pub_holiday = date in tw_holidays
        default_idx = 1 if (is_weekend or is_pub_holiday) else 0
        is_holiday = st.selectbox("日期性質", ["平日", "假日 (2.0)"], index=default_idx)
        
        t_col1, t_col2 = st.columns(2)
        time_labels = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
        
        st_label = t_col1.selectbox("開始時間", time_labels, index=34) # 預設 17:00
        en_label = t_col2.selectbox("結束時間", time_labels, index=38) # 預設 19:00
        
        st_time = datetime.strptime(st_label, "%H:%M").time()
        en_time = datetime.strptime(en_label, "%H:%M").time()
        
        dt1 = datetime.combine(date, st_time)
        dt2 = datetime.combine(date, en_time)
        if dt2 <= dt1: dt2 += timedelta(days=1)
        calc_hours = float((dt2 - dt1).total_seconds() / 3600.0)
        
        f_wage = st.number_input("您的時薪", value=218, step=1)
        
        if st.button("🚀 確認儲存"):
            a_h = 0.0; b_h = 0.0; c_h = 0.0
            if "假日" in is_holiday:
                c_h, type_label = calc_hours, "假日"
            else:
                type_label, a_h = "平日", min(calc_hours, 2.0)
                b_h = max(0.0, calc_hours - 2.0)
            
            total_pay = round((a_h * 1.33 + b_h * 1.66 + c_h * 2.0) * f_wage, 0)
            new_row = pd.DataFrame([[date, user_key, type_label, calc_hours, f_wage, a_h, b_h, c_h, total_pay]], columns=columns)
            all_data = pd.concat([all_data, new_row], ignore_index=True)
            all_data.to_csv(DATA_FILE, index=False)
            st.toast("資料已儲存！", icon='✅')
            st.rerun()

    with col_info:
        st.subheader("💡 即時預算")
        st.info(f"本次加班：**{calc_hours:.1f}** 小時")
        st.write(f"🔹 1.33時段: {min(calc_hours, 2.0) if '假日' not in is_holiday else 0:.1f} H")
        st.write(f"🔹 1.66時段: {max(0.0, calc_hours - 2.0) if '假日' not in is_holiday else 0:.1f} H")
        st.write(f"🔸 2.0時段: {calc_hours if '假日' in is_holiday else 0:.1f} H")

with tab2:
    total_amt = filtered_df['總加班費'].sum()
    total_hrs = filtered_df['總時數'].sum()
    total_days = len(filtered_df)

    st.markdown(f"""
    <div class="stat-container">
        <div class="stat-card money">
            <div class="card-label">💰 預估應領</div>
            <div class="card-value">${total_amt:,.0f}</div>
        </div>
        <div class="stat-card hours">
            <div class="card-label">⏱️ 累積時數</div>
            <div class="card-value">{total_hrs:.1f} H</div>
        </div>
        <div class="stat-card days">
            <div class="card-label">📅 登記天數</div>
            <div class="card-value">{total_days} 天</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    if not filtered_df.empty:
        col_t, col_b = st.columns([0.7, 0.3])
        col_t.subheader(f"📋 {sel_month}月期 明細")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered_df.drop(columns=["密鑰"]).to_excel(writer, index=False)
        col_b.download_button("📥 匯出 Excel", buffer.getvalue(), file_name=f"report_{sel_month}.xlsx")
        
        st.dataframe(filtered_df.drop(columns=["密鑰"]), use_container_width=True)
        
        st.divider()
        st.subheader("🗑️ 刪除紀錄")
        delete_options = filtered_df.apply(lambda x: f"{x['日期']} ({x['類型']} {x['總時數']}H)", axis=1).tolist()
        to_delete_label = st.selectbox("選擇要刪除的紀錄", delete_options)
        
        if st.button("🚨 確認刪除選中紀錄"):
            selected_date_str = to_delete_label[:10]
            updated_all_data = all_data[~((all_data['密鑰'] == str(user_key)) & (all_data['日期'].astype(str) == selected_date_str))]
            updated_all_data.to_csv(DATA_FILE, index=False)
            st.toast(f"已刪除 {selected_date_str} 的紀錄", icon='🗑️')
            st.rerun()
    else:
        st.info("目前尚無資料。")
