import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 已直接幫您填入如下
# ==========================================
API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 
# ==========================================

# 1. 初始化 AI 模型
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 頁面配置與介面美化
st.set_page_config(page_title="AI 圖片自動出題助手", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    /* 強化圖片上傳框的視覺，讓 iPad 更好操作 */
    .stFileUploader {
        background-color: white;
        padding: 30px;
        border-radius: 20px;
        border: 3px dashed #007bff;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.5em; 
        background-color: #007bff; 
        color: white; 
        font-weight: bold; 
        font-size: 1.1rem;
    }
    .quiz-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
        margin-bottom: 20px; 
        border-left: 8px solid #007bff; 
    }
    .score-box { 
        background-color: #ffffff; 
        padding: 30px; 
        border-radius: 20px; 
        text-align: center; 
        border: 3px solid #28a745; 
        margin-top: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 側邊欄設定
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/test-passed.png", width=80)
    st.title("⚙️ 出題控制台")
    num_questions = st.slider("生成題目數量", 1, 10, 3)
    difficulty = st.select_slider("題目難度", options=["簡單", "普通", "困難"])
    st.divider()
    if st.button("🗑️ 清空目前的題目"):
        if 'quiz_data' in st.session_state:
            del st.session_state.quiz_data
        st.rerun()
    st.info("💡 說明：您可以一次選取多張 iPad 照片，AI 會讀取圖中文字並自動出題。")

# 4. 主要顯示區
st.title("📸 圖片轉考卷：AI 視覺出題系統")
st.write("直接從 iPad 相簿選取多張照片，AI 會自動掃描內容並生成測驗題。")

# --- 圖片上傳區域 (支援多圖) ---
uploaded_files = st.file_uploader(
    "📂 點擊這裡選取或拖入照片 (可選多張)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"✅ 已成功讀取 {len(uploaded_files)} 張圖片")
    
    # 預覽縮圖
    img_cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with img_cols[idx % 5]:
            st.image(file, use_container_width=True)

    if st.button("✨ 開始辨識內容並生成題目"):
        with st.spinner("AI 正在閱讀您的照片並設計題目中..."):
            try:
                # 處理圖片
                image_data = [Image.open(file) for file in uploaded_files]
                
                # 指令
                prompt = f"""
                請閱讀圖片中的所有內容，根據內容生成 {num_questions} 題繁體中文的選擇題。
                題目難易度：{difficulty}。
                請嚴格以 JSON 格式回傳（不要 Markdown 標籤）：
                [
                  {{
                    "question": "題目內容",
                    "options": ["選項1", "選項2", "選項3", "選項4"],
                    "answer": "正確選項文字",
                    "explanation": "解析說明"
                  }}
                ]
                """
                
                # 發送給 Gemini
                response = model.generate_content([prompt] + image_data)
                
                # 清理回傳格式
                raw_json = re.sub(r'```json|```', '', response.text).strip()
                
                st.session_state.quiz_data = json.loads(raw_json)
                st.session_state.user_answers = {}
                st.success("考卷生成成功！")
            except Exception as e:
                st.error(f"錯誤：{e}")

# 5. 測驗顯示區
if 'quiz_data' in st.session_state:
    st.divider()
    st.subheader("📝 您的隨堂測驗")
    
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>第 {i+1} 題：{q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"請選擇答案 (Q{i+1})：", q['options'], key=f"q_{i}")
        
        if st.form_submit_button("🏁 繳交考卷"):
            score = 0
            total = len(st.session_state.quiz_data)
            
            st.subheader("📊 批改結果")
            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers[i] == q['answer']:
                    score += 1
                    st.success(f"✅ 第 {i+1} 題正確")
                else:
                    st.error(f"❌ 第 {i+1} 題錯誤。正確答案：【{q['answer']}】")
                st.info(f"💡 解析：{q['explanation']}")
            
            # 顯示得分卡片
            st.markdown(f"""
            <div class="score-box">
                <h2 style='color: #28a745;'>測驗完成！</h2>
                <p style='font-size: 1.8rem;'>您的最終得分：<b>{score} / {total}</b></p>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
