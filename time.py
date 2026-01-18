import streamlit as st
import google.generativeai as genai
import json
import re

# 1. 頁面配置與美化樣式
st.set_page_config(page_title="AI 智能考卷生成器", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; font-size: 1.1rem; }
    .quiz-card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 6px solid #007bff; }
    .score-box { background-color: #ffffff; padding: 30px; border-radius: 20px; text-align: center; border: 2px solid #28a745; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 設定 AI 鑰匙 (請把剛才複製的 Key 貼在下面引號內)
API_KEY = "這裡貼上你的_API_KEY" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 側邊欄設定
with st.sidebar:
    st.title("⚙️ 出題設定")
    num_questions = st.slider("生成題目數量", 1, 10, 3)
    difficulty = st.select_slider("難易度", options=["簡單", "普通", "困難"])
    st.divider()
    st.info("💡 提示：貼上的內容越具體，生成的題目品質越高。")

# 4. 主要介面
st.title("📚 AI 自動考卷生成系統")
st.write("輸入書本內容或課文重點，讓 AI 為您量身打造練習題。")

col_left, col_right = st.columns([0.6, 0.4])

with col_left:
    content = st.text_area("📖 請輸入或貼上書本內容：", height=400, placeholder="例如：貼上一段歷史故事、科學原理或英文課文...")

with col_right:
    st.subheader("🚀 操作區")
    if st.button("✨ 開始生成題目"):
        if not content:
            st.warning("請先輸入內容再生成題目哦！")
        else:
            with st.spinner("AI 正在深度閱讀並撰寫題目中..."):
                prompt = f"""
                請根據以下內容，生成 {num_questions} 題繁體中文的選擇題。
                題目難度設定為：{difficulty}。
                請嚴格遵守以下 JSON 格式回傳，不要有任何多餘的解釋文字：
                [
                  {{
                    "question": "題目描述",
                    "options": ["選項1", "選項2", "選項3", "選項4"],
                    "answer": "正確選項的完整文字內容",
                    "explanation": "詳細的答案解析"
                  }}
                ]
                內容內容：
                {content}
                """
                try:
                    response = model.generate_content(prompt)
                    raw_json = re.sub(r'```json|```', '', response.text).strip()
                    quiz_data = json.loads(raw_json)
                    st.session_state.quiz_data = quiz_data
                    st.session_state.user_answers = {}
                    st.success("考卷生成成功！請在下方作答。")
                except Exception as e:
                    st.error(f"生成過程發生錯誤，可能是內容太少或 AI 暫時忙碌。")

# 5. 顯示題目與作答區
if 'quiz_data' in st.session_state:
    st.divider()
    st.subheader("✍️ 隨堂測驗")
    
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"""
            <div class="quiz-card">
                <h4><b>第 {i+1} 題：{q['question']}</b></h4>
            </div>
            """, unsafe_allow_html=True)
            
            # 使用 radio 進行作答
            st.session_state.user_answers[i] = st.radio(f"選擇答案 (Q{i+1})：", q['options'], key=f"user_ans_{i}")
            st.write("") # 留白

        submit_btn = st.form_submit_button("🏁 提交考卷並看結果")

    if submit_btn:
        score = 0
        total = len(st.session_state.quiz_data)
        
        st.subheader("📊 測驗結果")
        for i, q in enumerate(st.session_state.quiz_data):
            is_correct = st.session_state.user_answers[i] == q['answer']
            if is_correct:
                score += 1
                st.success(f"✅ 第 {i+1} 題：正確")
            else:
                st.error(f"❌ 第 {i+1} 題：錯誤。正確答案是：【{q['answer']}】")
            
            st.info(f"💡 解析：{q['explanation']}")
            st.divider()
        
        # 顯示總分卡片
        st.markdown(f"""
        <div class="score-box">
            <h2 style='color: #28a745;'>測驗完成！</h2>
            <p style='font-size: 1.5rem;'>最終得分：<b>{score} / {total}</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.balloons()
