import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# 1. 頁面配置與進階 CSS 美化
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
    .stTextInput>div>div>input {
        background-color: #fff9e6;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：API Key 輸入與設定
with st.sidebar:
    st.header("🔑 安全設定")
    # 這裡讓你在網頁直接輸入 Key
    user_api_key = st.text_input("在此貼上新的 API Key", type="password", help="請輸入從 Google AI Studio 複製的新金鑰")
    
    if user_api_key:
        genai.configure(api_key=user_api_key)
        # 自動偵測模型邏輯
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = [m for m in models if "1.5-flash" in m]
            model_name = target_model[0] if target_model else models[0]
            current_model = genai.GenerativeModel(model_name)
            st.success(f"✅ 連線成功")
        except:
            st.error("❌ Key 無效或未授權")
            current_model = None
    else:
        st.warning("請輸入 API Key 才能開始")
        current_model = None

    st.divider()
    st.header("🎯 出題設定")
    # 題數按鈕
    st.write("📌 生成題數")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("10題"): st.session_state.num_q = 10
    with col2:
        if st.button("20題"): st.session_state.num_q = 20
    with col3:
        if st.button("30題"): st.session_state.num_q = 30
    
    if 'num_q' not in st.session_state: st.session_state.num_q = 15
    st.info(f"設定：**{st.session_state.num_q} 題**")

    # 難易度按鈕
    st.write("⚖️ 難度")
    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        if st.button("簡單"): st.session_state.diff = "簡單"
    with d_col2:
        if st.button("普通"): st.session_state.diff = "普通"
    with d_col3:
        if st.button("困難"): st.session_state.diff = "困難"
    
    if 'diff' not in st.session_state: st.session_state.diff = "普通"
    st.info(f"難度：**{st.session_state.diff}**")

# 3. 主要介面
st.title("📸 AI 視覺自動出題系統")

if not user_api_key:
    st.info("👋 你好！請先在左側欄位貼入你新申請的 API Key，就可以開始拍照出題囉！")
else:
    uploaded_files = st.file_uploader("📂 上傳照片 (建議一次 9 張)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        img_cols = st.columns(min(len(uploaded_files), 5))
        for idx, file in enumerate(uploaded_files):
            with img_cols[idx % 5]: st.image(file, use_container_width=True)

        if st.button("✨ 辨識圖片並開始出題", type="primary"):
            with st.spinner("AI 正在深度掃描內容..."):
                try:
                    image_data = [Image.open(file) for file in uploaded_files]
                    prompt = f"""
                    你是資深老師。請分析這 {len(uploaded_files)} 張圖，生成 {st.session_state.num_q} 題繁體中文選擇題。
                    難度：{st.session_state.diff}。
                    重要：answer 必須與 options 中的文字完全一模一樣。
                    回傳純 JSON 格式。
                    """
                    response = current_model.generate_content([prompt] + image_data)
                    clean_content = re.search(r'\[.*\]', response.text, re.DOTALL).group(0)
                    st.session_state.quiz_data = json.loads(clean_content)
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.success("🎉 生成成功！")
                except Exception as e:
                    st.error(f"錯誤：{e}")

# 4. 測驗顯示與批改
if 'quiz_data' in st.session_state:
    st.divider()
    if 'submitted' not in st.session_state: st.session_state.submitted = False

    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>第 {i+1} 題：{q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"選擇答案 (Q{i+1})", q['options'], key=f"ans_{i}")
        submit_clicked = st.form_submit_button("🏁 提交答案")

    if submit_clicked or st.session_state.submitted:
        st.session_state.submitted = True
        score = 0
        for i, q in enumerate(st.session_state.quiz_data):
            u_ans = str(st.session_state.user_answers[i]).strip()
            c_ans = str(q['answer']).strip()
            if u_ans == c_ans:
                score += 1
                st.success(f"✅ 第 {i+1} 題正確")
            else:
                st.error(f"❌ 第 {i+1} 題錯誤。答案：【{c_ans}】")
            st.info(f"💡 解析：{q['explanation']}")
        st.balloons()
        st.metric("總分", f"{score} / {len(st.session_state.quiz_data)}")
