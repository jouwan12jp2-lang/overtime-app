import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 配置 (已直接填入，不用再手動輸入)
# ==========================================
SAVED_API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 

# 1. 頁面配置
st.set_page_config(page_title="AI 圖片出題王 Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    div.stButton > button { border-radius: 8px; font-weight: bold; }
    .quiz-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
        border-left: 8px solid #007bff; 
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：自動載入 Key
with st.sidebar:
    st.header("🔑 安全設定")
    # 預設直接使用你提供的 Key
    user_api_key = st.text_input("API Key", value=SAVED_API_KEY, type="password")
    
    current_model = None
    if user_api_key:
        genai.configure(api_key=user_api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = [m for m in models if "1.5-flash" in m]
            model_name = target_model[0] if target_model else models[0]
            current_model = genai.GenerativeModel(model_name)
            st.success("✅ API 已自動就緒")
        except:
            st.error("❌ Key 無效，請檢查")

    st.divider()
    st.header("🎯 出題設定")
    # 題數按鈕
    st.write("📌 生成題數")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("10題"): st.session_state.num_q = 10
    with c2:
        if st.button("20題"): st.session_state.num_q = 20
    with c3:
        if st.button("30題"): st.session_state.num_q = 30
    
    if 'num_q' not in st.session_state: st.session_state.num_q = 15
    st.info(f"設定：**{st.session_state.num_q} 題**")

    # 難易度按鈕
    st.write("⚖️ 難度")
    d1, d2, d3 = st.columns(3)
    with d1:
        if st.button("簡單"): st.session_state.diff = "簡單"
    with d2:
        if st.button("普通"): st.session_state.diff = "普通"
    with d3:
        if st.button("困難"): st.session_state.diff = "困難"
    
    if 'diff' not in st.session_state: st.session_state.diff = "普通"
    st.info(f"難度：**{st.session_state.diff}**")

# 3. 主要介面 (保持不變)
st.title("📸 AI 視覺自動出題系統")

if not user_api_key:
    st.info("👋 請輸入 API Key 以開始。")
else:
    uploaded_files = st.file_uploader("📂 上傳照片", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("✨ 開始出題", type="primary"):
            with st.spinner("AI 正在分析內容並生成考題..."):
                try:
                    image_data = [Image.open(file) for file in uploaded_files]
                    prompt = f"""
                    你是一位專業老師。請分析圖片，生成 {st.session_state.num_q} 題繁體中文選擇題。
                    難度：{st.session_state.diff}。
                    1. 答案 (answer) 必須與選項 (options) 完全一致。
                    2. 每個題目必須包含解析 (explanation)。
                    """
                    response = current_model.generate_content([prompt] + image_data)
                    clean_content = re.search(r'\[.*\]', response.text, re.DOTALL).group(0)
                    st.session_state.quiz_data = json.loads(clean_content)
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.success("🎉 考題生成完畢！")
                except Exception as e:
                    st.error(f"錯誤：{e}")

# 4. 顯示與批改
if 'quiz_data' in st.session_state:
    st.divider()
    if 'submitted' not in st.session_state: st.session_state.submitted = False

    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"選擇答案", q['options'], key=f"ans_{i}")
        submit_clicked = st.form_submit_button("🏁 提交答案")

    if submit_clicked or st.session_state.submitted:
        st.session_state.submitted = True
        score = 0
        def clean_ans(text): return re.sub(r'^[A-D][\.\)\s]+', '', str(text)).strip()

        for i, q in enumerate(st.session_state.quiz_data):
            u_ans = clean_ans(st.session_state.user_answers[i])
            c_ans = clean_ans(q['answer'])
            if u_ans == c_ans:
                score += 1
                st.success(f"✅ 第 {i+1} 題正確")
            else:
                st.error(f"❌ 第 {i+1} 題錯誤。正確答案：【{q['answer']}】")
            st.info(f"💡 解析：{q.get('explanation', '無詳細解析')}")
            st.divider()
        st.balloons()
        st.metric("總分", f"{score} / {len(st.session_state.quiz_data)}")
