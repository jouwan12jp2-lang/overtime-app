import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 已填入
# ==========================================
API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 1. 頁面配置
st.set_page_config(page_title="AI 圖片萬能出題王", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stFileUploader {
        background-color: white;
        padding: 30px;
        border-radius: 20px;
        border: 3px dashed #007bff;
    }
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        height: 3.5em; 
        background-color: #007bff; 
        color: white; 
        font-weight: bold; 
    }
    .quiz-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
        margin-bottom: 20px; 
        border-left: 8px solid #007bff; 
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄設定 (調高題數上限)
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/test-passed.png", width=80)
    st.title("⚙️ 出題控制台")
    # 將題數上限調高到 30 題
    num_questions = st.slider("想要生成的總題數", 1, 30, 15)
    difficulty = st.select_slider("挑戰難度", options=["簡單", "普通", "困難"])
    st.divider()
    if st.button("🗑️ 清空目前的題目"):
        if 'quiz_data' in st.session_state:
            del st.session_state.quiz_data
        st.rerun()
    st.info(f"💡 您上傳了 9 張圖，建議設定為 {min(num_questions, 20)} 題以上以涵蓋所有重點。")

# 3. 主要顯示區
st.title("📸 圖片轉考卷：海量題目生成版")
st.write("已針對多圖上傳進行優化，AI 會細讀每一張圖片內容。")

uploaded_files = st.file_uploader(
    "📂 點擊這裡選取您的 9 張照片", 
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

    if st.button("✨ 辨識 9 張圖並生成海量題目"):
        with st.spinner(f"正在深度分析 9 張圖片，準備生成 {num_questions} 題..."):
            try:
                image_data = [Image.open(file) for file in uploaded_files]
                
                # 強化 Prompt，要求 AI 均勻分配題目到每一張圖
                prompt = f"""
                你是一位專業老師。這裡有 {len(uploaded_files)} 張教學圖片。
                請徹底閱讀每一張圖的細節，不要遺漏任何知識點。
                
                請根據圖片內容，總共生成 {num_questions} 題繁體中文的選擇題。
                要求：
                1. 題目必須平均分佈在所有上傳的圖片內容中。
                2. 難易度設定為：{difficulty}。
                3. 必須嚴格以 JSON 格式回傳，結構如下：
                [
                  {{
                    "question": "題目內容",
                    "options": ["選項1", "選項2", "選項3", "選項4"],
                    "answer": "正確選項文字",
                    "explanation": "解析說明"
                  }}
                ]
                """
                
                response = model.generate_content([prompt] + image_data)
                raw_json = re.sub(r'```json|```', '', response.text).strip()
                
                st.session_state.quiz_data = json.loads(raw_json)
                st.session_state.user_answers = {}
                st.success(f"🎉 成功生成 {len(st.session_state.quiz_data)} 題測驗！")
            except Exception as e:
                st.error(f"出題量較大時有時會斷訊，請嘗試減少題數或重試。錯誤：{e}")

# 4. 測驗顯示區
if 'quiz_data' in st.session_state:
    st.divider()
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"作答 {i+1}", q['options'], key=f"q_{i}")
        
        if st.form_submit_button("🏁 繳交考卷"):
            score = 0
            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers[i] == q['answer']:
                    score += 1
                    st.success(f"✅ Q{i+1} 正確")
                else:
                    st.error(f"❌ Q{i+1} 錯誤。答案：{q['answer']}")
                st.info(f"💡 解析：{q['explanation']}")
            st.balloons()
            st.metric("您的總得分", f"{score} / {len(st.session_state.quiz_data)}")
