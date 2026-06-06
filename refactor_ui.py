import codecs
import re

file_path = r"e:\my-stocks\halal_dashboard.py"

with codecs.open(file_path, "r", "utf-8") as f:
    content = f.read()

# Replace the tabs definition
tabs_pattern = r'tab_tracker, tab_my_portfolio, tab_portfolios, tab_accuracy, tab_charts, tab_news, tab_guide = st\.tabs\(\[.*?\]\)'

sidebar_code = """
    st.markdown('''
        <style>
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 1.1rem;
            font-weight: 600;
            padding: 10px 0;
            cursor: pointer;
        }
        /* Hide radio circles */
        [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
            display: none;
        }
        </style>
    ''', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #00F0FF; margin-bottom: 20px;'>SHAREQ MATRIX</h2>", unsafe_allow_html=True)
        page = st.radio("Navigation", [
            "📊 LIVE TRACKER", 
            "💼 MY PORTFOLIO", 
            "🤖 PORTFOLIO COMBOS", 
            "🎯 ALGO ACCURACY", 
            "📈 ADVANCED CHARTS", 
            "📰 NEWS RADAR", 
            "🧭 APP GUIDE"
        ], label_visibility="collapsed")
"""

content = re.sub(tabs_pattern, sidebar_code.strip(), content)

# Replace the with blocks
content = content.replace('    with tab_tracker:', '    if page == "📊 LIVE TRACKER":')
content = content.replace('    with tab_my_portfolio:', '    if page == "💼 MY PORTFOLIO":')
content = content.replace('    with tab_portfolios:', '    if page == "🤖 PORTFOLIO COMBOS":')
content = content.replace('    with tab_accuracy:', '    if page == "🎯 ALGO ACCURACY":')
content = content.replace('    with tab_charts:', '    if page == "📈 ADVANCED CHARTS":')
content = content.replace('    with tab_news:', '    if page == "📰 NEWS RADAR":')
content = content.replace('    with tab_guide:', '    if page == "🧭 APP GUIDE":')

with codecs.open(file_path, "w", "utf-8") as f:
    f.write(content)
print("Successfully refactored dashboard UI.")
