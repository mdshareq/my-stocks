import codecs
import re

file_path = r"e:\my-stocks\halal_dashboard.py"

with codecs.open(file_path, "r", "utf-8") as f:
    content = f.read()

tabs_pattern = r'tab_tracker, tab_my_portfolio, tab_portfolios, tab_accuracy, tab_charts, tab_news, tab_guide = st\.tabs\(\[.*?\]\)'

menu_code = """
    from streamlit_option_menu import option_menu
    
    st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)
    
    selected_tab = option_menu(
        menu_title=None,
        options=["Tracker", "Portfolio", "Combos", "Accuracy", "Charts", "News", "Guide"],
        icons=["activity", "briefcase", "robot", "bullseye", "graph-up", "newspaper", "compass"],
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {
                "padding": "10px", 
                "background-color": "#000000", 
                "border-radius": "50px",
                "max-width": "800px",
                "margin": "20px auto",
                "border": "1px solid #333"
            },
            "icon": {
                "color": "#64748b", 
                "font-size": "20px"
            }, 
            "nav-link": {
                "font-size": "0px", # Hides the text, leaving only the icon
                "text-align": "center", 
                "margin": "0 5px", 
                "--hover-color": "#111111",
                "border-radius": "50%",
                "width": "50px",
                "height": "50px",
                "display": "flex",
                "justify-content": "center",
                "align-items": "center"
            },
            "nav-link-selected": {
                "background-color": "#000000", 
                "icon-color": "#FFD700",
                "border-bottom": "3px solid #FFD700",
                "border-radius": "0px"
            }
        }
    )
"""

content = re.sub(tabs_pattern, menu_code.strip(), content)

# Replace the with blocks
content = content.replace('    with tab_tracker:', '    if selected_tab == "Tracker":')
content = content.replace('    with tab_my_portfolio:', '    if selected_tab == "Portfolio":')
content = content.replace('    with tab_portfolios:', '    if selected_tab == "Combos":')
content = content.replace('    with tab_accuracy:', '    if selected_tab == "Accuracy":')
content = content.replace('    with tab_charts:', '    if selected_tab == "Charts":')
content = content.replace('    with tab_news:', '    if selected_tab == "News":')
content = content.replace('    with tab_guide:', '    if selected_tab == "Guide":')

with codecs.open(file_path, "w", "utf-8") as f:
    f.write(content)
print("Successfully refactored dashboard UI to Option Menu.")
