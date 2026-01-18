import streamlit as st
import google.generativeai as genai
import json
import re
from PIL import Image

# ==========================================
# 🔑 1. API KEY 記憶 (預設填入)
# ==========================================
SAVED_API_KEY = "AIzaSyBRkz4-mlojLIdnkY6h85e4r1Xkv2S2AM4"

st.set_page_config(page_title="AI 智學出題王", layout="wide")

# 初始化 Session State (確保功能與資料不消失)
if 'num_q' not in st.session_state: st.session_state.num_q = 15
if 'diff' not in st.session_state: st.session_state.diff = "普通"
if 'wrong_pool' not in st.session_state: st.session_state.wrong_pool = []
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = None
if 'user_answers' not in st.session_state: st.session_state.user_answers = {}
if 'submitted' not in st.session_state: st.session_state.submitted = False

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    div.stButton > button { border-radius: 8px; font-weight: bold; }
    .quiz-card { 
        background-color: white; padding: 25px; border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; 
        border-left: 8px solid #007bff; 
    }
    .result-box { padding: 10px; border-radius: 8px; margin-top: 10px; font-weight: bold; }
    .stTextInput>div>div>input { background-color: #fff9e6; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# ⚙️ 2. 側邊欄：整合所有控制功能
# ==========================================
with st.sidebar:
    st.header("🔑 安全與記憶")
    user_api_key = st.text_input("Gemini API Key", value=SAVED_API_KEY, type="password")
    
    current_model = None
    if user_api_key:
        genai.configure(api_key=user_api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = [m for m in models if "1.5-flash" in m]
            current_model = genai.GenerativeModel(target[0] if target else models[0])
            st.success("✅ AI 已就緒")
        except: st.error("❌ Key 無效")

    st.divider()
    
    st.write("📌 生成題數")
    c1, c2, c3 = st.columns(3)
    if c1.button("10題"): st.session_state.num_q = 10
    if c2.button("20題"): st.session_state.num_q = 20
    if c3.button("30題"): st.session_state.num_q = 30
    st.info(f"目前設定：**{st.session_state.num_q} 題**")

    st.write("⚖️ 難易程度")
    d1, d2, d3 = st.columns(3)
    if d1.button("簡單"): st.session_state.diff = "簡單"
    if d2.button("普通"): st.session_state.diff = "普通"
    if d3.button("困難"): st.session_state.diff = "困難"
    st.info(f"目前難度：**{st.session_state.diff}**")

    st.divider()
    
    st.header("📚 錯題本")
    st.write(f"累積錯題：{len(st.session_state.wrong_pool)} 題")
    if st.button("🔄 錯題強化練習", use_container_width=True):
        if st.session_state.wrong_pool:
            st.session_state.quiz_data = st.session_state.wrong_pool[:10]
            st.session_state.user_answers = {}
            st.session_state.submitted = False
            st.rerun()
        else: st.warning("尚無錯題")

    if st.button("🗑️ 全部清空 (含錯題)", use_container_width=True):
        st.session_state.wrong_pool = []
        st.session_state.quiz_data = None
        st.rerun()

# ==========================================
# 📸 3. 主要介面
# ==========================================
st.title("📸 AI 全功能出題系統")

if not user_api_key:
    st.info("請輸入 API Key 以開始。")
else:
    uploaded_files = st.file_uploader("📂 上傳講義照片", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("✨ 辨識圖片並出題", type="primary", use_container_width=True):
            with st.spinner("AI 正在分析圖片..."):
                try:
                    image_data = [Image.open(file) for file in uploaded_files]
                    wrong_hint = str([q['question'] for q in st.session_state.wrong_pool[-3:]])
                    prompt = f"""
                    你是專業老師。分析圖片內容，生成 {st.session_state.num_q} 題繁體中文選擇題。
                    難度：{st.session_state.diff}。
                    重要規則：
                    1. answer 必須從 options 中原封不動挑選一個。
                    2. 每個題目必須包含解析 explanation。
                    3. 輸出純 JSON 陣列格式。
                    """
                    response = current_model.generate_content([prompt] + image_data)
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    st.session_state.quiz_data = json.loads(match.group(0))
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.success("🎉 生成成功！")
                except Exception as e: st.error(f"生成出錯：{e}")

# ==========================================
# 📝 4. 測驗與「即時題目下批改」邏輯
# ==========================================
if st.session_state.quiz_data:
    st.divider()
    
    # 輔助清理與比對函式
    def get_clean_text(text):
        return re.sub(r'^[A-D][\.\)\s\-]+', '', str(text)).strip()

    with st.form("quiz_form"):
        # 逐題顯示
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>Q{i+1}: {q["question"]}</b></div>', unsafe_allow_html=True)
            
            # 使用者選擇
            st.session_state.user_answers[i] = st.radio(f"作答 Q{i+1}", q['options'], key=f"ans_{i}", label_visibility="collapsed")
            
            # 如果已經提交，則在題目下方直接顯示結果
            if st.session_state.submitted:
                user_raw = st.session_state.user_answers[i]
                correct_raw = q['answer']
                u_clean = get_clean_text(user_raw)
                c_clean = get_clean_text(correct_raw)
                
                # 強化比對邏輯
                if u_clean == c_clean or u_clean in c_clean or c_clean in u_clean:
                    st.success(f"✅ 第 {i+1} 題正確！")
                else:
                    st.error(f"❌ 第 {i+1} 題錯誤。正確答案：【{correct_raw}】")
                
                st.info(f"💡 解析：{q.get('explanation', '無詳細解析')}")
                st.divider()
        
        if st.form_submit_button("🏁 提交答案並即時批改", use_container_width=True):
            st.session_state.submitted = True
            st.rerun() # 重新整理以觸發題目下方的結果顯示

    # 計算總分並更新錯題本
    if st.session_state.submitted:
        score = 0
        for i, q in enumerate(st.session_state.quiz_data):
            u_clean = get_clean_text(st.session_state.user_answers[i])
            c_clean = get_clean_text(q['answer'])
            if u_clean == c_clean or u_clean in c_clean or c_clean in u_clean:
                score += 1
            else:
                if q['question'] not in [wq['question'] for wq in st.session_state.wrong_pool]:
                    st.session_state.wrong_pool.append(q)
        
        st.balloons()
        st.metric("本次得分", f"{score} / {len(st.session_state.quiz_data)}")
