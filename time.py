import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# 1. 頁面配置
st.set_page_config(page_title="AI 智學出題王", layout="wide")

# 初始化錯題本 (Session State)
if 'wrong_pool' not in st.session_state:
    st.session_state.wrong_pool = []

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .quiz-card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 8px solid #007bff; }
    .wrong-book { background-color: #fff0f0; border: 2px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄
with st.sidebar:
    st.header("🔑 安全設定")
    user_api_key = st.text_input("API Key", type="password")
    
    if user_api_key:
        genai.configure(api_key=user_api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = [m for m in models if "1.5-flash" in m]
            current_model = genai.GenerativeModel(target[0] if target else models[0])
            st.success("✅ 連線成功")
        except: current_model = None
    else: current_model = None

    st.divider()
    st.header("📚 我的錯題本")
    st.write(f"目前累積錯題：**{len(st.session_state.wrong_pool)}** 題")
    
    if st.button("🔄 針對錯題強化練習", use_container_width=True):
        if len(st.session_state.wrong_pool) > 0:
            st.session_state.quiz_data = st.session_state.wrong_pool[:10] # 取前 10 題錯題
            st.session_state.user_answers = {}
            st.session_state.submitted = False
            st.rerun()
        else:
            st.warning("目前還沒有錯題紀錄喔！")

    if st.button("🗑️ 清空紀錄與錯題"):
        st.session_state.wrong_pool = []
        if 'quiz_data' in st.session_state: del st.session_state.quiz_data
        st.rerun()

# 3. 主要介面
st.title("📸 AI 視覺出題 & 弱點強化系統")

if not user_api_key:
    st.info("請先輸入 API Key。")
else:
    uploaded_files = st.file_uploader("📂 上傳講義照片", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("✨ 辨識圖片並出題", type="primary"):
            with st.spinner("分析中..."):
                try:
                    image_data = [Image.open(file) for file in uploaded_files]
                    # 這裡加入了對過去錯題的提示指令
                    wrong_context = str([q['question'] for q in st.session_state.wrong_pool[-5:]]) # 給 AI 看最近錯的 5 題
                    prompt = f"""
                    你是專業老師。請分析圖片內容，生成 10 題選擇題。
                    使用者過去曾答錯這些主題：{wrong_context}
                    請稍微提高與這些主題相關的題目比例。
                    回傳 JSON 格式。
                    """
                    response = current_model.generate_content([prompt] + image_data)
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    st.session_state.quiz_data = json.loads(match.group(0))
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                except Exception as e: st.error(f"錯誤：{e}")

# 4. 測驗與自動紀錄錯題
if 'quiz_data' in st.session_state:
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"作答 Q{i+1}", q['options'], key=f"ans_{i}")
        
        if st.form_submit_button("🏁 提交答案並紀錄錯題"):
            st.session_state.submitted = True

    if st.session_state.get('submitted'):
        score = 0
        temp_wrong = []
        for i, q in enumerate(st.session_state.quiz_data):
            u = str(st.session_state.user_answers[i]).strip()
            c = str(q['answer']).strip()
            if u == c:
                score += 1
                st.success(f"✅ Q{i+1} 正確")
            else:
                st.error(f"❌ Q{i+1} 錯誤")
                # 將錯題加入池中 (避免重複加入)
                if q not in st.session_state.wrong_pool:
                    st.session_state.wrong_pool.append(q)
            st.info(f"💡 解析：{q.get('explanation', '')}")
        
        st.metric("本次得分", f"{score} / {len(st.session_state.quiz_data)}")
        st.write(f"📖 錯題本已更新，目前共有 {len(st.session_state.wrong_pool)} 題可供後續強化。")
