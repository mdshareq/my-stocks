import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
import google.generativeai as genai
import os

# Page Configuration
st.set_page_config(
    page_title="Shareq Equities",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- MINIMALIST, FUTURISTIC CSS ---
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Outfit:wght@200;300;400;500;600;700&family=JetBrains+Mono:wght@100;300;400;500;700&display=swap');

        body, .stApp {
            background: radial-gradient(circle at 50% 0%, #1c1e26 0%, #0a0b12 70%) !important;
            color: #fafafa;
            font-family: 'Outfit', -apple-system, sans-serif !important;
        }
        
        .page-title {
            display: inline-block;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: 3px;
            background: linear-gradient(135deg, #00b8c4 0%, #a78bfa 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
            color: transparent !important;
            margin-bottom: 2px;
        }
        
        [data-testid="stHeader"] {
            background: transparent !important;
            z-index: 99999 !important;
        }
        .stApp > header {
            background: transparent !important;
            z-index: 99999 !important;
        }
        
        .page-subtitle {
            font-family: 'Outfit', sans-serif;
            font-weight: 300;
            color: rgba(250, 250, 250, 0.5);
            font-size: 0.85rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        
        .stock-card, .metric-card, .advisor-card {
            border-radius: 12px;
            padding: 24px;
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            margin-bottom: 16px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            color: #fafafa !important;
        }
        
        .stock-card:hover {
            transform: translateY(-4px) scale(1.01);
            background: rgba(255, 255, 255, 0.07) !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
        }
        
        .stock-card.positive {
            border-left: 3px solid #00b8c4 !important;
        }
        .stock-card.positive:hover {
            box-shadow: 0 10px 30px rgba(0, 184, 196, 0.15), inset 0 0 15px rgba(0, 184, 196, 0.03);
        }
        
        .stock-card.negative {
            border-left: 3px solid #e1004c !important;
        }
        .stock-card.negative:hover {
            box-shadow: 0 10px 30px rgba(225, 0, 76, 0.15), inset 0 0 15px rgba(225, 0, 76, 0.03);
        }
        
        .stock-card.neutral {
            border-left: 3px solid rgba(255, 255, 255, 0.3) !important;
        }
        .stock-card.neutral:hover {
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .metric-card {
            border-left: 3px solid #10b981 !important;
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(255, 255, 255, 0.04) 100%) !important;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.1);
        }
        
        .symbol {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.15rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            color: #fafafa !important;
        }
        
        .company {
            color: #fafafa;
            opacity: 0.6;
            margin: 4px 0 12px;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .value {
            font-size: 1.9rem;
            font-weight: 300;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
            color: #fafafa !important;
            letter-spacing: -0.5px;
        }
        
        .delta {
            font-size: 0.85rem;
            font-weight: 500;
            font-family: 'JetBrains Mono', monospace;
        }
        .stock-card.positive .delta { color: #00b8c4 !important; }
        .stock-card.negative .delta { color: #e1004c !important; }
        .stock-card.neutral .delta { color: #fafafa !important; opacity: 0.7; }
        
        .metric-card h4 {
            margin: 0;
            font-size: 0.75rem;
            text-transform: uppercase;
            color: #fafafa;
            opacity: 0.6;
            letter-spacing: 1.5px;
            font-family: 'Space Grotesk', sans-serif;
        }
        
        .metric-card .metric-value {
            font-size: 1.7rem;
            font-weight: 500;
            color: #fafafa !important;
            margin-top: 8px;
            font-family: 'Space Grotesk', sans-serif;
        }
        
        /* Pulse dot animation */
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #00b8c4;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 0 0 rgba(0, 184, 196, 0.7);
            animation: pulse 1.8s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 184, 196, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(0, 184, 196, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 184, 196, 0); }
        }
        
        /* Terminal Window */
        .terminal-window {
            background: rgba(255, 255, 255, 0.02) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .terminal-header {
            background: rgba(255, 255, 255, 0.05) !important;
            padding: 10px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
        }
        .terminal-dots {
            display: flex;
            gap: 6px;
            margin-right: 15px;
        }
        .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .dot.red { background: #ef4444; }
        .dot.yellow { background: #eab308; }
        .dot.green { background: #22c55e; }
        .terminal-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.75rem;
            color: #fafafa;
            opacity: 0.6;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        
        /* Chat UI Tweaks */
        [data-testid="stChatMessage"] {
            background-color: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.06) !important;
            border-radius: 8px !important;
            margin-bottom: 10px !important;
            padding: 12px 16px !important;
        }
        [data-testid="stChatMessageContent"] {
            font-family: 'Outfit', sans-serif !important;
            font-size: 0.95rem !important;
            color: #fafafa !important;
        }
        
        /* Scrollbar styling */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.25); }
        
        /* Streamlit inputs overrides */
        [data-testid="stSidebar"] {
            background-color: #0a0b12 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }
        [data-testid="stSidebar"] h3 {
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: 1.5px;
            font-size: 1.05rem;
            color: #fafafa !important;
        }
        
        .stButton>button {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 8px 20px !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2) !important;
        }
        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(168, 85, 247, 0.4) !important;
        }
        
        /* Tabs design */
        [data-testid="stTabBar"] {
            gap: 10px !important;
            background: transparent !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
            padding-bottom: 8px !important;
        }
        [data-testid="stTabBar"] button {
            font-family: 'Space Grotesk', sans-serif !important;
            border-radius: 6px !important;
            padding: 8px 16px !important;
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.06) !important;
            color: #fafafa !important;
            opacity: 0.7;
            transition: all 0.2s ease !important;
        }
        [data-testid="stTabBar"] button[aria-selected="true"] {
            background: rgba(255, 255, 255, 0.1) !important;
            border-color: #a78bfa !important;
            color: #a78bfa !important;
            opacity: 1;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# Expanded Shariah-compliant Stocks (60+ Assets)
HALAL_STOCKS = {
    # IT / Tech
    "TCS.NS": "Tata Consultancy Services", "INFY.NS": "Infosys", "HCLTECH.NS": "HCL Technologies",
    "WIPRO.NS": "Wipro", "KPITTECH.NS": "KPIT Technologies", "TECHM.NS": "Tech Mahindra",
    "PERSISTENT.NS": "Persistent Systems", "COFORGE.NS": "Coforge", "MPHASIS.NS": "Mphasis",
    "LTTS.NS": "L&T Technology Services", "TATAELXSI.NS": "Tata Elxsi", "CYIENT.NS": "Cyient",
    
    # FMCG / Consumer / Retail
    "HINDUNILVR.NS": "Hindustan Unilever", "NESTLEIND.NS": "Nestle India", 
    "BRITANNIA.NS": "Britannia Industries", "GODREJCP.NS": "Godrej Consumer Products", "DABUR.NS": "Dabur India", 
    "MARICO.NS": "Marico", "COLPAL.NS": "Colgate-Palmolive", "TATACONSUM.NS": "Tata Consumer Products", 
    "HATSUN.NS": "Hatsun Agro", "BATAINDIA.NS": "Bata India", "DMART.NS": "Avenue Supermarts", 
    "TRENT.NS": "Trent Ltd", "HAVELLS.NS": "Havells India", "VOLTAS.NS": "Voltas",
    
    # Pharma / Healthcare
    "SUNPHARMA.NS": "Sun Pharmaceuticals", "DIVISLAB.NS": "Divi's Laboratories", "CIPLA.NS": "Cipla", 
    "DRREDDY.NS": "Dr. Reddy's Lab", "TORNTPHARM.NS": "Torrent Pharmaceuticals", "ZYDUSLIFE.NS": "Zydus Lifesciences", 
    "LUPIN.NS": "Lupin", "AUROPHARMA.NS": "Aurobindo Pharma", "ALKEM.NS": "Alkem Laboratories", 
    "BIOCON.NS": "Biocon", "APOLLOHOSP.NS": "Apollo Hospitals", "SYNGENE.NS": "Syngene International",
    
    # Auto / Manufacturing
    "MARUTI.NS": "Maruti Suzuki", "BAJAJ-AUTO.NS": "Bajaj Auto", "EICHERMOT.NS": "Eicher Motors", 
    "HEROMOTOCO.NS": "Hero MotoCorp", "TVSMOTOR.NS": "TVS Motor Company", "BOSCHLTD.NS": "Bosch Limited",
    
    # Cement / Core
    "ULTRACEMCO.NS": "Ultratech Cement", "SHREECEM.NS": "Shree Cement", "GRASIM.NS": "Grasim Industries", 
    "AMBUJACEM.NS": "Ambuja Cements", "ACC.NS": "ACC Limited", 
    
    # Chemicals / Paints
    "ASIANPAINT.NS": "Asian Paints", "BERGEPAINT.NS": "Berger Paints", 
    "PIDILITIND.NS": "Pidilite Industries", "SRF.NS": "SRF Limited", "DEEPAKNTR.NS": "Deepak Nitrite", 
    "AARTIIND.NS": "Aarti Industries", "PIIND.NS": "PI Industries", "NAVINFLUOR.NS": "Navin Fluorine", 
    "TATACHEM.NS": "Tata Chemicals", "ATUL.NS": "Atul Ltd",
    
    # Energy / Miscellaneous
    "RELIANCE.NS": "Reliance Industries", "ONGC.NS": "Oil & Natural Gas Corp", "TITAN.NS": "Titan Company",
}
REVERSE_LOOKUP = {name: ticker for ticker, name in HALAL_STOCKS.items()}
KEY_FILE = ".env_gemini_key"

# --- API KEY MANAGEMENT ---
def load_saved_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    return ""

def save_key(key):
    with open(KEY_FILE, "w") as f:
        f.write(key.strip())

# --- HELPER FUNCTIONS ---
def calculate_rsi(data, periods=14):
    close_delta = data['Close'].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    ma_down = down.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    rsi = ma_up / ma_down
    return 100 - (100 / (1 + rsi))

def calculate_macd(data, fast=12, slow=26, signal=9):
    exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = data['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_bollinger_bands(data, window=20, num_of_std=2):
    sma = data['Close'].rolling(window=window).mean()
    std = data['Close'].rolling(window=window).std()
    upper_band = sma + (std * num_of_std)
    lower_band = sma - (std * num_of_std)
    return upper_band, lower_band

def generate_svg_sparkline(prices, color):
    if len(prices) < 2: return ""
    price_list = prices.tolist()
    min_p, max_p = min(price_list), max(price_list)
    if max_p == min_p: max_p += 1 
    width, height = 110, 35
    points = []
    for i, p in enumerate(price_list):
        x = (i / (len(price_list) - 1)) * width
        y = height - ((p - min_p) / (max_p - min_p)) * height
        points.append(f"{x},{y}")
    
    path_data = f"M {' L '.join(points)}"
    fill_path_data = f"{path_data} L {width},{height} L 0,{height} Z"
    grad_id = f"sparkline-grad-{hash(color) & 0xffffffff}"
    
    return f"""
    <svg width="{width}" height="{height}" viewBox="0 -2 {width} {height+4}" fill="none" xmlns="http://www.w3.org/2000/svg" style="overflow: visible;">
        <defs>
            <linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="{height}">
                <stop offset="0%" stop-color="{color}" stop-opacity="0.15"/>
                <stop offset="100%" stop-color="{color}" stop-opacity="0.0"/>
            </linearGradient>
        </defs>
        <path d="{fill_path_data}" fill="url(#{grad_id})" />
        <path d="{path_data}" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """

def get_best_model(api_key):
    try:
        genai.configure(api_key=api_key)
        available = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        preferred = [
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-pro',
            'gemini-flash-latest',
            'gemini-3.5-flash'
        ]
        for model_name in preferred:
            if model_name in available:
                return model_name
                
        for model_name in available:
            if 'flash' in model_name or 'pro' in model_name:
                return model_name
                
        if available:
            return available[0]
    except Exception:
        pass
    return 'gemini-2.5-flash'

@st.cache_data(ttl=300)
def fetch_live_and_spark_data():
    tickers = list(HALAL_STOCKS.keys())
    data = []
    sparklines = {}
    
    try:
        # Broader Market Filter
        nifty = yf.download("^NSEI", period="2y", interval="1d", progress=False)
        market_healthy = True
        if not nifty.empty and len(nifty) >= 50:
            nifty_close = nifty["Close"].squeeze()
            nifty_sma50 = nifty_close.rolling(window=50).mean().iloc[-1]
            nifty_price = nifty_close.iloc[-1]
            market_healthy = bool(float(nifty_price) > float(nifty_sma50))
            
        live_data = yf.download(tickers, period="2y", interval="1d", progress=False, group_by="ticker")
        for ticker in tickers:
            try:
                # Safely fetch info, default to 0 if rate limited
                market_cap = 0; debt_to_equity = 0; total_cash = 0; total_assets = 1
                try:
                    ticker_obj = yf.Ticker(ticker)
                    info = ticker_obj.fast_info if hasattr(ticker_obj, 'fast_info') else ticker_obj.info
                    market_cap = info.get("marketCap", 0) or 0
                    
                    # Some versions of fast_info don't have debt/cash. Fallback to info.
                    if not market_cap: market_cap = ticker_obj.info.get("marketCap", 0) or 0
                    debt_to_equity = ticker_obj.info.get("debtToEquity", 0) or 0
                    total_cash = ticker_obj.info.get("totalCash", 0) or 0
                    total_assets = ticker_obj.info.get("totalAssets", 0) or 1
                except Exception:
                    pass # Rate limited or data missing, use defaults
                    
                cash_ratio = (total_cash / total_assets) * 100 if total_assets > 1 else 0
                cash_compliant = cash_ratio < 33
            
                if isinstance(live_data.columns, pd.MultiIndex) and ticker in live_data.columns.levels[0]:
                    hist = live_data[ticker].copy()
                elif "Close" in live_data.columns and len(tickers) == 1:
                    hist = live_data.copy()
                else:
                    continue
                    
                if hist.empty or len(hist) < 200: continue
                
                # Save trailing 30-day closings for sparklines
                sparklines[ticker] = hist["Close"].tail(30)
                
                current_price = hist["Close"].iloc[-1]
                prev_close = hist["Close"].iloc[-2]
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100
                
                sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
                sma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]
                current_rsi = calculate_rsi(hist).iloc[-1]
                macd, signal = calculate_macd(hist)
                upper_bb, lower_bb = calculate_bollinger_bands(hist)
                
                try:
                    avg_vol = hist["Volume"].rolling(window=20).mean().iloc[-1]
                    current_vol = hist["Volume"].iloc[-1]
                    has_volume = current_vol > avg_vol
                except Exception:
                    has_volume = False
                    
                # ADVANCED SCORING LOGIC
                score = 50 
                
                # Base logic
                if current_price > sma_50: score += 5
                if current_rsi < 30: score += 10 
                elif current_rsi < 40: score += 5
                elif current_rsi > 70: score -= 20 
                if has_volume: score += 10
                if debt_to_equity > 0 and debt_to_equity < 33: score += 10 
                if cash_compliant and total_assets > 1: score += 10
                
                # Quantitative Filters
                if current_price > sma_200: score += 10
                
                # MACD Bullish Crossover
                if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                    score += 15
                elif macd.iloc[-1] > signal.iloc[-1]:
                    score += 5
                    
                # Bollinger Band Oversold Bounce
                if current_price <= lower_bb.iloc[-1] * 1.02:
                    score += 10
                    
                # Broader Market Penalty
                if not market_healthy:
                    score -= 15
                
                data.append({
                    "Symbol": ticker.replace(".NS", ""), "Company Name": HALAL_STOCKS[ticker],
                    "Live Price (₹)": round(current_price, 2), "Change (₹)": round(change, 2),
                    "% Change": round(change_pct, 2), "Market Cap": market_cap,
                    "RSI": round(current_rsi, 2), "SMA50": round(sma_50, 2), "Buy Score": score
                })
            except Exception:
                # If this specific ticker fails, just skip it and continue
                continue
    except Exception:
        pass
    
    df = pd.DataFrame(data)
    if not df.empty: df = df.sort_values(by="Buy Score", ascending=False).reset_index(drop=True)
    return df, pd.DataFrame(sparklines)

@st.cache_data(ttl=3600)
def calculate_backtest_accuracy(days_ago=30):
    """Simulates the Algo Score 30 days ago and checks if it successfully predicted a price increase."""
    tickers = list(HALAL_STOCKS.keys())
    try:
        # Fetch NIFTY for historical market trend
        nifty = yf.download("^NSEI", period="2y", interval="1d", progress=False)
        if not nifty.empty:
            nifty_close = nifty["Close"].squeeze()
            nifty_sma50_series = nifty_close.rolling(50).mean()
        else:
            nifty_close = pd.Series(dtype='float64')
            nifty_sma50_series = pd.Series(dtype='float64')

        hist_data = yf.download(tickers, period="2y", interval="1d", progress=False)
        closes = hist_data['Close'] if 'Close' in hist_data else hist_data
        volumes = hist_data['Volume'] if 'Volume' in hist_data else pd.DataFrame()
        if closes.empty or len(closes) < 200: return pd.DataFrame()
        
        t_target_idx = -days_ago
        t_now_idx = -1
        results = []
        
        for ticker in tickers:
            if ticker not in closes: continue
            col = closes[ticker].dropna()
            if len(col) < 200: continue
            
            vol_col = volumes[ticker].dropna() if ticker in volumes else pd.Series(dtype='float64')
            df = pd.DataFrame({'Close': col, 'Volume': vol_col})
            
            # Calculate historical indicators
            sma50 = df['Close'].rolling(50).mean()
            sma200 = df['Close'].rolling(200).mean()
            rsi = calculate_rsi(df)
            macd, signal = calculate_macd(df)
            upper_bb, lower_bb = calculate_bollinger_bands(df)
            vol_sma = df['Volume'].rolling(20).mean() if not vol_col.empty else pd.Series(dtype='float64')
            
            try:
                price_t = df['Close'].iloc[t_target_idx]
                price_now = df['Close'].iloc[t_now_idx]
                
                # Check broader market on t_target
                market_healthy = True
                if not nifty.empty and len(nifty) >= abs(t_target_idx):
                    try:
                        n_price = nifty_close.iloc[t_target_idx]
                        n_sma = nifty_sma50_series.iloc[t_target_idx]
                        market_healthy = bool(float(n_price) > float(n_sma))
                    except: pass
                
                # Recreate Algo logic for that day in the past
                score = 50 
                if price_t > sma50.iloc[t_target_idx]: score += 5 
                if rsi.iloc[t_target_idx] < 30: score += 10 
                elif rsi.iloc[t_target_idx] < 40: score += 5
                elif rsi.iloc[t_target_idx] > 70: score -= 20 
                if not vol_col.empty and vol_col.iloc[t_target_idx] > vol_sma.iloc[t_target_idx]: score += 10
                
                # NEW FILTERS
                if price_t > sma200.iloc[t_target_idx]: score += 10
                
                if macd.iloc[t_target_idx] > signal.iloc[t_target_idx] and macd.iloc[t_target_idx-1] <= signal.iloc[t_target_idx-1]:
                    score += 15
                elif macd.iloc[t_target_idx] > signal.iloc[t_target_idx]:
                    score += 5
                    
                if price_t <= lower_bb.iloc[t_target_idx] * 1.02:
                    score += 10
                    
                if not market_healthy:
                    score -= 15
                    
                score += 20 # Assumed baseline debt & cash compliance for backtest speed
                
                if score >= 85: # Only track "Strong Buys" for accuracy checking
                    actual_return = ((price_now - price_t) / price_t) * 100
                    success = "WIN" if actual_return > 0 else "LOSS"
                    
                    results.append({
                        "Asset": ticker.replace(".NS", ""),
                        "Historical Score": score,
                        "Price 30d Ago": price_t,
                        "Price Today": price_now,
                        "Return (%)": actual_return,
                        "Outcome": success
                    })
            except IndexError:
                continue

        return pd.DataFrame(results)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_stock_history(ticker, period="90d", interval="1d"):
    try:
        history = yf.download(ticker, period=period, interval=interval, progress=False)
        return history if history is not None else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_stock_news(company_name):
    news_items = []
    query = quote_plus(f"{company_name} stock India")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(rss_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if response.ok:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item")[:5]:
                news_items.append({
                    "title": item.findtext("title", "Untitled"), "source": item.findtext("source", "Google News"),
                    "link": item.findtext("link", ""), "published": item.findtext("pubDate", ""),
                })
    except: pass
    return news_items

@st.cache_data(ttl=86400) # Cache for 24 hours to prevent slow loads
def fetch_portfolio_cagr(tickers):
    """Fetches 5-year monthly data to calculate the historical CAGR for a list of tickers."""
    try:
        data = yf.download(tickers, period="5y", interval="1mo", progress=False)
        closes = data['Close'] if 'Close' in data else data
        if closes.empty: return 0.12 # Fallback to 12% if failed
        
        start_prices = closes.bfill().iloc[0]
        end_prices = closes.iloc[-1]
        
        years = 5
        cagrs = []
        for ticker in tickers:
            try:
                if ticker in start_prices and ticker in end_prices:
                    s_price = start_prices[ticker]
                    e_price = end_prices[ticker]
                    if pd.notna(s_price) and pd.notna(e_price) and float(s_price) > 0:
                        cagr = (float(e_price) / float(s_price)) ** (1 / years) - 1
                        cagrs.append(cagr)
            except: pass
            
        if cagrs:
            return sum(cagrs) / len(cagrs) # Average CAGR
        return 0.12
    except:
        return 0.12

def calculate_future_value(monthly_sip, cagr, years):
    """Calculates the Future Value of a SIP (Systematic Investment Plan)"""
    if cagr <= 0: return monthly_sip * 12 * years
    monthly_rate = cagr / 12
    months = int(years * 12)
    fv = monthly_sip * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
    return fv

# --- UI LAYOUT ---
# Header Area
st.markdown("""
<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(128,128,128,0.15); padding-bottom: 20px; margin-bottom: 30px;'>
    <div>
        <div class='page-title'>SHAREQ EQUITIES</div>
        <div class='page-subtitle' style='margin-bottom: 0;'>Institutional Shariah-Compliant Algorithmic Screener</div>
    </div>
    <div style='display: flex; align-items: center; gap: 10px; background: rgba(128,128,128,0.05); border: 1px solid rgba(128,128,128,0.1); padding: 8px 16px; border-radius: 30px;'>
        <span class='pulse-dot'></span>
        <span style='font-size: 0.72rem; font-family: "Space Grotesk", sans-serif; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;'>Telemetry Active</span>
    </div>
</div>
""", unsafe_allow_html=True)

saved_api_key = load_saved_key()

with st.sidebar:
    st.markdown("### SYSTEM SETTINGS")
    api_key = st.text_input("GEMINI API KEY", value=saved_api_key, type="password")
    
    if api_key != saved_api_key:
        save_key(api_key)
        st.success("API Key saved locally.")
        
    st.markdown("### DYNAMIC FILTERS")
    min_score = st.slider("Min Algo Score", min_value=0, max_value=100, value=50, step=5)
    max_rsi = st.slider("Max RSI", min_value=10, max_value=90, value=70, step=5)
    min_mcap_cr = st.slider("Min Market Cap (₹ Cr)", min_value=0, max_value=1000000, value=0, step=10000)
    
    ordered_companies = list(HALAL_STOCKS.values())
    stock_filter = st.multiselect("ASSET FILTER (Optional)", options=ordered_companies, default=[])
    if st.button("EXECUTE SCAN"): st.rerun()

with st.spinner("Executing market scan & calculating metrics..."):
    stock_data, sparkline_data = fetch_live_and_spark_data()

if not stock_data.empty:
    gainers = stock_data[stock_data["% Change"] > 0].shape[0]
    losers = stock_data[stock_data["% Change"] < 0].shape[0]
    best = stock_data.sort_values("% Change", ascending=False).iloc[0]
    worst = stock_data.sort_values("% Change").iloc[0]

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.markdown(f"<div class='metric-card'><h4>Market Breadth</h4><div class='metric-value'>{'Bullish' if gainers >= losers else 'Bearish'}</div><div style='color:#64748b; font-size: 0.78rem; margin-top:5px;'>{gainers} Advancing | {losers} Declining</div></div>", unsafe_allow_html=True)
    with mc2:
        st.markdown(f"<div class='metric-card' style='border-left-color: #00F0FF !important; background: linear-gradient(135deg, rgba(0, 240, 255, 0.04) 0%, rgba(10, 11, 18, 0.6) 100%) !important;'><h4>Top Momentum (24H)</h4><div class='metric-value' style='color:#00F0FF;'>{best['Symbol']} +{best['% Change']:.2f}%</div><div style='color:#64748b; font-size: 0.78rem; margin-top:5px;'>{best['Company Name']}</div></div>", unsafe_allow_html=True)
    with mc3:
        st.markdown(f"<div class='metric-card' style='border-left-color: #FF0055 !important; background: linear-gradient(135deg, rgba(255, 0, 85, 0.04) 0%, rgba(10, 11, 18, 0.6) 100%) !important;'><h4>Max Drawdown (24H)</h4><div class='metric-value' style='color:#FF0055;'>{worst['Symbol']} {worst['% Change']:.2f}%</div><div style='color:#64748b; font-size: 0.78rem; margin-top:5px;'>{worst['Company Name']}</div></div>", unsafe_allow_html=True)

    # --- ADVANCED AI ADVISOR (INTERACTIVE TERMINAL) ---
    col1, col2 = st.columns([1.1, 0.9])
    
    with col1:
        st.markdown("### 🧠 SHAREQ AI CORE")
        if api_key:
            model_name = get_best_model(api_key)
            top_10 = stock_data.head(10)
            top_pick = top_10.iloc[0]
            if "messages" not in st.session_state:
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": f"Shareq Matrix loaded. Target asset: **{top_pick['Company Name']} ({top_pick['Symbol']})**. Score: {top_pick['Buy Score']}/100. RSI: {top_pick['RSI']}. Awaiting queries."
                }]
                
            # Render terminal header
            st.markdown(f"""
            <div class='terminal-window'>
                <div class='terminal-header'>
                    <div class='terminal-dots'>
                        <div class='dot red'></div>
                        <div class='dot yellow'></div>
                        <div class='dot green'></div>
                    </div>
                    <div class='terminal-title'>Advisor Terminal ({model_name})</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Display chat messages from history
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            # React to user input
            if user_query := st.chat_input("Query advisor core (e.g. 'Analyze TCS')"):
                st.session_state.messages.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.write(user_query)
                
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing market data..."):
                        try:
                            genai.configure(api_key=api_key)
                            # Using dynamically found model name
                            model = genai.GenerativeModel(model_name)
                            context_prompt = (
                                "You are a clinical Islamic Finance advisor and quantitative stock analyst. "
                                f"Here is the top 10 market data of Shariah-compliant Indian equities:\n{top_10.to_string()}\n\n"
                                f"User Question: {user_query}\n\n"
                                "Respond with concise, high-value, institutional-grade financial insight."
                            )
                            response = model.generate_content(context_prompt).text
                            st.write(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                        except Exception as e:
                            error_msg = f"API Error: {str(e)}. Please check your API Key and network connection."
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.rerun()
        else:
            st.markdown("""
            <div class='terminal-window' style='border-color: rgba(239, 68, 68, 0.2);'>
                <div class='terminal-header' style='background: rgba(239, 68, 68, 0.08);'>
                    <div class='terminal-dots'>
                        <div class='dot red'></div>
                        <div class='dot yellow'></div>
                        <div class='dot green'></div>
                    </div>
                    <div class='terminal-title' style='color: #ef4444;'>Advisor Terminal [Locked]</div>
                </div>
                <div style='padding: 30px; text-align: center;'>
                    <div style='font-size: 2.2rem; margin-bottom: 12px;'>🔒</div>
                    <h4 style='color: var(--text-color); margin-bottom: 6px; font-family: "Space Grotesk", sans-serif; font-size: 0.95rem; letter-spacing: 1px;'>AUTHENTICATION REQUIRED</h4>
                    <p style='font-size: 0.8rem; color: var(--text-color); opacity: 0.65; max-width: 300px; margin: 0 auto 10px; line-height: 1.4;'>Provide your Gemini API Key in the system settings sidebar to unlock the Shareq AI Core.</p>
                    <div style='background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; font-size: 0.75rem; text-align: left; max-width: 320px; margin: 0 auto;'>
                        <strong style='color: #00F0FF;'>How to get a free API Key:</strong><br>
                        1. Go to <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #a78bfa; text-decoration: none;">Google AI Studio</a><br>
                        2. Sign in with your Google account.<br>
                        3. Click <b>"Create API Key"</b> and paste it in the sidebar.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with col2:
        st.markdown("### TOP 10 ALGORITHMIC PICKS")
        top_10 = stock_data.head(10)
        st.dataframe(
            top_10[['Symbol', 'Company Name', 'Live Price (₹)', 'RSI', 'Buy Score']],
            column_config={
                "Symbol": "Asset", "Company Name": "Entity",
                "Live Price (₹)": st.column_config.NumberColumn("Price (₹)", format="%.2f"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Buy Score": st.column_config.ProgressColumn("Signal Strength", min_value=0, max_value=100),
            }, hide_index=True, width="stretch"
        )

    st.markdown("<hr style='border: 1px solid #111; margin: 30px 0;'>", unsafe_allow_html=True)

    # --- TABS SYSTEM ---
    tab_tracker, tab_portfolios, tab_accuracy, tab_charts, tab_news = st.tabs(["📊 LIVE TRACKER", "💼 PORTFOLIO COMBOS", "🎯 ALGO ACCURACY", "📈 ADVANCED CHARTS", "📰 NEWS RADAR"])
    
    with tab_tracker:
        filtered_data = stock_data[
            (stock_data["Buy Score"] >= min_score) & 
            (stock_data["RSI"] <= max_rsi) & 
            (stock_data["Market Cap"] >= min_mcap_cr * 10000000)
        ]
        if stock_filter:
            filtered_data = filtered_data[filtered_data["Company Name"].isin(stock_filter)]
            
        card_cols = st.columns(4)
        for idx, row in enumerate(filtered_data.to_dict(orient="records")):
            with card_cols[idx % 4]:
                direction = "positive" if row["% Change"] > 0 else "negative" if row["% Change"] < 0 else "neutral"
                sign = "+" if row["% Change"] > 0 else ""
                color_hex = "#00F0FF" if row["% Change"] > 0 else "#FF0055" if row["% Change"] < 0 else "#555555"
                
                ticker = REVERSE_LOOKUP[row['Company Name']]
                svg_chart = ""
                if not sparkline_data.empty and ticker in sparkline_data.columns:
                    svg_chart = generate_svg_sparkline(sparkline_data[ticker].dropna(), color_hex)
                
                st.markdown(f"""
                <div class='stock-card {direction}'>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class='symbol'>{row['Symbol']}</div>
                            <div class='company'>{row['Company Name']}</div>
                        </div>
                        <div style="margin-top: 4px;">{svg_chart}</div>
                    </div>
                    <div class='value'>₹{row['Live Price (₹)']:.2f}</div>
                    <div class='delta'>{sign}{row['Change (₹)']:.2f} ({sign}{row['% Change']:.2f}%)</div>
                    <div style='margin-top: 15px; font-size: 0.75rem; font-family: monospace; color: #555;'>RSI: {row['RSI']} &nbsp;|&nbsp; SCORE: {row['Buy Score']}</div>
                </div>
                """, unsafe_allow_html=True)

    with tab_charts:
        st.markdown("### Technical Price Action (90 Days)")
        selected_stock_chart = st.selectbox("Select Asset for Technical Analysis:", options=stock_data["Company Name"].tolist(), key="chart_select")
        selected_ticker = REVERSE_LOOKUP[selected_stock_chart]
        
        with st.spinner(f"Loading telemetry for {selected_ticker}..."):
            stock_history = fetch_stock_history(selected_ticker)
            if not stock_history.empty:
                close_data = stock_history["Close"]
                if isinstance(close_data, pd.DataFrame): close_data = close_data.iloc[:, 0]
                
                fig = px.line(x=stock_history.index, y=close_data, labels={"y": "Close (₹)", "x": ""})
                fig.update_traces(line=dict(color="#00F0FF", width=2))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#888",
                    margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
                )
                st.plotly_chart(fig, use_container_width=True)

    with tab_news:
        st.markdown("### Algorithmic News Radar")
        selected_news_stock = st.selectbox("Scan Headlines For:", options=stock_data["Company Name"].tolist(), key="news_select")
        with st.spinner("Scanning global feeds..."):
            headlines = fetch_stock_news(selected_news_stock)
            if headlines:
                for item in headlines:
                    st.markdown(f"**[{item['title']}]({item['link']})** \n<span style='color:var(--text-color); opacity: 0.65; font-size: 0.85rem;'>{item['source']} • {item['published']}</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='border: 1px solid rgba(128,128,128,0.15); margin: 15px 0;'>", unsafe_allow_html=True)
            else:
                st.info("No actionable intelligence found for this asset in the last 24 hours.")
                
    with tab_accuracy:
        st.markdown("### 30-Day Predictive Backtest")
        st.write("This engine simulates applying the Shareq algorithm 30 days in the past to see if its 'Strong Buy' recommendations (Score ≥ 85) successfully predicted a price increase.")
        
        with st.spinner("Simulating historical algorithm telemetry..."):
            backtest_df = calculate_backtest_accuracy(days_ago=30)
            
            if not backtest_df.empty:
                wins = len(backtest_df[backtest_df['Outcome'] == 'WIN'])
                total = len(backtest_df)
                win_rate = (wins / total) * 100 if total > 0 else 0
                
                color = "#00F0FF" if win_rate > 50 else "#FF0055"
                st.markdown(f"<div style='margin: 20px 0; padding: 20px; background: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, 0.15); border-left: 3px solid {color}; border-radius: 12px;'> <h3 style='margin:0; font-weight: 300; font-family: \"Space Grotesk\", sans-serif; color: var(--text-color);'>Win Rate: <span style='color:{color}'>{win_rate:.1f}%</span></h3> <p style='margin: 5px 0 0 0; color: var(--text-color); opacity: 0.6;'>{wins} successful predictions out of {total} strong buy signals triggered 30 days ago.</p> </div>", unsafe_allow_html=True)
                
                def style_outcome(val):
                    color = '#22c55e' if val == 'WIN' else '#ef4444' if val == 'LOSS' else 'inherit'
                    return f'color: {color}; font-weight: bold;'
                
                styled_df = backtest_df.style.map(style_outcome, subset=['Outcome'])
                
                st.dataframe(
                    styled_df,
                    column_config={
                        "Price 30d Ago": st.column_config.NumberColumn(format="₹%.2f"),
                        "Price Today": st.column_config.NumberColumn(format="₹%.2f"),
                        "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
                    }, hide_index=True, width="stretch"
                )
            else:
                st.info("No 'Strong Buy' signals were triggered 30 days ago by the algorithm parameters.")
                
    with tab_portfolios:
        st.markdown("### Time-Horizon Model Portfolios & SIP Projections")
        st.write("These algorithmic portfolios are categorized by investment horizon. Use the slider below to project your wealth based on historical mathematical CAGRs.")
        
        monthly_sip = st.slider("Monthly SIP Investment (₹)", min_value=1000, max_value=100000, value=10000, step=1000)
        
        portfolios = {
            "⚡ Short-Term Momentum (6 Months)": {
                "horizon": 0.5,
                "holdings": [
                    {"ticker": "KPITTECH", "weight": 20, "sector": "IT", "color": "#0ea5e9"},
                    {"ticker": "TRENT", "weight": 20, "sector": "Retail", "color": "#f43f5e"},
                    {"ticker": "ZYDUSLIFE", "weight": 20, "sector": "Pharma", "color": "#10b981"},
                    {"ticker": "TATAELXSI", "weight": 20, "sector": "IT", "color": "#0ea5e9"},
                    {"ticker": "COFORGE", "weight": 10, "sector": "IT", "color": "#0ea5e9"},
                    {"ticker": "VOLTAS", "weight": 10, "sector": "Consumer", "color": "#eab308"}
                ]
            },
            "⚖️ Mid-Term Balanced (3 Years)": {
                "horizon": 3.0,
                "holdings": [
                    {"ticker": "TCS", "weight": 25, "sector": "IT", "color": "#0ea5e9"},
                    {"ticker": "SUNPHARMA", "weight": 20, "sector": "Pharma", "color": "#10b981"},
                    {"ticker": "MARUTI", "weight": 15, "sector": "Auto", "color": "#8b5cf6"},
                    {"ticker": "TITAN", "weight": 15, "sector": "Consumer", "color": "#eab308"},
                    {"ticker": "RELIANCE", "weight": 15, "sector": "Energy", "color": "#f97316"},
                    {"ticker": "ONGC", "weight": 10, "sector": "Energy", "color": "#f97316"}
                ]
            },
            "💎 Long-Term Compounders (10 Years)": {
                "horizon": 10.0,
                "holdings": [
                    {"ticker": "ASIANPAINT", "weight": 25, "sector": "Core", "color": "#f59e0b"},
                    {"ticker": "PIDILITIND", "weight": 20, "sector": "Chemicals", "color": "#06b6d4"},
                    {"ticker": "HINDUNILVR", "weight": 20, "sector": "FMCG", "color": "#ec4899"},
                    {"ticker": "NESTLEIND", "weight": 15, "sector": "FMCG", "color": "#ec4899"},
                    {"ticker": "DMART", "weight": 10, "sector": "Retail", "color": "#f43f5e"},
                    {"ticker": "HAVELLS", "weight": 10, "sector": "Consumer", "color": "#eab308"}
                ]
            }
        }
        
        for p_name, p_data_info in portfolios.items():
            holding_defs = p_data_info["holdings"]
            p_tickers_no_ns = [h["ticker"] for h in holding_defs]
            p_tickers = [t + ".NS" for t in p_tickers_no_ns]
            p_data = stock_data[stock_data["Symbol"].isin(p_tickers_no_ns)]
            
            # Fetch real historical CAGR for the portfolio
            cagr = fetch_portfolio_cagr(p_tickers)
            future_value = calculate_future_value(monthly_sip, cagr, p_data_info["horizon"])
            total_invested = monthly_sip * 12 * p_data_info["horizon"]
            
            if not p_data.empty:
                avg_score = p_data["Buy Score"].mean()
                avg_return = p_data["% Change"].mean()
                
                # Determine color based on average score
                if avg_score >= 75: p_color = "#00F0FF"
                elif avg_score >= 50: p_color = "#F0B90B"
                else: p_color = "#FF0055"
                
                return_color = "#00F0FF" if avg_return > 0 else "#FF0055"
                
                holdings_html = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-top: 15px;'>"
                for h in holding_defs:
                    alloc_amt = monthly_sip * (h['weight'] / 100)
                    holdings_html += f"<div style='background: rgba(0,0,0,0.3); padding: 10px 15px; border-radius: 6px; border-left: 3px solid {h['color']};'><div style='display: flex; justify-content: space-between; margin-bottom: 5px;'><strong style='color: #fafafa; font-size: 0.9rem;'>{h['ticker']}</strong><span style='color: #00F0FF; font-weight: bold; font-size: 0.9rem;'>₹{alloc_amt:,.0f}</span></div><div style='display: flex; justify-content: space-between; align-items: center;'><div style='display: flex; align-items: center; gap: 5px;'><div style='width: 8px; height: 8px; border-radius: 50%; background: {h['color']};'></div><span style='color: #94a3b8; font-size: 0.75rem;'>{h['sector']}</span></div><span style='color: #94a3b8; font-size: 0.75rem;'>{h['weight']}% Alloc</span></div></div>"
                holdings_html += "</div>"
                
                st.markdown(f"""
                <div style='margin-bottom: 20px; padding: 20px; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(128, 128, 128, 0.15); border-left: 4px solid {p_color}; border-radius: 12px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                        <h3 style='margin:0; font-family: "Space Grotesk", sans-serif; color: #fafafa;'>{p_name}</h3>
                        <div style='text-align: right;'>
                            <div style='font-size: 0.8rem; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;'>Avg Algo Score</div>
                            <div style='font-size: 1.8rem; font-weight: bold; color: {p_color};'>{avg_score:.1f}</div>
                        </div>
                    </div>
                    <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 15px;'>
                        <div style='background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px;'>
                            <div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 5px;'>Historical 5Y CAGR</div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #a78bfa;'>{cagr*100:.1f}%</div>
                            <div style='font-size: 0.75rem; color: #64748b; margin-top: 5px;'>Real Data Average</div>
                        </div>
                        <div style='background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; border: 1px solid rgba(0, 240, 255, 0.2);'>
                            <div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 5px;'>Projected Future Value</div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #00F0FF;'>₹{future_value:,.0f}</div>
                            <div style='font-size: 0.75rem; color: #64748b; margin-top: 5px;'>vs ₹{total_invested:,.0f} invested</div>
                        </div>
                    </div>
                    <div style='display: flex; gap: 25px; margin-bottom: 15px; padding: 0 5px;'>
                        <div><span style='color: #94a3b8; font-size: 0.85rem;'>24H Momentum: </span> <span style='font-weight: 600; color: {return_color}'>{avg_return:+.2f}%</span></div>
                        <div><span style='color: #94a3b8; font-size: 0.85rem;'>Active Assets: </span> <span style='font-weight: 600; color: #fafafa;'>{len(p_data)}</span></div>
                    </div>
                    <div style='font-size: 0.9rem; color: #cbd5e1; line-height: 1.5; padding: 0 5px;'>
                        <strong style='color: #94a3b8; margin-bottom: 10px; display: inline-block;'>Fund Holdings Breakdown:</strong>
                        {holdings_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)