import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import holidays
import io

st.set_page_config(page_title="加班費統計系統", layout="wide")
st.title("🕒 雲端加班費統計系統")

# 在雲端環境中，我們使用本地 CSV 暫存
DATA_FILE = "overtime_db.csv"
columns = ["日期", "密鑰", "類型", "總時數", "時薪", "A時段(1.33)", "B時段(1.66)", "C時段(2.0)", "總加班費"]

if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=columns).to_csv(DATA_FILE, index=False)

# 身份驗證
st.sidebar.header("🔑 帳號登入")
user_key = st.sidebar.text_input("輸入您的個人密鑰 (Key)", type="password")

if not user_key:
    st.warning("👈 請輸入密鑰以存取您的資料。")
    st.stop()

# 讀取與過濾
all_data = pd.read_csv(DATA_FILE)
all_data["日期"] = pd.to_datetime(all_data["日期"]).dt.date
df = all_data[all_data["密鑰"] == str(user_key)].copy()

# 下載備份按鈕
if not df.empty:
    st.sidebar.divider()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 下載我的 Excel 存檔", buffer.getvalue(), file_name=f"backup_{user_key}.xlsx")

# ... (其餘登記與統計邏輯與之前相同)