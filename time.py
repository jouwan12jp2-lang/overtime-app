import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 配置 (已填入您的金鑰)
# ==========================================
API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 

# 初始化 Google Gemini API
try:
    genai.configure(api_key=API_KEY)
    # 修正 404 錯誤：使用 gemini-1.5-flash 的標準名稱
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"API 初始化失敗，請檢查網路或 API Key。錯誤：{e}")

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

# 2. 側邊欄：題數上限調高
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/000000/test-passed.png", width=80)
    st.title("⚙️ 出題控制台")
    # 最高支援一次生成 30 題
    num_questions = st.slider("想要生成的總題數", 1, 30, 15)
    difficulty = st.select_slider("挑戰難度", options=["簡單", "普通", "困難"])
    st.divider()
    if st.button("🗑️ 清空目前題目"):
        if 'quiz_data' in st.session_state:
            del st.session_state.quiz_data
        st.rerun()
    st.info(f"💡 針對 9 張照片，建議設定 15 題以上能涵蓋更多細節。")

# 3. 主要顯示區
st.title("📸 圖片轉考卷：海量題目生成版")
st.write("適合 iPad 使用：上傳多張講義照片，AI 會自動掃描並轉化為選擇題。")

# --- 圖片上傳區域 (支援多圖) ---
uploaded_files = st.file_uploader(
    "📂 點擊選取或拖入照片 (可一次選 9 張)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"✅ 已讀取 {len(uploaded_files)} 張圖片")
    
    # 預覽縮圖
    img_cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with img_cols[idx % 5]:
            st.image(file, use_container_width=True)

    if st.button("✨ 辨識所有圖片並生成題目"):
        with st.spinner(f"AI 正在深度掃描 {len(uploaded_files)} 張圖，準備生成 {num_questions} 題..."):
            try:
                # 處理圖片轉 PIL 格式
                image_data = [Image.open(file) for file in uploaded_files]
                
                # 給 AI 的深度出題指令
                prompt = f"""
                你是一位專業的學科老師。請詳細閱讀這 {len(uploaded_files)} 張圖片內容。
                
                請根據這些內容，總共生成 {num_questions} 題繁體中文的選擇題。
                
                出題規範：
                1. 題目必須均勻分佈在所有圖片的內容中。
                2. 題目難度設定為：{difficulty}。
                3. 必須嚴格以 JSON 格式回傳（不要包含任何 Markdown 標籤或文字說明）：
                [
                  {{
                    "question": "題目內容",
                    "options": ["選項1", "選項2", "選項3", "選項4"],
                    "answer": "正確選項的完整文字",
                    "explanation": "詳細的答案解析"
                  }}
                ]
                """
                
                # 發送請求 (傳入指令 + 圖片列表)
                response = model.generate_content([prompt] + image_data)
                
                # 提取 JSON 內容（過濾 Markdown ```json 標籤）
                clean_content = response.text
                if "```json" in clean_content:
                    clean_content = clean_content.split("```json")[1].split("```")[0]
                elif "```" in clean_content:
                    clean_content = clean_content.split("```")[1].split("```")[0]
                
                # 儲存結果
                st.session_state.quiz_data = json.loads(clean_content.strip())
                st.session_state.user_answers = {}
                st.success(f"🎉 生成完畢！共計 {len(st.session_state.quiz_data)} 題。")
            except Exception as e:
                st.error(f"生成失敗。原因可能為圖片文字太模糊或題數過多（建議一次最多 20-25 題）。錯誤訊息：{e}")

# 4. 測驗與批改顯示區
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
                is_correct = st.session_state.user_answers[i] == q['answer']
                if is_correct:
                    score += 1
                    st.success(f"✅ 第 {i+1} 題正確")
                else:
                    st.error(f"❌ 第 {i+1} 題錯誤。正確答案：【{q['answer']}】")
                st.info(f"💡 解析：{q['explanation']}")
            
            # 分數看版
            st.markdown(f"""
            <div class="score-box">
                <h2 style='color: #28a745;'>測驗完成！</h2>
                <p style='font-size: 1.8rem;'>您的得分：<b>{score} / {total}</b></p>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
