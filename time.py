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

# 🚀 模型自動偵測邏輯 (保持不變)
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
    /* 整體背景與字體 */
    .main { background-color: #f4f7f9; }
    
    /* 側邊欄按鈕美化 */
    div.stButton > button:first-child {
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    /* 題目卡片美化 */
    .quiz-card { 
        background-color: white; 
        padding: 30px; 
        border-radius: 18px; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.06); 
        margin-bottom: 25px; 
        border-left: 10px solid #007bff; 
    }
    
    /* 上傳框美化 */
    .stFileUploader { 
        background-color: white; 
        padding: 40px; 
        border-radius: 25px; 
        border: 2px dashed #007bff;
        text-align: center;
    }
    
    /* 分數大字報 */
    .score-display {
        font-size: 3rem;
        font-weight: bold;
        color: #28a745;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 側邊欄：改用按鈕選擇
with st.sidebar:
    st.header("🎯 出題設定")
    
    # 題數選擇按鈕
    st.write("📌 生成題數")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("10題"): st.session_state.num_q = 10
    with col2:
        if st.button("20題"): st.session_state.num_q = 20
    with col3:
        if st.button("30題"): st.session_state.num_q = 30
    
    # 初始化預設值
    if 'num_q' not in st.session_state: st.session_state.num_q = 15
    st.info(f"當前設定：**{st.session_state.num_q} 題**")

    st.divider()

    # 難易度選擇按鈕
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
        if 'quiz_data' in st.session_state: del st.session_state.quiz_data
        st.rerun()

# 3. 主要顯示區
st.title("📸 AI 視覺自動出題系統")
st.caption("iPad 專用美化版：選取 9 張照片，快速轉化為深度測驗。")

uploaded_files = st.file_uploader("📂 點擊選取講義或筆記照片", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    st.success(f"✅ 已成功載入 {len(uploaded_files)} 張內容")
    # 縮圖展示
    img_cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with img_cols[idx % 5]: st.image(file, use_container_width=True)

    if st.button("✨ 辨識圖片並開始出題", type="primary"):
        if not model:
            st.error("AI 引擎未就緒")
        else:
            with st.spinner(f"正在分析圖片內容並設計 {st.session_state.num_q} 道題目..."):
                try:
                    image_data = [Image.open(file) for file in uploaded_files]
                    prompt = f"""
                    你是一位資深教師，請深度分析這 {len(uploaded_files)} 張圖片的知識點。
                    
                    請生成 {st.session_state.num_q} 題繁體中文選擇題。
                    難度：{st.session_state.diff}。
                    
                    要求：
                    1. 題目必須平均分佈在所有照片中。
                    2. 回傳必須是純 JSON 陣列格式：
                    [
                      {{"question": "題目", "options": ["A", "B", "C", "D"], "answer": "正確選項文字", "explanation": "解析"}}
                    ]
                    """
                    response = model.generate_content([prompt] + image_data)
                    
                    # 清理 JSON
                    clean_content = response.text
                    json_match = re.search(r'\[.*\]', clean_content, re.DOTALL)
                    clean_content = json_match.group(0) if json_match else re.sub(r'```json\s*|```\s*', '', clean_content).strip()
                    
                    st.session_state.quiz_data = json.loads(clean_content)
                    st.session_state.user_answers = {}
                    st.success("🎉 題目生成完畢！")
                except Exception as e:
                    st.error(f"生成失敗：{e}")

# 4. 測驗顯示區
if 'quiz_data' in st.session_state:
    st.divider()
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="quiz-card"><b>第 {i+1} 題：{q["question"]}</b></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio(f"作答區 (Q{i+1})", q['options'], key=f"ans_{i}")
        
        if st.form_submit_button("🏁 提交答案查看報告"):
            score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if st.session_state.user_answers[i] == q['answer']])
            
            st.subheader("📊 詳細批改報告")
            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers[i] == q['answer']:
                    st.success(f"✅ 第 {i+1} 題答對")
                else:
                    st.error(f"❌ 第 {i+1} 題答錯。正確答案：【{q['answer']}】")
                st.info(f"💡 解析：{q['explanation']}")
            
            st.markdown(f"""
            <div style="text-align: center; background: white; padding: 40px; border-radius: 20px; border: 4px solid #28a745;">
                <p style="font-size: 1.5rem; margin-bottom: 0;">您的最終得分</p>
                <div class="score-display">{score} / {len(st.session_state.quiz_data)}</div>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
