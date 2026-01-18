import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 配置 (已填入您的金鑰)
# ==========================================
API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 
genai.configure(api_key=API_KEY)

# 🚀 終極修復：自動從您的 API 帳戶抓取可用的模型名稱
@st.cache_resource
def get_working_model():
    try:
        # 抓取目前帳戶支援的所有模型
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 優先尋找 flash 1.5 系列
        flash_models = [m for m in models if "1.5-flash" in m]
        if flash_models:
            return genai.GenerativeModel(flash_models[0])
        # 如果沒有 flash，隨便抓一個可用的 (例如 gemini-pro)
        return genai.GenerativeModel(models[0])
    except Exception as e:
        st.error(f"無法取得模型清單，請檢查 API Key。詳細錯誤：{e}")
        return None

model = get_working_model()

# 1. 頁面配置
st.set_page_config(page_title="AI 圖片自動出題王", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stFileUploader { background-color: white; padding: 30px; border-radius: 20px; border: 3px dashed #007bff; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; }
    .quiz-card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; border-left: 8px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄
with st.sidebar:
    st.title("⚙️ 出題控制台")
    num_questions = st.slider("想要生成的總題數", 1, 30, 15)
    difficulty = st.select_slider("挑戰難度", options=["簡單", "普通", "困難"])
    if st.button("🗑️ 清空目前題目"):
        if 'quiz_data' in st.session_state: del st.session_state.quiz_data
        st.rerun()

# 3. 主要顯示區
st.title("📸 圖片轉考卷：海量題目生成版")
st.write("已啟用「模型自動偵測」模式，解決 404 報錯問題。")

uploaded_files = st.file_uploader("📂 點擊選取或拖入照片 (可一次選多張)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    st.success(f"✅ 已讀取 {len(uploaded_files)} 張圖片")
    img_cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with img_cols[idx % 5]: st.image(file, use_container_width=True)

    if st.button("✨ 辨識 9 張圖並生成海量題目"):
        if not model:
            st.error("目前無法連接到 AI 模型，請稍後再試。")
        else:
            with st.spinner(f"AI 正在使用 {model.model_name} 掃描圖片中..."):
                try:
                    image_data = [Image.open(file) for file in uploaded_files]
                    prompt = f"""
                    你是一位專業老師，請閱讀圖片內容並生成 {num_questions} 題繁體中文選擇題。
                    難易度：{difficulty}。題目需均勻分佈於所有圖片。
                    回傳格式必須是 JSON 陣列，例如：
                    [
                      {{"question": "題目", "options": ["A", "B", "C", "D"], "answer": "正確選項文字", "explanation": "解析"}}
                    ]
                    (請勿包含 JSON 以外的文字說明)
                    """
                    
                    response = model.generate_content([prompt] + image_data)
                    
                    # 強化 JSON 提取
                    clean_content = response.text
                    json_match = re.search(r'\[.*\]', clean_content, re.DOTALL)
                    if json_match:
                        clean_content = json_match.group(0)
                    else:
                        clean_content = re.sub(r'```json\s*|```\s*', '', clean_content).strip()
                    
                    st.session_state.quiz_data = json.loads(clean_content)
                    st.session_state.user_answers = {}
                    st.success(f"🎉 成功生成！")
                except Exception as e:
                    st.error(f"生成失敗。錯誤訊息：{e}")

# 4. 顯示題目
if 'quiz_data' in st.session_state:
    st.divider()
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"選擇答案 (Q{i+1})：", q['options'], key=f"ans_{i}")
        
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
            st.metric("總分", f"{score} / {len(st.session_state.quiz_data)}")
