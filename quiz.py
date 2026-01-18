import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# 1. 頁面配置與介面美化
st.set_page_config(page_title="AI 圖片自動出題助手", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    /* 強化圖片上傳框的視覺 */
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
        padding: 40px; 
        border-radius: 25px; 
        text-align: center; 
        border: 3px solid #28a745; 
        margin-top: 30px; 
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 設定 AI 鑰匙 (請在此貼上您的 API Key)
API_KEY = "這裡貼上你的_API_KEY" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    st.info("💡 說明：您可以一次選取多張 iPad 圖片，AI 會綜合所有圖片內容來出題。")

# 4. 主要顯示區
st.title("📸 圖片轉考卷：AI 視覺出題系統")
st.write("適合 iPad 使用者：直接從相簿選取筆記或課本照片，自動生成測驗題。")

# --- 圖片上傳區域 (支援多圖) ---
uploaded_files = st.file_uploader(
    "📂 點擊這裡選取或拖入照片 (可選多張)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

# 5. 處理圖片與生成邏輯
if uploaded_files:
    st.success(f"已讀取 {len(uploaded_files)} 張圖片")
    
    # 在畫面上顯示圖片縮圖
    img_cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with img_cols[idx % 5]:
            st.image(file, caption=f"圖 {idx+1}", use_container_width=True)

    # 生成按鈕
    if st.button("✨ 開始辨識內容並生成題目"):
        with st.spinner("AI 正在閱讀您的圖片內容並設計題目中..."):
            try:
                # 將所有上傳的圖片轉換為 PIL Image 格式
                image_data = [Image.open(file) for file in uploaded_files]
                
                # 設定給 AI 的指令
                prompt = f"""
                請仔細閱讀並分析這些圖片中的文字、公式與圖表內容。
                根據內容生成 {num_questions} 題繁體中文的選擇題。
                題目難易度請設定為：{difficulty}。
                
                請嚴格以 JSON 格式回傳，不要有任何 Markdown 標籤或其他多餘文字：
                [
                  {{
                    "question": "題目內容",
                    "options": ["選項1", "選項2", "選項3", "選項4"],
                    "answer": "正確選項的完整文字內容",
                    "explanation": "針對該題目的詳細解答與原理說明"
                  }}
                ]
                """
                
                # 發送給 Gemini 進行多模態運算 (文字 + 圖片)
                response = model.generate_content([prompt] + image_data)
                
                # 清理 AI 可能回傳的 Markdown 代碼塊
                raw_json = re.sub(r'```json|```', '', response.text).strip()
                
                # 儲存到 session_state 以防刷新後消失
                st.session_state.quiz_data = json.loads(raw_json)
                st.session_state.user_answers = {}
                st.success("考卷生成成功！")
            except Exception as e:
                st.error(f"抱歉，發生了錯誤。可能是圖片不夠清晰或 API 額度限制。錯誤訊息：{e}")

# 6. 測驗顯示區
if 'quiz_data' in st.session_state:
    st.divider()
    st.subheader("📝 您的個人化隨堂測驗")
    
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            # 顯示題目卡片
            st.markdown(f"""
            <div class="quiz-card">
                <b>第 {i+1} 題：{q['question']}</b>
            </div>
            """, unsafe_allow_html=True)
            
            # 選擇題選項
            st.session_state.user_answers[i] = st.radio(
                f"請選擇正確答案 (Q{i+1})：", 
                q['options'], 
                key=f"q_{i}"
            )
            st.write("") # 增加間隔
            
        submit_btn = st.form_submit_button("🏁 繳交考卷")

    # 7. 批改邏輯
    if submit_btn:
        score = 0
        total = len(st.session_state.quiz_data)
        
        st.subheader("📊 批改報告")
        for i, q in enumerate(st.session_state.quiz_data):
            is_correct = st.session_state.user_answers[i] == q['answer']
            if is_correct:
                score += 1
                st.success(f"✅ 第 {i+1} 題答對了！")
            else:
                st.error(f"❌ 第 {i+1} 題答錯。正確答案是：【{q['answer']}】")
            
            st.info(f"💡 解析：{q['explanation']}")
            st.divider()
        
        # 顯示最終分數
        st.markdown(f"""
        <div class="score-box">
            <h2 style='color: #28a745;'>測驗結束！</h2>
            <p style='font-size: 1.8rem;'>您的總分：<b>{score} / {total}</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.balloons()
