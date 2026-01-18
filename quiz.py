import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# 1. 頁面配置
st.set_page_config(page_title="AI 圖片出題王 Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    div.stButton > button { border-radius: 8px; font-weight: bold; height: 3em; }
    .quiz-card { 
        background-color: white; 
        padding: 25px; 
        border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
        border-left: 8px solid #007bff; 
    }
    /* 讓側邊欄輸入框更明顯 */
    .stTextInput>div>div>input {
        background-color: #fff9e6;
        border: 2px solid #ffcc00;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：安全設定與出題控制
with st.sidebar:
    st.header("🔑 安全設定")
    # 提醒：請去 Google AI Studio 申請一個新的 Key
    user_api_key = st.text_input("輸入新的 API Key", type="password", help="請輸入新的 API Key 以恢復功能")
    
    current_model = None
    if user_api_key:
        try:
            genai.configure(api_key=user_api_key)
            # 自動找尋可用模型
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = [m for m in models if "1.5-flash" in m]
            current_model = genai.GenerativeModel(target[0] if target else models[0])
            st.success("✅ 連線成功")
        except Exception as e:
            st.error(f"❌ 無法連線：{e}")

    st.divider()
    st.header("🎯 出題設定")
    # 題數按鈕 (使用會話狀態保持選擇)
    if 'num_q' not in st.session_state: st.session_state.num_q = 15
    if 'diff' not in st.session_state: st.session_state.diff = "普通"

    st.write("📌 生成題數")
    c1, c2, c3 = st.columns(3)
    if c1.button("10題"): st.session_state.num_q = 10
    if c2.button("20題"): st.session_state.num_q = 20
    if c3.button("30題"): st.session_state.num_q = 30
    st.info(f"目前設定：**{st.session_state.num_q} 題**")

    st.write("⚖️ 難度")
    d1, d2, d3 = st.columns(3)
    if d1.button("簡單"): st.session_state.diff = "簡單"
    if d2.button("普通"): st.session_state.diff = "普通"
    if d3.button("困難"): st.session_state.diff = "困難"
    st.info(f"目前難度：**{st.session_state.diff}**")

# 3. 主要介面
st.title("📸 AI 視覺自動出題系統")

if not user_api_key:
    st.warning("⚠️ 偵測到金鑰失效。請點擊上方 [Google AI Studio](https://aistudio.google.com/app/apikey) 重新申請一組 Key，並貼到左側黃色框框中。")
else:
    uploaded_files = st.file_uploader("📂 上傳 9 張照片 (支援多圖)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("✨ 辨識圖片並開始出題", type="primary", use_container_width=True):
            if current_model is None:
                st.error("請確保 API Key 正確且連線成功")
            else:
                with st.spinner("AI 正在分析內容..."):
                    try:
                        image_data = [Image.open(file) for file in uploaded_files]
                        prompt = f"""
                        你是專業老師。請分析圖片內容，生成 {st.session_state.num_q} 題繁體中文選擇題。
                        難度：{st.session_state.diff}。
                        規則：1. answer 必須與 options 完全一致。2. 包含解析 explanation。3. JSON 格式回傳。
                        """
                        response = current_model.generate_content([prompt] + image_data)
                        match = re.search(r'\[.*\]', response.text, re.DOTALL)
                        st.session_state.quiz_data = json.loads(match.group(0))
                        st.session_state.user_answers = {}
                        st.session_state.submitted = False
                        st.success("🎉 生成成功！")
                    except Exception as e:
                        st.error(f"生成出錯：{e}")

# 4. 測驗與批改
if 'quiz_data' in st.session_state:
    st.divider()
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"作答 Q{i+1}", q['options'], key=f"ans_{i}")
        
        if st.form_submit_button("🏁 提交答案", use_container_width=True):
            st.session_state.submitted = True

    if st.session_state.get('submitted'):
        score = 0
        def clean(t): return re.sub(r'^[A-D][\.\)\s]+', '', str(t)).strip()
        
        for i, q in enumerate(st.session_state.quiz_data):
            u = clean(st.session_state.user_answers[i])
            c = clean(q['answer'])
            if u == c:
                score += 1
                st.success(f"✅ Q{i+1} 正確")
            else:
                st.error(f"❌ Q{i+1} 錯誤。答案是：{q['answer']}")
            st.info(f"💡 解析：{q.get('explanation', '無解析')}")
        st.balloons()
        st.metric("您的總分", f"{score} / {len(st.session_state.quiz_data)}")
