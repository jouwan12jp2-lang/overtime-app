import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# 1. 頁面配置與美化樣式
st.set_page_config(page_title="AI 圖片自動出題助手", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; }
    .quiz-card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 6px solid #007bff; }
    .score-box { background-color: #ffffff; padding: 30px; border-radius: 20px; text-align: center; border: 2px solid #28a745; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 設定 AI 鑰匙 (請確認這裡有填入你的 KEY)
API_KEY = "這裡貼上你的_API_KEY" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 側邊欄設定
with st.sidebar:
    st.title("⚙️ 出題設定")
    num_questions = st.slider("生成題目數量", 1, 10, 3)
    difficulty = st.select_slider("難易度", options=["簡單", "普通", "困難"])
    st.divider()
    if st.button("🗑️ 清空所有題目"):
        if 'quiz_data' in st.session_state:
            del st.session_state.quiz_data
        st.rerun()

# 4. 主要介面
st.title("📸 圖片轉考卷系統")
st.write("上傳 iPad 照片或筆記截圖，AI 將自動辨識內容並出題。")

# --- 圖片上傳區 ---
uploaded_files = st.file_uploader("📂 請選擇照片 (可一次選多張)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    # 在網頁上預覽圖片
    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        with cols[idx % 4]:
            st.image(file, caption=f"圖片 {idx+1}", use_container_width=True)

# 5. 生成邏輯
if st.button("✨ 辨識圖片並生成題目"):
    if not uploaded_files:
        st.warning("請先上傳至少一張照片！")
    else:
        with st.spinner("AI 正在掃描圖片中的文字並思考題目..."):
            # 準備圖片資料
            image_data = []
            for file in uploaded_files:
                img = Image.open(file)
                image_data.append(img)
            
            # 指令
            prompt = f"""
            請先閱讀並理解這些圖片中的所有文字內容。
            接著，根據這些內容生成 {num_questions} 題繁體中文的選擇題。
            題目難度：{difficulty}。
            
            請嚴格遵守以下 JSON 格式回傳：
            [
              {{
                "question": "題目描述",
                "options": ["選項1", "選項2", "選項3", "選項4"],
                "answer": "正確選項的完整文字內容",
                "explanation": "詳細的答案解析"
              }}
            ]
            """
            
            try:
                # 同時傳送圖片與文字指令給 Gemini
                response = model.generate_content([prompt] + image_data)
                raw_json = re.sub(r'```json|```', '', response.text).strip()
                quiz_data = json.loads(raw_json)
                st.session_state.quiz_data = quiz_data
                st.session_state.user_answers = {}
                st.success("辨識成功！題目已準備好。")
            except Exception as e:
                st.error(f"辨識失敗，可能是圖片不清晰或 AI 暫時忙碌。錯誤：{e}")

# 6. 顯示考卷區 (同前一版)
if 'quiz_data' in st.session_state:
    st.divider()
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><h4><b>Q{i+1}: {q["question"]}</b></h4></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"作答 Q{i+1}", q['options'], key=f"ans_{i}")
        
        if st.form_submit_button("🏁 提交答案"):
            score = 0
            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers[i] == q['answer']:
                    score += 1
                    st.success(f"✅ Q{i+1} 正確")
                else:
                    st.error(f"❌ Q{i+1} 錯誤：答案是【{q['answer']}】")
                st.info(f"💡 解析：{q['explanation']}")
            
            st.balloons()
            st.metric("得分", f"{score} / {len(st.session_state.quiz_data)}")
