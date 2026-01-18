import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 配置 (已填入您的金鑰)
# ==========================================
API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 

# 修正 404 報錯的初始化邏輯
genai.configure(api_key=API_KEY)

# 建立模型實例 (嘗試正式路徑)
try:
    # 這是最標準的正式版路徑，通常能解決 404 問題
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
except Exception as e:
    # 如果上面失敗，嘗試加上 models/ 前綴
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# 1. 頁面配置與介面美化
st.set_page_config(page_title="AI 圖片自動出題王", layout="wide")

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

# 2. 側邊欄設定 (題數調高至 30 題)
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/test-passed.png", width=80)
    st.title("⚙️ 出題控制台")
    num_questions = st.slider("想要生成的總題數", 1, 30, 15)
    difficulty = st.select_slider("挑戰難度", options=["簡單", "普通", "困難"])
    st.divider()
    if st.button("🗑️ 清空目前的題目"):
        if 'quiz_data' in st.session_state:
            del st.session_state.quiz_data
        st.rerun()
    st.info(f"💡 建議：上傳 9 張照片時，設定 20 題以上能更完整覆蓋內容。")

# 3. 主要顯示區
st.title("📸 圖片轉考卷：海量題目生成版")
st.write("適合 iPad 使用：上傳多張講義照片，AI 會自動掃描並轉化為選擇題。")

# --- 圖片上傳區域 (支援多圖) ---
uploaded_files = st.file_uploader(
    "📂 點擊選取或拖入照片 (可一次選多張)", 
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
        with st.spinner(f"AI 正在深度掃描 {len(uploaded_files)} 張圖，準備生成 {num_questions} 題..."):
            try:
                # 處理圖片轉 PIL 格式
                image_data = [Image.open(file) for file in uploaded_files]
                
                # 給 AI 的深度出題指令
                prompt = f"""
                你是一位專業的老師。請詳細閱讀這 {len(uploaded_files)} 張圖片內容。
                請根據內容，總共生成 {num_questions} 題繁體中文的選擇題。
                
                要求：
                1. 題目必須平均分佈在所有上傳的圖片中。
                2. 難度設定：{difficulty}。
                3. 必須嚴格以 JSON 格式回傳，結構如下：
                [
                  {{
                    "question": "題目內容",
                    "options": ["選項1", "選項2", "選項3", "選項4"],
                    "answer": "正確選項的完整文字",
                    "explanation": "解析說明"
                  }}
                ]
                (請勿回傳 JSON 以外的任何文字)
                """
                
                # 執行生成
                response = model.generate_content([prompt] + image_data)
                
                # 強力提取 JSON 內容 (防止 Markdown 標籤干擾)
                clean_content = response.text
                clean_content = re.sub(r'```json\s*|```\s*', '', clean_content).strip()
                
                # 儲存結果
                st.session_state.quiz_data = json.loads(clean_content)
                st.session_state.user_answers = {}
                st.success(f"🎉 成功生成 {len(st.session_state.quiz_data)} 題測驗！")
            except Exception as e:
                st.error(f"生成失敗。這通常是 API 暫時連線問題，請點擊按鈕重試一次。錯誤：{e}")

# 4. 測驗顯示區
if 'quiz_data' in st.session_state:
    st.divider()
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"選擇答案 (Q{i+1})：", q['options'], key=f"ans_{i}")
        
        if st.form_submit_button("🏁 提交答案並看結果"):
            score = 0
            total = len(st.session_state.quiz_data)
            
            st.subheader("📊 批改報告")
            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers[i] == q['answer']:
                    score += 1
                    st.success(f"✅ 第 {i+1} 題正確")
                else:
                    st.error(f"❌ 第 {i+1} 題錯誤。正確答案：【{q['answer']}】")
                st.info(f"💡 解析：{q['explanation']}")
            
            st.balloons()
            st.metric("您的總得分", f"{score} / {total}")
