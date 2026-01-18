import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 API KEY 配置
# ==========================================
API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4" 
genai.configure(api_key=API_KEY)

# 🚀 模型自動偵測邏輯
@st.cache_resource
def get_working_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if "1.5-flash" in m]
        if flash_models:
            return genai.GenerativeModel(flash_models[0])
        return genai.GenerativeModel(models[0])
    except Exception as e:
        st.error(f"無法取得模型清單。詳細錯誤：{e}")
        return None

model = get_working_model()

# 1. 頁面配置與進階 CSS 美化
st.set_page_config(page_title="AI 圖片出題王 Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    div.stButton > button { border-radius: 8px; transition: all 0.3s; }
    .quiz-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
        border-left: 8px solid #007bff; 
    }
    .correct-ans { color: #28a745; font-weight: bold; }
    .wrong-ans { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄設定
with st.sidebar:
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
    st.info(f"當前設定：**{st.session_state.num_q} 題**")

    st.divider()

    # 難易度按鈕
    st.write("⚖️ 難易程度")
    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        if st.button("簡單"): st.session_state.diff = "簡單"
    with d_col2:
        if st.button("普通"): st.session_state.diff = "普通"
    with d_col3:
        if st.button("困難"): st.session_state.diff = "困難"
    
    if 'diff' not in st.session_state: st.session_state.diff = "普通"
    st.info(f"當前難度：**{st.session_state.diff}**")

    st.divider()
    if st.button("🗑️ 清空數據", use_container_width=True):
        for key in ['quiz_data', 'user_answers', 'submitted']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

# 3. 主要介面
st.title("📸 AI 視覺自動出題系統")

uploaded_files = st.file_uploader("📂 上傳照片 (支援多圖)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    img_cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with img_cols[idx % 5]: st.image(file, use_container_width=True)

    if st.button("✨ 辨識圖片並開始出題", type="primary"):
        with st.spinner("AI 正在深度掃描內容..."):
            try:
                image_data = [Image.open(file) for file in uploaded_files]
                prompt = f"""
                你是資深老師。讀取這 {len(uploaded_files)} 張圖，生成 {st.session_state.num_q} 題繁體中文選擇題。
                難度：{st.session_state.diff}。
                
                重要規範：
                1. "answer" 欄位必須與 "options" 列表中的其中一個字串完全一致（不可包含 A. B. 等前綴）。
                2. 嚴格回傳 JSON 陣列格式：
                [
                  {{"question": "題目", "options": ["選項1", "選項2", "選項3", "選項4"], "answer": "選項1", "explanation": "解析"}}
                ]
                """
                response = model.generate_content([prompt] + image_data)
                clean_content = re.search(r'\[.*\]', response.text, re.DOTALL).group(0)
                st.session_state.quiz_data = json.loads(clean_content)
                st.session_state.user_answers = {}
                st.session_state.submitted = False # 重置提交狀態
                st.success("🎉 題目生成成功！")
            except Exception as e:
                st.error(f"生成失敗：{e}")

# 4. 測驗顯示區
if 'quiz_data' in st.session_state:
    st.divider()
    
    # 用一個變數紀錄是否點擊了提交
    if 'submitted' not in st.session_state: st.session_state.submitted = False

    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>第 {i+1} 題：{q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"選擇答案 (Q{i+1})", q['options'], key=f"ans_{i}")
        
        submit_clicked = st.form_submit_button("🏁 提交答案")

    if submit_clicked or st.session_state.submitted:
        st.session_state.submitted = True
        score = 0
        total = len(st.session_state.quiz_data)
        
        st.subheader("📊 批改報告")
        for i, q in enumerate(st.session_state.quiz_data):
            # 關鍵：自動去掉前後空格進行比對
            user_ans = str(st.session_state.user_answers[i]).strip()
            correct_ans = str(q['answer']).strip()
            
            is_correct = (user_ans == correct_ans)
            
            if is_correct:
                score += 1
                st.markdown(f"✅ **第 {i+1} 題：正確**")
            else:
                st.markdown(f"❌ **第 {i+1} 題：錯誤**")
                st.write(f"你的答案：`{user_ans}`")
                st.write(f"正確答案：<span class='correct-ans'>{correct_ans}</span>", unsafe_allow_html=True)
            
            st.info(f"💡 解析：{q['explanation']}")
            st.divider()
        
        st.balloons()
        st.metric("總分", f"{score} / {total}")
