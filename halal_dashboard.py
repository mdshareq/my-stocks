import streamlit as st
import yfinance as yf
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
import google.generativeai as genai
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

# --- FIREBASE INITIALIZATION ---
db = None
_firebase_error = None
_hardcoded_path = r"E:\my-stocks\.firebase_key.json"

try:
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(_hardcoded_path)
            firebase_admin.initialize_app(cred)
            print(f"Firebase: Initialized from {_hardcoded_path}")
        except Exception as file_e:
            try:
                if "firebase" in st.secrets:
                    cred = credentials.Certificate(dict(st.secrets["firebase"]))
                    firebase_admin.initialize_app(cred)
                    print("Firebase: Initialized from Streamlit secrets.")
                else:
                    _firebase_error = f"File error: {file_e}"
            except Exception as secret_e:
                _firebase_error = f"Secrets error: {secret_e}"
    
    if firebase_admin._apps:
        db = firestore.client()
        print("Firebase: Firestore client connected.")
    else:
        if not _firebase_error:
            _firebase_error = "Initialization skipped."
except Exception as e:
    db = None
    _firebase_error = str(e)
    print(f"Firebase Init Error: {e}")

# Page Configuration

# --- UNIVERSAL METRICS LOAD ---
UNIVERSE_METRICS_DF = pd.DataFrame()
try:
    if os.path.exists("halal_metrics.json"):
        with open("halal_metrics.json", "r", encoding="utf-8") as f:
            raw_metrics = json.load(f)
            if raw_metrics:
                valid_metrics = {k: v for k, v in raw_metrics.items() if "error" not in v}
                df = pd.DataFrame.from_dict(valid_metrics, orient='index')
                for col in ['pe', 'beta', 'market_cap', 'price', 'debt_ratio', 'liquidity_ratio', 'receivables_ratio']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                if 'dividend_yield' in df.columns:
                    df['dividend_yield'] = pd.to_numeric(df['dividend_yield'], errors='coerce').fillna(0)
                
                if 'is_compliant' not in df.columns:
                    df['is_compliant'] = False
                else:
                    df['is_compliant'] = df['is_compliant'].fillna(False).astype(bool)
                df['Compliance'] = df['is_compliant'].apply(lambda x: "✅ Halal" if x else "❌ Fail/Pending")
                
                # Generate a Fundamental Score (0-100)
                # Ideal: PE between 5 and 25 (score high), Beta near 1.0 (score high)
                def calc_score(row):
                    pe = row.get('pe', 0)
                    beta = row.get('beta', 1.0)
                    pe_score = 100 - min(abs(pe - 15) * 2, 50) if pe > 0 else 30
                    beta_score = 100 - min(abs(beta - 1.0) * 50, 50)
                    return (pe_score * 0.6) + (beta_score * 0.4)
                    
                df['Fundamental Score'] = df.apply(calc_score, axis=1)
                df['RSI'] = 50.0 # Mock RSI for the UI
                df['Company Name'] = df['name']
                df['Symbol'] = df['symbol']
                df['Live Price (₹)'] = df['price']
                df['Buy Score'] = df['Fundamental Score']
                UNIVERSE_METRICS_DF = df
except Exception as e:
    print("Error loading universal metrics:", e)

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

        /* Minimalist Institutional Form Submit Button */
        div[data-testid="stFormSubmitButton"] button {
            background-color: transparent !important;
            border: 1px solid rgba(148, 163, 184, 0.4) !important;
            color: #94a3b8 !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            font-family: 'Space Grotesk', sans-serif !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            border-color: #00F0FF !important;
            color: #00F0FF !important;
            background-color: rgba(0, 240, 255, 0.05) !important;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.1) !important;
        }

        /* Prevent Streamlit from fading stale elements */
        [data-testid="stAppViewContainer"] [data-stale="true"],
        [data-testid="stHeader"] [data-stale="true"],
        [data-testid="stSidebar"] [data-stale="true"],
        div[data-stale="true"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
        }

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
        .metric-card.momentum {
            border-left: 3px solid #00F0FF !important;
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.04) 0%, rgba(10, 11, 18, 0.6) 100%) !important;
        }
        .metric-card.momentum:hover {
            box-shadow: 0 8px 25px rgba(0, 240, 255, 0.15) !important;
        }
        .metric-card.drawdown {
            border-left: 3px solid #FF0055 !important;
            background: linear-gradient(135deg, rgba(255, 0, 85, 0.04) 0%, rgba(10, 11, 18, 0.6) 100%) !important;
        }
        .metric-card.drawdown:hover {
            box-shadow: 0 8px 25px rgba(255, 0, 85, 0.15) !important;
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
        
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 15px;
            margin-top: 15px;
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


HALAL_STOCKS = {}
try:
    if os.path.exists("live_watchlist.json"):
        with open("live_watchlist.json", "r", encoding="utf-8") as f:
            HALAL_STOCKS = json.load(f)
except Exception as e:
    print("Error loading live watchlist:", e)

REVERSE_LOOKUP = {info["name"]: ticker for ticker, info in HALAL_STOCKS.items()}
if 'UNIVERSE_METRICS_DF' in globals() and not UNIVERSE_METRICS_DF.empty:
    for _, row in UNIVERSE_METRICS_DF.iterrows():
        name = row['Company Name']
        sym = row['Symbol']
        if pd.notna(name) and pd.notna(sym):
            sym_ns = sym if str(sym).endswith((".NS", ".BO")) else sym + ".NS"
            if name not in REVERSE_LOOKUP:
                REVERSE_LOOKUP[name] = sym_ns

FULL_UNIVERSE = {}
try:
    if os.path.exists("halal_universe.json"):
        with open("halal_universe.json", "r", encoding="utf-8") as f:
            FULL_UNIVERSE = json.load(f)
    else:
        for ticker, info in HALAL_STOCKS.items():
            FULL_UNIVERSE[ticker] = info["name"]
except Exception:
    for ticker, info in HALAL_STOCKS.items():
        FULL_UNIVERSE[ticker] = info["name"]

REVERSE_FULL_UNIVERSE = {v: k for k, v in FULL_UNIVERSE.items()}

KEY_FILE = ".env_gemini_key"

# --- API KEY MANAGEMENT ---
def load_saved_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
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

# --- ALGO WEIGHTS ENGINE ---
DEFAULT_WEIGHTS = {
    "sma_50_above": 5,
    "rsi_below_30": 10,
    "rsi_below_40": 5,
    "rsi_above_70": -20,
    "high_volume": 10,
    "good_debt": 10,
    "good_cash": 10,
    "sma_200_above": 10,
    "macd_crossover": 15,
    "macd_bullish": 5,
    "bb_bounce": 10,
    "market_crash": -15
}

@st.cache_data(ttl=3600)
def fetch_algo_weights():
    if db is None: return DEFAULT_WEIGHTS
    try:
        doc = db.collection("system").document("algo_weights").get()
        if doc.exists:
            return doc.to_dict()
        else:
            db.collection("system").document("algo_weights").set(DEFAULT_WEIGHTS)
            return DEFAULT_WEIGHTS
    except Exception:
        return DEFAULT_WEIGHTS

def run_ml_optimizer():
    if db is None: return False, "Database not connected."
    try:
        nifty = yf.download("^NSEI", period="1mo", interval="1d", progress=False)
        if nifty.empty: return False, "Could not fetch market data."
        
        # Safely extract scalar values
        nifty_close = nifty["Close"]
        if isinstance(nifty_close, pd.DataFrame):
            nifty_close = nifty_close.iloc[:, 0]
            
        nifty_start = float(nifty_close.iloc[0])
        nifty_end = float(nifty_close.iloc[-1])
        market_return = ((nifty_end - nifty_start) / nifty_start) * 100
        
        doc = db.collection("system").document("algo_weights").get()
        weights = doc.to_dict() if doc.exists else DEFAULT_WEIGHTS.copy()
        
        # Determine if we are using Local AI
        ai_engine = st.session_state.get("ai_engine", "gemini")
        if ai_engine == "local":
            local_model = st.session_state.get("local_model", "qwen2.5-coder:3b-instruct")
            prompt = f"""You are a quantitative financial analyst AI.
The NIFTY 50 index has returned {market_return:.2f}% over the past 30 days.
Current algorithmic weights are: {json.dumps(weights)}

Rules for adjustments:
- If market is BEARISH (< 0%): Increase defensive metrics (good_debt, good_cash, rsi_below_30) and decrease momentum metrics (macd_crossover, sma_50_above).
- If market is BULLISH (> 0%): Increase momentum metrics and decrease defensive metrics slightly.
- Weights must stay between 0 and 30, except market_crash which can be negative (0 to -30), and rsi_above_70 (0 to -30).

Return ONLY a valid JSON dictionary of the updated weights. Do not provide explanations.
"""
            try:
                local_url = st.session_state.get("local_api_url", "http://localhost:11434/v1/chat/completions")
                local_key = st.session_state.get("local_api_key", "")
                headers = {"Content-Type": "application/json"}
                if local_key:
                    headers["Authorization"] = f"Bearer {local_key}"
                
                res = requests.post(local_url, json={
                    "model": local_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                }, headers=headers, timeout=30)
                res.raise_for_status()
                
                try:
                    response_json = res.json()
                except json.JSONDecodeError:
                    return False, f"Local AI returned an invalid response (HTML instead of JSON). Check the API URL ({local_url}) - you might be pointing to a Web UI port instead of the API port, or you might need an API Key."
                
                response_text = response_json["choices"][0]["message"]["content"].strip()
                if response_text.startswith("```json"):
                    response_text = response_text.replace("```json", "", 1).replace("```", "")
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "")
                
                new_weights = json.loads(response_text)
                for k, v in new_weights.items():
                    if k in weights and isinstance(v, (int, float)):
                        weights[k] = v
                
                db.collection("system").document("algo_weights").set(weights)
                fetch_algo_weights.clear()
                return True, f"Local AI ({local_model}) optimized algorithm weights for a {'Bearish' if market_return < 0 else 'Bullish'} market."
            except Exception as api_e:
                return False, f"Local AI Connection Failed: {str(api_e)}"
        else:
            # Auto-adjust logic based on market regime (Simple Heuristic ML)
            if market_return < 0:
                # Bear Market: Increase defense
                weights["rsi_below_30"] = min(20, weights.get("rsi_below_30", 10) + 2)
                weights["good_debt"] = min(15, weights.get("good_debt", 10) + 2)
                weights["good_cash"] = min(15, weights.get("good_cash", 10) + 2)
                # Decrease momentum
                weights["macd_crossover"] = max(5, weights.get("macd_crossover", 15) - 3)
                weights["sma_50_above"] = max(2, weights.get("sma_50_above", 5) - 1)
            else:
                # Bull Market: Increase momentum
                weights["macd_crossover"] = min(25, weights.get("macd_crossover", 15) + 3)
                weights["sma_50_above"] = min(10, weights.get("sma_50_above", 5) + 2)
                weights["sma_200_above"] = min(15, weights.get("sma_200_above", 10) + 2)
                # Decrease defense slightly
                weights["rsi_below_30"] = max(5, weights.get("rsi_below_30", 10) - 2)
                
            db.collection("system").document("algo_weights").set(weights)
            fetch_algo_weights.clear()
            return True, f"Algorithm successfully recalibrated for a {'Bearish' if market_return < 0 else 'Bullish'} market."
    except Exception as e:
        return False, str(e)


# --- USER PORTFOLIO LOGIC ---
def add_to_portfolio(email, symbol, company_name, price, qty):
    if db is None: return False, "Firebase is offline."
    try:
        if qty <= 0: return False, "Quantity must be greater than 0."
        portfolio_ref = db.collection("users").document(email).collection("portfolio").document(symbol)
        doc = portfolio_ref.get()
        
        if doc.exists:
            # Average out the buy price
            data = doc.to_dict()
            old_qty = data.get("quantity", 0)
            old_price = data.get("buy_price", 0)
            
            new_qty = old_qty + qty
            new_avg_price = ((old_qty * old_price) + (qty * price)) / new_qty
            
            portfolio_ref.update({
                "quantity": new_qty,
                "buy_price": new_avg_price,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        else:
            portfolio_ref.set({
                "symbol": symbol,
                "company_name": company_name,
                "buy_price": float(price),
                "quantity": int(qty),
                "added_at": firestore.SERVER_TIMESTAMP
            })
        return True, f"Successfully added {qty} shares of {symbol}."
    except Exception as e:
        return False, str(e)

def get_user_portfolio(email):
    if db is None: return []
    try:
        docs = db.collection("users").document(email).collection("portfolio").stream()
        return [doc.to_dict() for doc in docs]
    except Exception:
        return []

def update_portfolio(email, symbol, price, qty):
    from firebase_admin import firestore
    if db is None: return False, "Firebase is offline."
    try:
        if qty <= 0: return False, "Quantity must be greater than 0."
        portfolio_ref = db.collection("users").document(email).collection("portfolio").document(symbol)
        portfolio_ref.update({
            "buy_price": float(price),
            "quantity": int(qty),
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        return True, f"Successfully updated {symbol}."
    except Exception as e:
        return False, str(e)

def remove_from_portfolio(email, symbol):
    if db is None: return False, "Firebase is offline."
    try:
        db.collection("users").document(email).collection("portfolio").document(symbol).delete()
        return True, "Removed."
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=86400)
def fetch_fundamentals(ticker):
    # 1. Try Firestore Cache (7-day TTL)
    if db is not None:
        try:
            doc = db.collection("fundamentals_cache").document(ticker).get()
            if doc.exists:
                data = doc.to_dict()
                if "fetched_at" in data:
                    # Handle both offset-naive and aware datetime
                    fetched_date = data["fetched_at"]
                    if hasattr(fetched_date, 'replace'): 
                        fetched_date = fetched_date.replace(tzinfo=None)
                    if (datetime.now() - fetched_date).days < 7:
                        return data.get("debt_to_equity", 0), data.get("total_cash", 0), data.get("total_assets", 1)
        except Exception:
            pass
            
    # 2. Live Fetching with Fallbacks
    debt_to_equity, total_cash, total_assets = 0, 0, 1
    try:
        t = yf.Ticker(ticker)
        debt_to_equity = t.info.get("debtToEquity", 0) or 0
        total_cash = t.info.get("totalCash", 0) or 0
        total_assets = t.info.get("totalAssets", 0) or 1
        
        # Deep Fallback to Balance Sheet if basic info fails
        if debt_to_equity == 0 or total_cash == 0:
            bs = t.balance_sheet
            if not bs.empty:
                if 'Total Debt' in bs.index and 'Stockholders Equity' in bs.index:
                    debt = bs.loc['Total Debt'].iloc[0]
                    eq = bs.loc['Stockholders Equity'].iloc[0]
                    if eq > 0: debt_to_equity = (debt / eq) * 100
                if 'Cash And Cash Equivalents' in bs.index:
                    total_cash = bs.loc['Cash And Cash Equivalents'].iloc[0]
                if 'Total Assets' in bs.index:
                    total_assets = bs.loc['Total Assets'].iloc[0]
    except Exception:
        pass
        
    # 3. Save to Cache
    if db is not None:
        try:
            db.collection("fundamentals_cache").document(ticker).set({
                "debt_to_equity": debt_to_equity,
                "total_cash": total_cash,
                "total_assets": total_assets,
                "fetched_at": firestore.SERVER_TIMESTAMP
            })
        except Exception:
            pass
            
    return debt_to_equity, total_cash, total_assets

@st.cache_data(ttl=300)
def fetch_live_and_spark_data():
    algo_weights = fetch_algo_weights()
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
                    if not market_cap: market_cap = ticker_obj.info.get("marketCap", 0) or 0
                except Exception:
                    market_cap = 0
                    
                debt_to_equity, total_cash, total_assets = fetch_fundamentals(ticker)
                    
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
                
                # 14 Day Return (2 Weeks)
                price_14d_ago = hist["Close"].iloc[-15] if len(hist) >= 15 else prev_close
                return_14d = ((current_price - price_14d_ago) / price_14d_ago) * 100
                
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
                if current_price > sma_50: score += algo_weights.get("sma_50_above", 5)
                if current_rsi < 30: score += algo_weights.get("rsi_below_30", 10)
                elif current_rsi < 40: score += algo_weights.get("rsi_below_40", 5)
                elif current_rsi > 70: score += algo_weights.get("rsi_above_70", -20)
                if has_volume: score += algo_weights.get("high_volume", 10)
                if debt_to_equity > 0 and debt_to_equity < 33: score += algo_weights.get("good_debt", 10)
                if cash_compliant and total_assets > 1: score += algo_weights.get("good_cash", 10)
                
                # Quantitative Filters
                if current_price > sma_200: score += algo_weights.get("sma_200_above", 10)
                
                # MACD Bullish Crossover
                if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                    score += algo_weights.get("macd_crossover", 15)
                elif macd.iloc[-1] > signal.iloc[-1]:
                    score += algo_weights.get("macd_bullish", 5)
                    
                # Bollinger Band Oversold Bounce
                if current_price <= lower_bb.iloc[-1] * 1.02:
                    score += algo_weights.get("bb_bounce", 10)
                    
                # Broader Market Penalty
                if not market_healthy:
                    score += algo_weights.get("market_crash", -15)
                
                company_name = ticker
                if ticker in HALAL_STOCKS:
                    company_name = HALAL_STOCKS[ticker]["name"]
                elif 'UNIVERSE_METRICS_DF' in globals() and not UNIVERSE_METRICS_DF.empty:
                    m = UNIVERSE_METRICS_DF[UNIVERSE_METRICS_DF['Symbol'] == ticker.replace(".NS", "").replace(".BO", "")]
                    if not m.empty: company_name = m.iloc[0]['Company Name']
                
                data.append({
                    "Symbol": ticker.replace(".NS", ""), "Company Name": company_name,
                    "Live Price (₹)": round(current_price, 2), "Change (₹)": round(change, 2),
                    "% Change": round(change_pct, 2), "14D Return": round(return_14d, 2), "Market Cap": market_cap,
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
def get_ml_prediction_for_symbol(symbol):
    import os
    if not os.path.exists("best_model.pth"): return None
    try:
        import torch
        import numpy as np
        import json
        import yfinance as yf
        from sklearn.preprocessing import MinMaxScaler
        from ml_model import StockPredictorLSTM
        
        sym_sent = 0.0
        if os.path.exists("sentiment_data.json"):
            with open("sentiment_data.json", "r", encoding="utf-8") as f:
                sent_data = json.load(f)
                sym_sent = sent_data.get(symbol, {}).get("score", 0.0)
                
        hist = yf.Ticker(symbol).history(period="2mo")
        if hist.empty or len(hist) < 30: return None
        
        df_ml = hist[['Open', 'High', 'Low', 'Close', 'Volume']].tail(30).copy()
        if isinstance(df_ml.columns, pd.MultiIndex):
            df_ml.columns = df_ml.columns.get_level_values(0)
        df_ml['Sentiment'] = sym_sent
        
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(df_ml.values)
        x_tensor = torch.tensor(scaled_data, dtype=torch.float32).unsqueeze(0)
        
        device = torch.device('cpu')
        model = StockPredictorLSTM(input_dim=6, hidden_dim=64, num_layers=2, output_dim=1).to(device)
        model.load_state_dict(torch.load("best_model.pth", map_location=device))
        model.eval()
        
        with torch.no_grad():
            pred_scaled = model(x_tensor).item()
            
        dummy = np.zeros((1, 6))
        dummy[0, 3] = pred_scaled
        pred_price = scaler.inverse_transform(dummy)[0, 3]
        
        current_px = df_ml['Close'].iloc[-1]
        pred_change = ((pred_price - current_px) / current_px) * 100
        
        return {"price": pred_price, "change": pred_change, "sentiment": sym_sent}
    except Exception:
        return None

@st.cache_data(ttl=3600)
def calculate_backtest_accuracy(days_ago=30):
    """Fetches real 30-day algorithmic accuracy from Firebase, falling back to simulated logic if unavailable."""
    results = []
    
    # --- FIREBASE REAL-WORLD BACKTEST ---
    if db is not None:
        target_date = datetime.now() - timedelta(days=days_ago)
        # Search backward up to 10 days if no snapshot exactly 30 days ago exists
        for i in range(10):
            search_date = (target_date - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                doc = db.collection("daily_predictions").document(search_date).get()
                if doc.exists:
                    data = doc.to_dict()
                    predictions = data.get("predictions", [])
                    strong_buys = [p for p in predictions if p["Buy Score"] >= 75][:10]
                    
                    if strong_buys:
                        tickers_to_fetch = [p["Symbol"] if str(p["Symbol"]).endswith((".NS", ".BO")) else p["Symbol"] + ".NS" for p in strong_buys]
                        live_data = yf.download(tickers_to_fetch, period="5d", interval="1d", progress=False)
                        
                        for p in strong_buys:
                            ticker_ns = p["Symbol"] if str(p["Symbol"]).endswith((".NS", ".BO")) else p["Symbol"] + ".NS"
                            price_t = p["Live Price (₹)"]
                            try:
                                if isinstance(live_data, pd.DataFrame) and "Close" in live_data.columns:
                                    if isinstance(live_data.columns, pd.MultiIndex):
                                        price_now = float(live_data["Close"][ticker_ns].iloc[-1])
                                    else:
                                        price_now = float(live_data["Close"].iloc[-1])
                                else:
                                    price_now = float(live_data.iloc[-1])
                                    
                                actual_return = ((price_now - price_t) / price_t) * 100
                                success = "WIN" if actual_return > 0 else "LOSS"
                                results.append({
                                    "Asset": p["Symbol"],
                                    "Historical Score": p["Buy Score"],
                                    "Price 30d Ago": price_t,
                                    "Price Today": price_now,
                                    "Return (%)": actual_return,
                                    "Outcome": success
                                })
                            except Exception:
                                pass
                        
                        if results:
                            return pd.DataFrame(results)
                        break
            except Exception as e:
                print(f"Firebase Fetch Error: {e}")
                break

    # --- STATELESS SIMULATION FALLBACK ---
    tickers = list(HALAL_STOCKS.keys())
    # Expand the backtest simulation using the top 100 highly rated stocks from the 2700-stock master database
    if 'UNIVERSE_METRICS_DF' in globals() and not UNIVERSE_METRICS_DF.empty:
        safe_universe = UNIVERSE_METRICS_DF[UNIVERSE_METRICS_DF['market_cap'] >= 15000000000]
        top_100_symbols = safe_universe.sort_values(by='Buy Score', ascending=False).head(100)['Symbol'].tolist()
        top_100_tickers = [sym if str(sym).endswith((".NS", ".BO")) else sym + ".NS" for sym in top_100_symbols]
        tickers = list(set(tickers + top_100_tickers))
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

@st.cache_data(ttl=3600)
def calculate_ml_backtest_accuracy(days_ago=30, sample_size=20):
    """Simulates the LSTM PyTorch model dynamically in the past to see its accuracy."""
    try:
        import torch
        import numpy as np
        from sklearn.preprocessing import MinMaxScaler
        from ml_model import StockPredictorLSTM
        
        if not os.path.exists("best_model.pth"):
            return pd.DataFrame()
            
        device = torch.device('cpu')
        model = StockPredictorLSTM(input_dim=6, hidden_dim=64, num_layers=2, output_dim=1).to(device)
        model.load_state_dict(torch.load("best_model.pth", map_location=device))
        model.eval()
        
        sentiment_data = {}
        if os.path.exists("sentiment_data.json"):
            with open("sentiment_data.json", "r", encoding="utf-8") as f:
                sentiment_data = json.load(f)
                
        if 'UNIVERSE_METRICS_DF' in globals() and not UNIVERSE_METRICS_DF.empty:
            top_picks = UNIVERSE_METRICS_DF.sort_values(by='Buy Score', ascending=False).head(sample_size)
            tickers = top_picks['Symbol'].tolist()
            tickers = [t if str(t).endswith((".NS", ".BO")) else t + ".NS" for t in tickers]
        else:
            tickers = list(HALAL_STOCKS.keys())[:sample_size]
            
        hist_data = yf.download(tickers, period="100d", interval="1d", progress=False, group_by="ticker")
        
        results = []
        seq_length = 30
        
        for ticker in tickers:
            try:
                sym_sent = sentiment_data.get(ticker, {}).get("score", 0.0)
                
                if isinstance(hist_data.columns, pd.MultiIndex):
                    if ticker not in hist_data.columns.levels[0]: continue
                    df = hist_data[ticker][['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                else:
                    if ticker != tickers[0]: continue
                    df = hist_data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                    
                if len(df) < seq_length + days_ago + 1:
                    continue
                    
                t_target_idx = -days_ago
                t_next_idx = t_target_idx + 1 if t_target_idx < -1 else None
                
                df_ml = df.iloc[t_target_idx - seq_length : t_target_idx].copy()
                if len(df_ml) < seq_length: continue
                
                df_ml['Sentiment'] = sym_sent
                
                scaler = MinMaxScaler()
                scaled_data = scaler.fit_transform(df_ml.values)
                x_tensor = torch.tensor(scaled_data, dtype=torch.float32).unsqueeze(0)
                
                with torch.no_grad():
                    pred_scaled = model(x_tensor).item()
                    
                dummy = np.zeros((1, 6))
                dummy[0, 3] = pred_scaled
                pred_price = scaler.inverse_transform(dummy)[0, 3]
                
                price_t = float(df['Close'].iloc[t_target_idx - 1])
                if t_next_idx is not None:
                    actual_price_next = float(df['Close'].iloc[t_next_idx])
                else:
                    actual_price_next = float(df['Close'].iloc[-1])
                
                predicted_change = pred_price - price_t
                actual_change = actual_price_next - price_t
                
                if predicted_change > 0 and actual_change > 0:
                    success = "WIN"
                elif predicted_change < 0 and actual_change < 0:
                    success = "WIN"
                else:
                    success = "LOSS"
                    
                results.append({
                    "Asset": ticker.replace(".NS", ""),
                    "Pred Direction": "UP" if predicted_change > 0 else "DOWN",
                    "Actual Direction": "UP" if actual_change > 0 else "DOWN",
                    "Predicted Price": pred_price,
                    "Actual Price": actual_price_next,
                    "Diff (₹)": pred_price - actual_price_next,
                    "Outcome": success
                })
            except Exception:
                pass
                
        return pd.DataFrame(results)
    except Exception as e:
        print(f"ML Backtest Error: {e}")
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

def generate_dynamic_portfolios(stock_data, monthly_sip, risk_profile="Balanced", strategy="Growth (Momentum)"):
    """Dynamically generates portfolios based on live algorithmic data, the 2700+ universe, and user risk profiles."""
    portfolios = {}
    
    # Use the globally loaded universe
    universe_df = UNIVERSE_METRICS_DF
    
    # Define a color palette for sectors
    sector_colors = {
        "Technology": "#0ea5e9", "Healthcare": "#10b981", "Financial Services": "#8b5cf6",
        "Consumer Defensive": "#f59e0b", "Consumer Cyclical": "#f43f5e", "Industrials": "#64748b",
        "Energy": "#eab308", "Basic Materials": "#14b8a6", "Real Estate": "#ec4899", "Utilities": "#06b6d4"
    }
        
    def waterfall_allocate(pool_df, price_col="Live Price (₹)", sym_col="Symbol"):
        holdings_dict = {}
        for _, row in pool_df.iterrows():
            sym = row[sym_col]
            sec = row.get("sector", "Unknown") if "sector" in row else HALAL_STOCKS.get(sym+".NS", {}).get("sector", "Unknown")
            # Assign color dynamically
            color = sector_colors.get(sec, "#00F0FF")
            
            holdings_dict[sym] = {
                "qty": 0, 
                "price": row[price_col], 
                "sector": sec,
                "color": color,
                "score": row.get("Buy Score", 85.0)
            }
            
        remaining_budget = monthly_sip
        cheapest_price = pool_df[price_col].min()
        
        while remaining_budget >= cheapest_price:
            bought_anything = False
            for _, row in pool_df.iterrows():
                sym = row[sym_col]
                price = row[price_col]
                if remaining_budget >= price:
                    holdings_dict[sym]["qty"] += 1
                    remaining_budget -= price
                    bought_anything = True
            if not bought_anything:
                break
                
        final_holdings = []
        total_invested = monthly_sip - remaining_budget
        
        for sym, data in holdings_dict.items():
            if data["qty"] > 0:
                weight = ((data["qty"] * data["price"]) / total_invested) * 100
                final_holdings.append({
                    "ticker": sym.replace(".NS", "").replace(".BO", ""),
                    "full_ticker": sym,
                    "weight": weight,
                    "sector": data["sector"],
                    "color": data["color"],
                    "price": data["price"],
                    "qty": data["qty"],
                    "actual_spend": data["qty"] * data["price"],
                    "score": data["score"]
                })
                
        final_holdings = sorted(final_holdings, key=lambda x: x["weight"], reverse=True)
        return final_holdings, total_invested, remaining_budget

    # If the 2700+ universe exists, filter it!
    if universe_df is not None and not universe_df.empty:
        # Globally remove dangerous penny stocks and micro-caps (< ₹250 Crores) and ensure Halal compliance
        universe_df = universe_df[(universe_df['market_cap'] >= 2500000000) & (universe_df['is_compliant'] == True)]
        
        if "Conservative" in risk_profile:
            # Conservative: Strictly Mid & Large-Cap (> ₹5,000 Crores) and low Beta
            filtered_df = universe_df[(universe_df['beta'] < 1.0) & (universe_df['beta'] > 0) & (universe_df['market_cap'] >= 50000000000)]
            title_prefix = "🛡️ Safe"
        elif "Aggressive" in risk_profile:
            filtered_df = universe_df[(universe_df['beta'] > 1.2) & (universe_df['market_cap'] >= 5000000000)]
            title_prefix = "🚀 Aggressive"
        else:
            filtered_df = universe_df[(universe_df['beta'] >= 0.8) & (universe_df['beta'] <= 1.2) & (universe_df['market_cap'] >= 15000000000)]
            title_prefix = "⚖️ Balanced"
            
        if "Fundamental Score 90+" in strategy:
            filtered_df = filtered_df[filtered_df['Fundamental Score'] >= 90]
            filtered_df = filtered_df.sort_values('Fundamental Score', ascending=False)
        elif "Value" in strategy:
            filtered_df = filtered_df[(filtered_df['pe'] > 0) & (filtered_df['pe'] < 25)]
            filtered_df = filtered_df.sort_values('pe', ascending=True)
        elif "Income" in strategy:
            if 'dividend_yield' in filtered_df.columns:
                filtered_df = filtered_df.sort_values('dividend_yield', ascending=False)
            else:
                filtered_df = filtered_df.sort_values('market_cap', ascending=False)
        else:
            filtered_df = filtered_df.sort_values(['beta', 'market_cap'], ascending=[False, False])
            
        pool = filtered_df.head(20).copy()
        
        p1 = pool.head(10)
        h1, i1, r1 = waterfall_allocate(p1, "Live Price (₹)", "Symbol")
        portfolios[f"{title_prefix} Universe Portfolio (6 Months)"] = {"horizon": 0.5, "holdings": h1, "monthly_invested": i1, "uninvested_cash": r1}

        p2 = pool.iloc[5:15] if len(pool) >= 15 else pool.head(10)
        h2, i2, r2 = waterfall_allocate(p2, "Live Price (₹)", "Symbol")
        portfolios[f"{title_prefix} Universe Portfolio (3 Years)"] = {"horizon": 3.0, "holdings": h2, "monthly_invested": i2, "uninvested_cash": r2}

        p3 = pool.sort_values('market_cap', ascending=False).head(10)
        h3, i3, r3 = waterfall_allocate(p3, "Live Price (₹)", "Symbol")
        portfolios[f"{title_prefix} Universe Portfolio (10 Years)"] = {"horizon": 10.0, "holdings": h3, "monthly_invested": i3, "uninvested_cash": r3}

    else:
        # FALLBACK: Use top 57
        momentum_pool = stock_data[(stock_data["RSI"] >= 40) & (stock_data["RSI"] <= 75)].copy()
        if not momentum_pool.empty:
            momentum_pool = momentum_pool.sort_values(by=["14D Return", "Buy Score"], ascending=[False, False])
        momentum_assets = momentum_pool.head(12)
        if len(momentum_assets) < 5: 
            momentum_assets = stock_data.sort_values(by="14D Return", ascending=False).head(5)
        
        m_holdings, m_invested, m_rem = waterfall_allocate(momentum_assets)
        portfolios["⚡ Short-Term Momentum (6 Months)"] = {"horizon": 0.5, "holdings": m_holdings, "monthly_invested": m_invested, "uninvested_cash": m_rem}
        
        mid_pool = stock_data.sort_values(by="Buy Score", ascending=False).head(10)
        if len(mid_pool) < 5: mid_pool = stock_data.head(5)
        
        mid_holdings, mid_invested, mid_rem = waterfall_allocate(mid_pool)
        portfolios["⚖️ Mid-Term Balanced (3 Years)"] = {"horizon": 3.0, "holdings": mid_holdings, "monthly_invested": mid_invested, "uninvested_cash": mid_rem}
        
        defensive_sectors = ["FMCG", "Pharma", "Core", "Healthcare"]
        long_pool = stock_data[stock_data["Symbol"].apply(lambda x: HALAL_STOCKS.get(x+".NS", {}).get("sector") in defensive_sectors)].copy()
        if not long_pool.empty:
            long_pool = long_pool.sort_values(by="Buy Score", ascending=False)
        else:
            long_pool = stock_data.sort_values(by="Buy Score", ascending=False)
        long_assets = long_pool.head(10)
        
        l_holdings, l_invested, l_rem = waterfall_allocate(long_assets)
        portfolios["💎 Long-Term Compounders (10 Years)"] = {"horizon": 10.0, "holdings": l_holdings, "monthly_invested": l_invested, "uninvested_cash": l_rem}
        
    return portfolios
def log_daily_predictions_to_firebase(df):
    """Saves a daily snapshot of the algorithm's top predictions to Firestore."""
    if db is None: return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    doc_ref = db.collection("daily_predictions").document(today_str)
    
    try:
        if doc_ref.get().exists:
            return # Already logged today
            
        top_stocks = df.head(20).to_dict(orient="records")
        payload = {
            "date": today_str,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "predictions": top_stocks
        }
        doc_ref.set(payload)
        print(f"Successfully logged {today_str} predictions to Firebase.")
    except Exception as e:
        print(f"Firebase Logging Error: {e}")

# --- USER AUTHENTICATION ---
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def _save_session(user_dict):
    try:
        with open(".session_cache.json", "w") as f:
            # Only save serializable parts of user
            json.dump({"email": user_dict.get("email"), "gemini_api_key": user_dict.get("gemini_api_key")}, f)
    except Exception:
        pass

if 'user' not in st.session_state:
    st.session_state.user = None
    if os.path.exists(".session_cache.json"):
        try:
            with open(".session_cache.json", "r") as f:
                cached_user = json.load(f)
                if isinstance(cached_user, dict) and "email" in cached_user:
                    st.session_state.user = cached_user
        except Exception:
            pass

if 'auth_action' not in st.session_state:
    st.session_state.auth_action = 'Login'

if st.session_state.user is None:
    auth_container = st.empty()
    with auth_container.container():
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

        /* ── Keyframes for pure-CSS abstract background ── */
        @keyframes orbDrift1 {
            0%   { transform: translate(0px, 0px); }
            33%  { transform: translate(40px, -30px); }
            66%  { transform: translate(-20px, 20px); }
            100% { transform: translate(0px, 0px); }
        }
        @keyframes orbDrift2 {
            0%   { transform: translate(0px, 0px); }
            33%  { transform: translate(-35px, 25px); }
            66%  { transform: translate(15px, -40px); }
            100% { transform: translate(0px, 0px); }
        }
        @keyframes scanline {
            0%   { top: -80px; opacity: 0; }
            5%   { opacity: 1; }
            95%  { opacity: 1; }
            100% { top: 110vh; opacity: 0; }
        }

        /* Full dark background */
        [data-testid="stAppViewContainer"], .stApp {
            background: #080a10 !important;
            background-image: none !important;
            overflow: hidden !important;
        }
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="stHeader"] {display: none !important;}
        footer {display: none !important;}

        /* ── Abstract orb layer via stApp pseudo-elements ── */
        .stApp::before {
            content: '';
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 12% 22%, rgba(0,240,255,0.07) 0%, transparent 38%),
                radial-gradient(circle at 85% 68%, rgba(167,139,250,0.06) 0%, transparent 40%),
                radial-gradient(circle at 50% 88%, rgba(0,184,196,0.05) 0%, transparent 32%),
                radial-gradient(circle at 78% 15%, rgba(99,102,241,0.05) 0%, transparent 28%);
            animation: orbDrift1 18s ease-in-out infinite;
        }
        .stApp::after {
            content: '';
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image: radial-gradient(circle, rgba(148,163,184,0.07) 1px, transparent 1px);
            background-size: 52px 52px;
            animation: orbDrift2 22s ease-in-out infinite;
        }

        /* Scanline sweep */
        [data-testid="stAppViewContainer"]::after {
            content: '';
            position: fixed;
            left: 0; right: 0;
            height: 80px;
            background: linear-gradient(to bottom, transparent, rgba(0,240,255,0.025), transparent);
            animation: scanline 8s linear infinite;
            z-index: 1;
            pointer-events: none;
        }

        /* ── Login card = the block-container itself ── */
        .main .block-container {
            max-width: 430px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            margin-top: 8vh !important;
            margin-bottom: 5vh !important;
            padding: 44px 44px 40px !important;
            position: relative !important;
            z-index: 10 !important;
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 20px !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            box-shadow: 0 24px 64px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.06) !important;
        }

        /* Brand tag */
        .login-brand {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: rgba(0, 240, 255, 0.55);
            margin-bottom: 28px;
        }

        /* Heading */
        .login-heading {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.65rem;
            font-weight: 600;
            color: #f0f4f8;
            margin-bottom: 4px;
            letter-spacing: -0.3px;
        }

        /* Sub-heading */
        .login-sub {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.8rem;
            color: rgba(255,255,255,0.32);
            margin-bottom: 28px;
            letter-spacing: 0.2px;
        }

        /* Input label */
        div[data-testid="stTextInput"] label p {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.7rem !important;
            font-weight: 500 !important;
            letter-spacing: 1.2px !important;
            text-transform: uppercase !important;
            color: rgba(255,255,255,0.38) !important;
            margin-bottom: 5px !important;
        }

        /* Input field */
        div[data-testid="stTextInput"] input {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.09) !important;
            border-radius: 10px !important;
            color: #f0f4f8 !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.9rem !important;
            padding: 11px 13px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: rgba(255,255,255,0.16) !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: rgba(0, 240, 255, 0.38) !important;
            box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.07) !important;
            background: rgba(0, 240, 255, 0.03) !important;
        }
        div[data-testid="stTextInput"] > div {
            border: none !important;
            box-shadow: none !important;
        }

        /* Primary button (Sign In) */
        div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(135deg, rgba(0,240,255,0.13) 0%, rgba(167,139,250,0.13) 100%) !important;
            border: 1px solid rgba(0,240,255,0.32) !important;
            color: #d8f8ff !important;
            border-radius: 10px !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            letter-spacing: 1.8px !important;
            text-transform: uppercase !important;
            padding: 12px 0 !important;
            width: 100% !important;
            transition: all 0.22s ease !important;
            box-shadow: 0 0 18px rgba(0,240,255,0.07) !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: linear-gradient(135deg, rgba(0,240,255,0.2) 0%, rgba(167,139,250,0.2) 100%) !important;
            border-color: rgba(0,240,255,0.55) !important;
            box-shadow: 0 0 28px rgba(0,240,255,0.15) !important;
            transform: translateY(-1px) !important;
        }

        /* Ghost / secondary buttons */
        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stButton"] button:not([kind="primary"]) {
            background: transparent !important;
            border: none !important;
            color: rgba(0,240,255,0.5) !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            box-shadow: none !important;
            padding: 2px 0 !important;
            text-decoration: underline !important;
            text-underline-offset: 3px !important;
        }
        div[data-testid="stButton"] button:not([kind="primary"]):hover {
            color: rgba(0,240,255,0.82) !important;
            transform: none !important;
            box-shadow: none !important;
        }

        /* Demo button */
        .demo-btn button {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.07) !important;
            color: rgba(255,255,255,0.28) !important;
            border-radius: 8px !important;
            font-size: 0.72rem !important;
            letter-spacing: 1.2px !important;
            text-transform: uppercase !important;
            text-decoration: none !important;
            padding: 8px 0 !important;
            font-weight: 500 !important;
            transition: all 0.2s !important;
        }
        .demo-btn button:hover {
            border-color: rgba(255,255,255,0.15) !important;
            color: rgba(255,255,255,0.5) !important;
            background: rgba(255,255,255,0.06) !important;
        }

        /* Alert/notification */
        [data-testid="stNotification"] {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.09) !important;
            border-radius: 10px !important;
            color: rgba(255,255,255,0.65) !important;
        }

        /* Thin divider */
        .login-divider {
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07), transparent);
            margin: 24px 0;
        }

        /* Footer */
        .login-footer {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.6rem;
            color: rgba(255,255,255,0.15);
            text-align: center;
            margin-top: 24px;
            letter-spacing: 0.5px;
        }
    </style>
    """, unsafe_allow_html=True)


        is_login = st.session_state.auth_action == 'Login'

        # Brand tag
        st.markdown("<div class='login-brand'>Shareq Equities &nbsp;/&nbsp; Terminal Access</div>", unsafe_allow_html=True)

        # Heading
        heading = "Welcome back" if is_login else "Create account"
        sub = "Enter your credentials to continue." if is_login else "Register to unlock the full platform."
        st.markdown(f"<div class='login-heading'>{heading}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='login-sub'>{sub}</div>", unsafe_allow_html=True)

        if db is None:
            st.warning("⚠️ Firebase offline — local mode active.")

        email_val = st.text_input("Email", placeholder="user@example.com", key="auth_email")
        password_val = st.text_input("Password", type="password", placeholder="••••••••", key="auth_pass")

        if is_login:
            st.markdown("<div style='text-align:right; margin-top:-8px; margin-bottom:18px;'><a href='#' style='font-family:Space Grotesk,sans-serif; font-size:0.75rem; color:rgba(0,240,255,0.45); text-decoration:none; letter-spacing:0.5px;'>Forgot password?</a></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

        # Primary button
        if st.button("Sign In" if is_login else "Create Account", type="primary", use_container_width=True):
            if not email_val or not password_val:
                st.error("Both fields are required.")
            elif db is None:
                auth_container.empty()
                st.session_state.user = {"email": email_val, "gemini_api_key": ""}
                _save_session(st.session_state.user)
                st.rerun()
            else:
                users_ref = db.collection("users").document(email_val)
                doc = users_ref.get()
                if not is_login:
                    if doc.exists:
                        st.error("Account already exists. Please sign in.")
                    else:
                        users_ref.set({
                            "email": email_val,
                            "password_hash": hash_password(password_val),
                            "gemini_api_key": "",
                            "created_at": firestore.SERVER_TIMESTAMP
                        })
                        auth_container.empty()
                        st.session_state.user = {"email": email_val, "gemini_api_key": ""}
                        _save_session(st.session_state.user)
                        st.rerun()
                else:
                    if not doc.exists:
                        st.error("No account found. Please register first.")
                    else:
                        user_data = doc.to_dict()
                        if user_data.get("password_hash") == hash_password(password_val):
                            auth_container.empty()
                            st.session_state.user = user_data
                            _save_session(st.session_state.user)
                            st.rerun()
                        else:
                            st.error("Incorrect password.")

        # Divider
        st.markdown("<div class='login-divider'></div>", unsafe_allow_html=True)

        # Toggle auth mode
        prompt_text = "No account yet?" if is_login else "Already registered?"
        toggle_label = "Register here" if is_login else "Sign in instead"
        st.markdown(f"<div style='text-align:center; font-family:Space Grotesk,sans-serif; font-size:0.8rem; color:rgba(255,255,255,0.28); margin-bottom:10px;'>{prompt_text}</div>", unsafe_allow_html=True)
        if st.button(toggle_label, key="toggle_auth", use_container_width=True):
            st.session_state.auth_action = 'Register' if is_login else 'Login'
            st.rerun()

        # Demo access
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='demo-btn'>", unsafe_allow_html=True)
        if st.button("⚡  Quick Demo Access", key="demo_btn", use_container_width=True):
            auth_container.empty()
            st.session_state["demo_prefill"] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get("demo_prefill"):
            st.info("🔑 Demo credential — Username: `Shareq`")

        # Footer
        st.markdown("<div class='login-footer'>SHAREQ EQUITIES &nbsp;·&nbsp; SHARIAH-COMPLIANT SCREENER &nbsp;·&nbsp; v2.0</div>", unsafe_allow_html=True)

    st.stop()

# --- CSS RESET: Undo login-page overrides for the main dashboard ---
st.markdown("""
<style>
    /* Restore full-width block container */
    .main .block-container {
        max-width: 1200px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding: 3rem 1rem 1rem !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        box-shadow: none !important;
    }
    /* Remove login pseudo-element backgrounds from stApp */
    .stApp::before, .stApp::after {
        display: none !important;
    }
    [data-testid="stAppViewContainer"]::after {
        display: none !important;
    }
    /* Restore dashboard sidebar */
    [data-testid="stSidebar"] { display: flex !important; }
    [data-testid="stHeader"] { display: flex !important; }
    footer { display: block !important; }
    /* Restore dashboard button styles (undo login button overrides) */
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
        font-size: inherit !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        text-transform: none !important;
        padding: 8px 20px !important;
        width: auto !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2) !important;
        text-decoration: none !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.4) !important;
    }
    div[data-testid="stButton"] button:not([kind="primary"]) {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2) !important;
        text-decoration: none !important;
        padding: 8px 20px !important;
    }
    div[data-testid="stButton"] button:not([kind="primary"]):hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.4) !important;
        color: white !important;
    }
    /* Restore input styles for dashboard */
    div[data-testid="stTextInput"] label p {
        font-size: 0.875rem !important;
        font-weight: 400 !important;
        letter-spacing: 0 !important;
        text-transform: none !important;
        color: inherit !important;
    }
    div[data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #fafafa !important;
        font-size: 0.9rem !important;
        padding: 8px 12px !important;
    }
</style>
""", unsafe_allow_html=True)

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

if st.session_state.user:
    saved_api_key = st.session_state.user.get("gemini_api_key", "")
else:
    saved_api_key = load_saved_key()

with st.sidebar:
    if st.session_state.user:
        st.markdown(f"<div style='font-size: 0.8rem; color: #00F0FF; margin-bottom: 15px;'>Logged in: {st.session_state.user['email']}</div>", unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn"):
            st.session_state.user = None
            if os.path.exists(".session_cache.json"):
                try: os.remove(".session_cache.json")
                except Exception: pass
            st.rerun()
            
    st.markdown("### SYSTEM SETTINGS")
    
    ai_engine = st.radio("AI Engine", ["Google Gemini (Cloud)", "Local Odysseus Agent"], horizontal=True)
    if ai_engine == "Local Odysseus Agent":
        if st.button("🚀 Start Local AI Module (run.bat)", use_container_width=True):
            import subprocess
            try:
                subprocess.Popen([r"C:\Users\share\OneDrive\Desktop\run.bat"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                st.success("Started Local AI Module in a new window!")
            except Exception as e:
                st.error(f"Error starting local AI: {e}")
        
        local_model = st.selectbox("Local Model", ["qwen2.5-coder:3b-instruct", "llama3.2:3b"])
        local_api_url = st.text_input("Local API URL", value="http://localhost:11434/v1/chat/completions")
        local_api_key = st.text_input("Local API Key (If Required)", type="password")
        st.session_state.ai_engine = "local"
        st.session_state.local_model = local_model
        st.session_state.local_api_url = local_api_url
        st.session_state.local_api_key = local_api_key
    else:
        st.session_state.ai_engine = "gemini"
        
    api_key = st.text_input("GEMINI API KEY", value=saved_api_key, type="password")
    
    if api_key != saved_api_key:
        if st.session_state.user and db:
            db.collection("users").document(st.session_state.user["email"]).update({"gemini_api_key": api_key})
            st.session_state.user["gemini_api_key"] = api_key
            st.success("API Key securely saved to Cloud Profile.")
        else:
            save_key(api_key)
            st.success("API Key saved locally.")
            
    if st.button("🧠 Auto-Optimize Algorithm", help="Run ML engine to adjust scoring weights based on market regime.", width="stretch"):
        with st.spinner("Training model & adjusting weights..."):
            success, msg = run_ml_optimizer()
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("### LIVE DATA")
    auto_refresh = st.toggle("Enable Live Auto-Refresh (1m)", value=False)
    if auto_refresh:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=60000, key="data_refresh")
        
    st.markdown("### DYNAMIC FILTERS")
    min_score = st.slider("Min Algo Score", min_value=0, max_value=100, value=50, step=5)
    max_rsi = st.slider("Max RSI", min_value=10, max_value=90, value=70, step=5)
    min_mcap_cr = st.slider("Min Market Cap (₹ Cr)", min_value=0, max_value=1000000, value=0, step=10000)
    
    ordered_companies = [info["name"] for info in HALAL_STOCKS.values()]
    stock_filter = st.multiselect("ASSET FILTER (Optional)", options=ordered_companies, default=[])
    if st.button("EXECUTE SCAN"): st.rerun()

with st.spinner("Initializing Shareq Matrix Core & Syncing Live Data..."):
    stock_data, sparkline_data = fetch_live_and_spark_data()
    if not stock_data.empty:
        log_daily_predictions_to_firebase(stock_data)

if not stock_data.empty:
    gainers = stock_data[stock_data["% Change"] > 0].shape[0]
    losers = stock_data[stock_data["% Change"] < 0].shape[0]
    best = stock_data.sort_values("% Change", ascending=False).iloc[0]
    worst = stock_data.sort_values("% Change").iloc[0]

    best_ticker = REVERSE_LOOKUP.get(best['Company Name'], best['Symbol'])
    best_spark = ""
    if not sparkline_data.empty and best_ticker in sparkline_data.columns:
        best_spark = generate_svg_sparkline(sparkline_data[best_ticker].dropna(), "#00F0FF")
        
    worst_ticker = REVERSE_LOOKUP.get(worst['Company Name'], worst['Symbol'])
    worst_spark = ""
    if not sparkline_data.empty and worst_ticker in sparkline_data.columns:
        worst_spark = generate_svg_sparkline(sparkline_data[worst_ticker].dropna(), "#FF0055")

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.markdown(f"<div class='metric-card' style='height:100%; display:flex; flex-direction:column; justify-content:space-between;'><div><h4>Market Breadth</h4><div class='metric-value'>{'Bullish' if gainers >= losers else 'Bearish'}</div><div style='color:#64748b; font-size: 0.78rem; margin-top:5px;'>{gainers} Advancing | {losers} Declining</div></div></div>", unsafe_allow_html=True)
    with mc2:
        st.markdown(f"<div class='metric-card momentum' style='height:100%; display:flex; flex-direction:column; justify-content:space-between;'><div><h4>Top Momentum (24H)</h4><div class='metric-value' style='color:#00F0FF;'>{best['Symbol']} +{best['% Change']:.2f}%</div><div style='color:#64748b; font-size: 0.78rem; margin-top:5px; margin-bottom: 10px;'>{best['Company Name']}</div></div><div>{best_spark}</div></div>", unsafe_allow_html=True)
    with mc3:
        st.markdown(f"<div class='metric-card drawdown' style='height:100%; display:flex; flex-direction:column; justify-content:space-between;'><div><h4>Max Drawdown (24H)</h4><div class='metric-value' style='color:#FF0055;'>{worst['Symbol']} {worst['% Change']:.2f}%</div><div style='color:#64748b; font-size: 0.78rem; margin-top:5px; margin-bottom: 10px;'>{worst['Company Name']}</div></div><div>{worst_spark}</div></div>", unsafe_allow_html=True)

    # --- ADVANCED AI ADVISOR (INTERACTIVE TERMINAL) ---
    col1, col2 = st.columns([1.1, 0.9])
    
    with col1:
        st.markdown("### 🧠 SHAREQ AI CORE")
        ai_engine = st.session_state.get("ai_engine", "gemini")
        if ai_engine == "local" or api_key:
            model_name = st.session_state.get("local_model", "qwen2.5-coder:3b-instruct") if ai_engine == "local" else get_best_model(api_key)
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
                    <div class='terminal-title'>Advisor Terminal ({model_name} - {'Local' if ai_engine == 'local' else 'Cloud'})</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Display chat messages from history (only show the recent exchange)
            for msg in st.session_state.messages[-2:]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            # React to user input
            if user_query := st.chat_input("Query advisor core (e.g. 'Analyze TCS')"):
                st.session_state.messages.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.write(user_query)
                
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing market data..."):
                        import re
                        import pandas as pd
                        
                        query_words = set(re.findall(r'\b[A-Za-z0-9]+\b', user_query.upper()))
                        
                        # Find relevant stocks by matching Symbol or words in Company Name
                        def is_relevant(row):
                            symbol_match = str(row.get('Symbol', '')).upper() in query_words
                            name_words = set(re.findall(r'\b[A-Za-z0-9]+\b', str(row.get('Company Name', '')).upper()))
                            name_match = bool(query_words.intersection(name_words))
                            return symbol_match or name_match
                        
                        relevant_mask = stock_data.apply(is_relevant, axis=1)
                        relevant_stocks = stock_data[relevant_mask]
                        
                        # Combine relevant stocks with Top 10, max ~20 rows to prevent context overflow
                        context_df = pd.concat([relevant_stocks, top_10]).drop_duplicates(subset=["Symbol"]).head(20)
                        
                        context_prompt = (
                            "You are a clinical Islamic Finance advisor and quantitative stock analyst. "
                            f"Here is the relevant market data of Shariah-compliant Indian equities (filtered for the user's query):\n{context_df.to_string()}\n\n"
                            "CRITICAL RULES:\n"
                            "1. ALL stocks in the provided table are ALREADY strictly vetted and certified as 100% Shariah-compliant by the Shareq Matrix. DO NOT claim any stock in the table is non-compliant or haram.\n"
                            "2. Do not hallucinate or guess a company's business model (e.g., claiming a company makes firearms or alcohol if you are unsure). If you do not know the exact business model, state that and focus purely on the provided quantitative metrics (RSI, Buy Score, 14D Return, etc.).\n\n"
                            f"User Question: {user_query}\n\n"
                            "Respond with concise, high-value, institutional-grade financial insight."
                        )
                        try:
                            if ai_engine == "local":
                                import requests
                                local_url = st.session_state.get("local_api_url", "http://localhost:11434/v1/chat/completions")
                                local_key = st.session_state.get("local_api_key", "")
                                headers = {"Content-Type": "application/json"}
                                if local_key:
                                    headers["Authorization"] = f"Bearer {local_key}"
                                
                                res = requests.post(local_url, json={
                                    "model": model_name,
                                    "messages": [{"role": "user", "content": context_prompt}],
                                    "temperature": 0.7
                                }, headers=headers, timeout=60)
                                res.raise_for_status()
                                try:
                                    response_json = res.json()
                                except Exception:
                                    raise Exception(f"Local AI returned HTML instead of JSON. Check the API URL ({local_url}) and API Key.")
                                response = response_json["choices"][0]["message"]["content"].strip()
                            else:
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel(model_name)
                                response = model.generate_content(context_prompt).text
                                
                            st.write(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                        except Exception as e:
                            error_msg = f"AI Connection Error: {str(e)}. Please check your {'Odysseus server' if ai_engine == 'local' else 'Gemini API Key'}."
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
        if not UNIVERSE_METRICS_DF.empty:
            st.markdown("<span style='font-size:0.8rem; color:var(--primary-color);'>Scanning the 2,700+ Master Database</span>", unsafe_allow_html=True)
            safe_universe = UNIVERSE_METRICS_DF[(UNIVERSE_METRICS_DF['market_cap'] >= 20000000000) & (UNIVERSE_METRICS_DF['is_compliant'] == True)]
            top_10 = safe_universe.sort_values(by='Buy Score', ascending=False).head(10)
            
            st.dataframe(
                top_10[['Symbol', 'Company Name', 'Live Price (₹)', 'Compliance', 'pe', 'Buy Score']],
                column_config={
                    "Symbol": "Asset", "Company Name": "Entity",
                    "Live Price (₹)": st.column_config.NumberColumn("Price (₹)", format="%.2f"),
                    "Compliance": "Shariah Status",
                    "pe": st.column_config.NumberColumn("P/E Ratio", format="%.1f"),
                    "Buy Score": st.column_config.ProgressColumn("Signal Strength", min_value=0, max_value=100, format="%.1f"),
                }, hide_index=True, width="stretch"
            )
        else:
            top_10 = stock_data.head(10)
            st.dataframe(
                top_10[['Symbol', 'Company Name', 'Live Price (₹)', 'RSI', 'Buy Score']],
                column_config={
                    "Symbol": "Asset", "Company Name": "Entity",
                    "Live Price (₹)": st.column_config.NumberColumn("Price (₹)", format="%.2f"),
                    "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
                    "Buy Score": st.column_config.ProgressColumn("Signal Strength", min_value=0, max_value=100, format="%.1f"),
                }, hide_index=True, width="stretch"
            )

    st.markdown("<hr style='border: 1px solid #111; margin: 30px 0;'>", unsafe_allow_html=True)

    # --- TABS SYSTEM ---
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
                "margin": "0 auto",
                "border": "1px solid #333"
            },
            "icon": {
                "font-size": "22px" # Removed hardcoded color so it inherits
            }, 
            "nav-link": {
                "color": "#64748b", # Inactive icon color
                "font-size": "0px", # Hides the text, leaving only the icon
                "text-align": "center", 
                "margin": "0 5px", 
                "--hover-color": "#111111",
                "padding": "10px 0" # Natural height instead of fixed 50px
            },
            "nav-link-selected": {
                "background-color": "#000000", 
                "color": "#FFD700", # Active icon color
                "border-bottom": "2px solid #FFD700",
                "border-radius": "0px"
            }
        }
    )
    
    st.components.v1.html("""
    <script>
    (function() {

        const CSS = `
            /* All transitions use only opacity + transform — GPU-accelerated, zero layout reflow */
            .nav-link {
                position: relative !important;
                overflow: visible !important;
            }

            /* Icon: smooth fade + shrink on hover */
            .nav-link i, .nav-link svg {
                transition: opacity 0.22s ease, transform 0.22s ease !important;
                opacity: 1;
                transform: scale(1);
            }
            .nav-link:hover i, .nav-link:hover svg {
                opacity: 0 !important;
                transform: scale(0.5) !important;
            }

            /* Label span: absolutely centred, always at correct font-size, just invisible */
            .nav-label {
                position: absolute !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                font-size: 12px !important;
                font-weight: 500 !important;
                opacity: 0 !important;
                transition: opacity 0.22s ease !important;
                white-space: nowrap !important;
                color: #e2e8f0 !important;
                font-family: 'Space Grotesk', sans-serif !important;
                pointer-events: none !important;
                letter-spacing: 0.4px !important;
            }
            .nav-link:hover .nav-label {
                opacity: 1 !important;
            }

            /* Active tab: icon gone, label gold */
            .nav-link-selected i, .nav-link-selected svg {
                opacity: 0 !important;
                transform: scale(0.5) !important;
            }
            .nav-link-selected .nav-label {
                opacity: 1 !important;
                color: #FFD700 !important;
                font-weight: 600 !important;
            }
        `;

        function processIframe(iframe) {
            try {
                const doc = iframe.contentDocument;
                if (!doc || !doc.body) return;

                const links = doc.querySelectorAll('.nav-link');
                if (!links.length) return;

                // Inject CSS once
                if (!doc.head.querySelector('#sq-nav-css')) {
                    const s = doc.createElement('style');
                    s.id = 'sq-nav-css';
                    s.textContent = CSS;
                    doc.head.appendChild(s);
                }

                // Wrap bare text nodes in .nav-label spans (idempotent)
                links.forEach(link => {
                    if (link.querySelector('.nav-label')) return;
                    const textNode = Array.from(link.childNodes)
                        .find(n => n.nodeType === 3 && n.textContent.trim().length > 0);
                    if (textNode) {
                        const span = doc.createElement('span');
                        span.className = 'nav-label';
                        span.textContent = textNode.textContent.trim();
                        textNode.replaceWith(span);
                    }
                });

            } catch (e) {}
        }

        function scanAll() {
            parent.document.querySelectorAll('iframe').forEach(f => {
                if (f.contentDocument && f.contentDocument.readyState === 'complete') {
                    processIframe(f);
                } else {
                    f.addEventListener('load', () => processIframe(f), { once: true });
                }
            });
        }

        // Watch for iframes being dynamically added by Streamlit
        new MutationObserver(scanAll)
            .observe(parent.document.body, { childList: true, subtree: true });

        // Retries with increasing delays to handle all load timings
        [0, 150, 400, 900, 1800].forEach(t => setTimeout(scanAll, t));

    })();
    </script>
    """, height=0)
    
    if selected_tab == "Tracker":
        filtered_data = stock_data[
            (stock_data["Buy Score"] >= min_score) & 
            (stock_data["RSI"] <= max_rsi) & 
            (stock_data["Market Cap"] >= min_mcap_cr * 10000000)
        ]
        if stock_filter:
            filtered_data = filtered_data[filtered_data["Company Name"].isin(stock_filter)]
            
        def render_cards_html(df_chunk):
            html = "<div class='card-grid'>"
            for row in df_chunk.to_dict(orient="records"):
                direction = "positive" if row["% Change"] > 0 else "negative" if row["% Change"] < 0 else "neutral"
                sign = "+" if row["% Change"] > 0 else ""
                color_hex = "#00F0FF" if row["% Change"] > 0 else "#FF0055" if row["% Change"] < 0 else "#555555"
                
                ticker = REVERSE_LOOKUP[row['Company Name']]
                svg_chart = ""
                if not sparkline_data.empty and ticker in sparkline_data.columns:
                    svg_chart = generate_svg_sparkline(sparkline_data[ticker].dropna(), color_hex)
                
                html += f"""
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
"""
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
                    
        top_data = filtered_data.head(8)
        rest_data = filtered_data.iloc[8:]
        
        render_cards_html(top_data)
        
        if not rest_data.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("VIEW ALL QUALIFYING ASSETS", expanded=False):
                render_cards_html(rest_data)


    if selected_tab == "Portfolio":
        st.markdown("### My Personal Portfolio")
        if not st.session_state.user:
            st.warning("🔒 You must be logged in to view and manage your personal portfolio.")
            st.info("Use the Secure Authentication Gateway on the main screen to log in or register.")
        else:
            email = st.session_state.user["email"]
            st.markdown(f"<p style='color: #94a3b8;'>Logged in as: <strong>{email}</strong></p>", unsafe_allow_html=True)
            
            with st.expander("➕ Add Asset to Portfolio", expanded=False):
                with st.form("add_portfolio_form", clear_on_submit=True):
                    cols = st.columns([3, 1.5, 1.5, 1.5])
                    with cols[0]:
                        sel_stock = st.selectbox("Select Asset from 2700+ Universe", options=sorted(list(FULL_UNIVERSE.values())))
                    with cols[1]:
                        qty = st.number_input("Quantity", min_value=1, step=1)
                    with cols[2]:
                        user_price = st.number_input("Purchase Price (₹)", min_value=0.0, format="%.2f", help="Leave 0.0 to use Live Price")
                    with cols[3]:
                        st.markdown("<br>", unsafe_allow_html=True)
                        submit_add = st.form_submit_button("Add to Portfolio", width="stretch")
                    
                    if submit_add:
                        symbol = REVERSE_FULL_UNIVERSE.get(sel_stock, "")
                        
                        if user_price > 0.0:
                            final_price = user_price
                        else:
                            live_row = stock_data[stock_data["Symbol"] == symbol]
                            if not live_row.empty:
                                final_price = float(live_row.iloc[0]["Live Price (₹)"])
                            else:
                                try:
                                    import yfinance as yf
                                    tkr = yf.Ticker(symbol)
                                    final_price = float(tkr.fast_info.last_price)
                                except Exception:
                                    final_price = 0.0
                                
                        success, msg = add_to_portfolio(email, symbol, sel_stock, final_price, qty)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                            
            # Load Portfolio
            holdings = get_user_portfolio(email)
            if not holdings:
                st.info("Your portfolio is currently empty. Add assets using the form above.")
            else:
                total_invested = 0
                current_value = 0
                
                # Fetch live prices for holdings
                portfolio_display = []
                for h in holdings:
                    sym = h["symbol"]
                    qty = h["quantity"]
                    buy_px = h["buy_price"]
                    
                    invested = qty * buy_px
                    total_invested += invested
                    
                    # Get live price from stock_data if available, otherwise fetch dynamically
                    live_row = stock_data[stock_data["Symbol"] == sym]
                    if not live_row.empty:
                        live_px = float(live_row.iloc[0]["Live Price (₹)"])
                    else:
                        try:
                            import yfinance as yf
                            tkr = yf.Ticker(sym)
                            live_px = float(tkr.fast_info.last_price)
                        except Exception:
                            live_px = buy_px
                    
                    curr_val = qty * live_px
                    current_value += curr_val
                    
                    profit = curr_val - invested
                    profit_pct = (profit / invested) * 100 if invested > 0 else 0
                    
                    portfolio_display.append({
                        "Symbol": sym,
                        "Company": h.get("company_name", sym),
                        "Shares": qty,
                        "Avg Buy (₹)": buy_px,
                        "Live Price (₹)": live_px,
                        "P&L (₹)": profit,
                        "P&L (%)": profit_pct
                    })
                
                # Summary Cards
                total_profit = current_value - total_invested
                total_profit_pct = (total_profit / total_invested) * 100 if total_invested > 0 else 0
                
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.markdown(f"<div class='metric-card'><h4>Total Invested</h4><div class='metric-value'>₹{total_invested:,.2f}</div></div>", unsafe_allow_html=True)
                with mc2:
                    st.markdown(f"<div class='metric-card'><h4>Current Value</h4><div class='metric-value'>₹{current_value:,.2f}</div></div>", unsafe_allow_html=True)
                with mc3:
                    color = "#00F0FF" if total_profit >= 0 else "#FF0055"
                    sign = "+" if total_profit >= 0 else ""
                    st.markdown(f"<div class='metric-card' style='border-left-color: {color} !important;'><h4>Overall P&L</h4><div class='metric-value' style='color:{color};'>{sign}₹{total_profit:,.2f} ({sign}{total_profit_pct:.2f}%)</div></div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                import pandas as pd
                df_port = pd.DataFrame(portfolio_display)
                
                # Display dataframe
                st.dataframe(
                    df_port.style.format({
                        "Avg Buy (₹)": "{:.2f}",
                        "Live Price (₹)": "{:.2f}",
                        "P&L (₹)": "{:+.2f}",
                        "P&L (%)": "{:+.2f}%"
                    }).map(lambda x: "color: #00F0FF;" if isinstance(x, (int, float)) and x > 0 else "color: #FF0055;" if isinstance(x, (int, float)) and x < 0 else "", subset=["P&L (₹)", "P&L (%)"]),
                    hide_index=True,
                    width="stretch"
                )
                
                st.markdown("### AI Predictions for Your Holdings")
                pred_cols = st.columns(3)
                col_idx = 0
                for h in holdings:
                    sym = h["symbol"]
                    pred = get_ml_prediction_for_symbol(sym)
                    if pred:
                        pred_color = "#10b981" if pred['change'] > 0 else "#ef4444"
                        pred_sign = "+" if pred['change'] > 0 else ""
                        with pred_cols[col_idx % 3]:
                            st.markdown(f"<div style='border-left: 3px solid {pred_color}; padding: 12px; background: rgba(0,0,0,0.15); border-radius: 6px; margin-bottom: 10px;'>", unsafe_allow_html=True)
                            st.markdown(f"<div style='font-size:0.85rem; color:#64748b;'>{sym}</div>", unsafe_allow_html=True)
                            st.markdown(f"<h5 style='margin-top:2px; margin-bottom:4px;'>Forecast: <span style='color: {pred_color};'>₹{pred['price']:.2f}</span></h5>", unsafe_allow_html=True)
                            st.markdown(f"<div style='font-size:0.8rem; color: #94a3b8;'>Change: <strong style='color: {pred_color};'>{pred_sign}{pred['change']:.2f}%</strong></div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                        col_idx += 1
                        
                if col_idx == 0:
                    st.info("No ML predictions available for your current holdings.")
                
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("Manage Holdings (Edit or Remove)"):
                    manage_sym = st.selectbox("Select Asset to Manage", options=[h["Symbol"] for h in portfolio_display])
                    
                    # Find current qty and price for the selected asset
                    current_asset = next((h for h in portfolio_display if h["Symbol"] == manage_sym), None)
                    if current_asset:
                        edit_cols = st.columns(3)
                        with edit_cols[0]:
                            new_qty = st.number_input("Update Quantity", min_value=1, step=1, value=int(current_asset["Shares"]))
                        with edit_cols[1]:
                            new_price = st.number_input("Update Purchase Price (₹)", min_value=0.0, format="%.2f", value=float(current_asset["Avg Buy (₹)"]))
                        with edit_cols[2]:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("Save Changes", type="secondary", use_container_width=True):
                                suc, m = update_portfolio(email, manage_sym, new_price, new_qty)
                                if suc:
                                    st.success(m)
                                    st.rerun()
                                else:
                                    st.error(m)
                    
                    st.markdown("---")
                    if st.button("Remove Selected Asset", type="primary"):
                        suc, m = remove_from_portfolio(email, manage_sym)
                        if suc:
                            st.success(m)
                            st.rerun()
                        else:
                            st.error(m)

    if selected_tab == "Charts":
        st.markdown("### Technical Price Action & Shariah Compliance")
        
        if not UNIVERSE_METRICS_DF.empty:
            # Source options from the 2700+ Master Database, but only allow Halal assets
            halal_universe = UNIVERSE_METRICS_DF[UNIVERSE_METRICS_DF['is_compliant'] == True].copy()
            halal_universe = halal_universe.sort_values(by="Company Name")
            
            options = halal_universe["Company Name"].tolist()
            selected_stock_chart = st.selectbox("Select Asset for Technical Analysis:", options=options, key="chart_select")
            
            # Look up the ticker in the master database
            selected_ticker = halal_universe[halal_universe['Company Name'] == selected_stock_chart].iloc[0]['Symbol']
        else:
            # Fallback to the hardcoded list
            selected_stock_chart = st.selectbox("Select Asset for Technical Analysis:", options=stock_data["Company Name"].tolist(), key="chart_select")
            selected_ticker = REVERSE_LOOKUP.get(selected_stock_chart, stock_data["Symbol"].iloc[0])
        
        if not UNIVERSE_METRICS_DF.empty and selected_ticker in UNIVERSE_METRICS_DF['Symbol'].values:
            row_data = UNIVERSE_METRICS_DF[UNIVERSE_METRICS_DF['Symbol'] == selected_ticker].iloc[0]
            if 'debt_ratio' in row_data and not pd.isna(row_data['debt_ratio']):
                debt = row_data.get('debt_ratio', 0) * 100
                liq = row_data.get('liquidity_ratio', 0) * 100
                rec = row_data.get('receivables_ratio', 0) * 100
                is_comp = row_data.get('is_compliant', False)
                
                status_color = "#10b981" if is_comp else "#ef4444"
                status_text = "HALAL (PASS)" if is_comp else "HARAM (FAIL)"
                
                st.markdown(f"<div style='border: 1px solid {status_color}; border-left: 5px solid {status_color}; padding: 15px; border-radius: 8px; margin-bottom: 20px; background: rgba(0,0,0,0.2);'> <h4 style='margin-top: 0; color: {status_color}; margin-bottom: 15px;'>AAOIFI Shariah Compliance: {status_text}</h4> <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-family: monospace; font-size: 0.95rem; color: #e2e8f0;'> <div><strong style='color: #94a3b8;'>Debt Ratio:</strong><br><span style='font-size: 1.2rem; color: {'#10b981' if debt < 33 else '#ef4444'}'>{debt:.1f}%</span> <span style='font-size: 0.8rem; color: #64748b;'>(Limit 33%)</span></div> <div><strong style='color: #94a3b8;'>Liquidity:</strong><br><span style='font-size: 1.2rem; color: {'#10b981' if liq < 33 else '#ef4444'}'>{liq:.1f}%</span> <span style='font-size: 0.8rem; color: #64748b;'>(Limit 33%)</span></div> <div><strong style='color: #94a3b8;'>Receivables:</strong><br><span style='font-size: 1.2rem; color: {'#10b981' if rec < 33 else '#ef4444'}'>{rec:.1f}%</span> <span style='font-size: 0.8rem; color: #64748b;'>(Limit 33%)</span></div> </div> </div>", unsafe_allow_html=True)
            
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
                st.plotly_chart(fig, width="stretch")
                
                # --- ML PREDICTION INTEGRATION ---
                st.markdown("### 🤖 ML Price Prediction (LSTM + Sentiment)")
                if os.path.exists("best_model.pth"):
                    try:
                        import torch
                        import numpy as np
                        from sklearn.preprocessing import MinMaxScaler
                        from ml_model import StockPredictorLSTM
                        
                        # Load Sentiment
                        sentiment_data = {}
                        if os.path.exists("sentiment_data.json"):
                            with open("sentiment_data.json", "r", encoding="utf-8") as f:
                                sentiment_data = json.load(f)
                                
                        sym_sent = sentiment_data.get(selected_ticker, {}).get("score", 0.0)
                        
                        # Prepare data
                        seq_length = 30
                        if len(stock_history) >= seq_length:
                            df_ml = stock_history[['Open', 'High', 'Low', 'Close', 'Volume']].tail(seq_length).copy()
                            if isinstance(df_ml.columns, pd.MultiIndex):
                                df_ml.columns = df_ml.columns.get_level_values(0)
                            df_ml['Sentiment'] = sym_sent
                            
                            scaler = MinMaxScaler()
                            # We fit on this small window for simplicity in inference (or load global scaler if we saved it)
                            scaled_data = scaler.fit_transform(df_ml.values)
                            
                            x_tensor = torch.tensor(scaled_data, dtype=torch.float32).unsqueeze(0)
                            
                            device = torch.device('cpu')
                            model = StockPredictorLSTM(input_dim=6, hidden_dim=64, num_layers=2, output_dim=1).to(device)
                            model.load_state_dict(torch.load("best_model.pth", map_location=device))
                            model.eval()
                            
                            with torch.no_grad():
                                pred_scaled = model(x_tensor).item()
                                
                            # Inverse transform: create a dummy array with 6 columns to inverse transform
                            dummy = np.zeros((1, 6))
                            dummy[0, 3] = pred_scaled  # Close is index 3
                            pred_price = scaler.inverse_transform(dummy)[0, 3]
                            
                            current_px = close_data.iloc[-1]
                            pred_change = ((pred_price - current_px) / current_px) * 100
                            
                            pred_color = "#10b981" if pred_change > 0 else "#ef4444"
                            pred_sign = "+" if pred_change > 0 else ""
                            
                            st.markdown(f"<div style='border-left: 4px solid {pred_color}; padding: 15px; background: rgba(0,0,0,0.15); border-radius: 6px;'>", unsafe_allow_html=True)
                            st.markdown(f"<h4 style='margin-top:0;'>Next Day Forecast: <span style='color: {pred_color};'>₹{pred_price:.2f}</span></h4>", unsafe_allow_html=True)
                            st.markdown(f"<p style='margin-bottom:0; color: #94a3b8;'>Predicted Change: <strong style='color: {pred_color};'>{pred_sign}{pred_change:.2f}%</strong> (Based on 30-day technicals & FinBERT sentiment score: {sym_sent:.2f})</p>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                        else:
                            st.warning("Not enough historical data to generate ML prediction.")
                    except Exception as e:
                        st.error(f"Failed to run ML Inference: {e}")
                else:
                    st.info("The ML Model hasn't been trained yet. Run `python train_model.py` to activate predictions.")

    if selected_tab == "News":
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
                
    if selected_tab == "Accuracy":
        st.markdown("### 30-Day Predictive Backtest")
        st.write("This engine simulates applying the Shareq algorithm 30 days in the past to see if its 'Strong Buy' recommendations (Score ≥ 85) successfully predicted a price increase.")
        
        with st.spinner("Simulating historical algorithm telemetry..."):
            backtest_df = calculate_backtest_accuracy(days_ago=30)
            
            if not backtest_df.empty:
                wins = len(backtest_df[backtest_df['Outcome'] == 'WIN'])
                total = len(backtest_df)
                win_rate = (wins / total) * 100 if total > 0 else 0
                
                color = "#00F0FF" if win_rate > 50 else "#FF0055"
                st.markdown(f"<div style='margin: 20px 0; padding: 20px; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(148, 163, 184, 0.1); border-left: 3px solid {color}; border-radius: 12px;'> <h3 style='margin:0; font-weight: 300; font-family: \"Space Grotesk\", sans-serif; color: var(--text-color);'>Win Rate: <span style='color:{color}'>{win_rate:.1f}%</span></h3> <p style='margin: 5px 0 0 0; color: var(--text-color); opacity: 0.6;'>{wins} successful predictions out of {total} strong buy signals triggered across the Universal Database exactly 30 days ago.</p> </div>", unsafe_allow_html=True)
                
                def style_outcome(val):
                    color = '#22c55e' if val == 'WIN' else '#ef4444' if val == 'LOSS' else 'inherit'
                    return f'color: {color}; font-weight: bold;'
                
                # --- Pagination ---
                page_size = 10
                total_rows = len(backtest_df)
                total_pages = max(1, (total_rows - 1) // page_size + 1)
                
                if "bt_page" not in st.session_state:
                    st.session_state.bt_page = 1
                st.session_state.bt_page = min(st.session_state.bt_page, total_pages)
                
                start_idx = (st.session_state.bt_page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_df = backtest_df.iloc[start_idx:end_idx].style.map(style_outcome, subset=['Outcome'])
                
                st.dataframe(
                    paginated_df,
                    column_config={
                        "Price 30d Ago": st.column_config.NumberColumn(format="₹%.2f"),
                        "Price Today": st.column_config.NumberColumn(format="₹%.2f"),
                        "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
                    }, hide_index=True, width="stretch"
                )
                
                pc1, pc2, pc3 = st.columns([1, 2, 1])
                with pc1:
                    if st.button("⬅️ Previous", key="bt_prev", disabled=(st.session_state.bt_page <= 1), use_container_width=True):
                        st.session_state.bt_page -= 1
                        st.rerun()
                with pc2:
                    st.markdown(f"<div style='text-align: center; padding: 5px; color: #94a3b8; font-size: 0.9rem;'>Page {st.session_state.bt_page} of {total_pages} (Showing {start_idx+1}-{min(end_idx, total_rows)} of {total_rows})</div>", unsafe_allow_html=True)
                with pc3:
                    if st.button("Next ➡️", key="bt_next", disabled=(st.session_state.bt_page >= total_pages), use_container_width=True):
                        st.session_state.bt_page += 1
                        st.rerun()
            else:
                st.info("No 'Strong Buy' signals were triggered 30 days ago by the algorithm parameters.")
                
            st.markdown("---")
            st.markdown("### LSTM AI Model Backtest")
            st.write("Simulates the LSTM PyTorch model dynamically 30 days in the past on a random sample to see if its directional prediction was correct.")
            with st.spinner("Simulating ML forward-predictions..."):
                ml_backtest_df = calculate_ml_backtest_accuracy(days_ago=30, sample_size=20)
                if not ml_backtest_df.empty:
                    ml_wins = len(ml_backtest_df[ml_backtest_df['Outcome'] == 'WIN'])
                    ml_total = len(ml_backtest_df)
                    ml_win_rate = (ml_wins / ml_total) * 100 if ml_total > 0 else 0
                    
                    ml_color = "#00F0FF" if ml_win_rate > 50 else "#FF0055"
                    st.markdown(f"<div style='margin: 20px 0; padding: 20px; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(148, 163, 184, 0.1); border-left: 3px solid {ml_color}; border-radius: 12px;'> <h3 style='margin:0; font-weight: 300; font-family: \"Space Grotesk\", sans-serif; color: var(--text-color);'>ML Win Rate: <span style='color:{ml_color}'>{ml_win_rate:.1f}%</span></h3> <p style='margin: 5px 0 0 0; color: var(--text-color); opacity: 0.6;'>{ml_wins} correct directional predictions out of {ml_total} sampled stocks exactly 30 days ago.</p> </div>", unsafe_allow_html=True)
                    
                    # --- Pagination for ML Backtest ---
                    ml_page_size = 10
                    ml_total_rows = len(ml_backtest_df)
                    ml_total_pages = max(1, (ml_total_rows - 1) // ml_page_size + 1)
                    
                    if "ml_bt_page" not in st.session_state:
                        st.session_state.ml_bt_page = 1
                    st.session_state.ml_bt_page = min(st.session_state.ml_bt_page, ml_total_pages)
                    
                    ml_start_idx = (st.session_state.ml_bt_page - 1) * ml_page_size
                    ml_end_idx = ml_start_idx + ml_page_size
                    ml_paginated_df = ml_backtest_df.iloc[ml_start_idx:ml_end_idx].style.map(style_outcome, subset=['Outcome'])
                    
                    st.dataframe(
                        ml_paginated_df,
                        column_config={
                            "Predicted Price": st.column_config.NumberColumn(format="₹%.2f"),
                            "Actual Price": st.column_config.NumberColumn(format="₹%.2f"),
                            "Diff (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                        }, hide_index=True, width="stretch"
                    )
                    
                    mpc1, mpc2, mpc3 = st.columns([1, 2, 1])
                    with mpc1:
                        if st.button("⬅️ Previous", key="ml_bt_prev", disabled=(st.session_state.ml_bt_page <= 1), use_container_width=True):
                            st.session_state.ml_bt_page -= 1
                            st.rerun()
                    with mpc2:
                        st.markdown(f"<div style='text-align: center; padding: 5px; color: #94a3b8; font-size: 0.9rem;'>Page {st.session_state.ml_bt_page} of {ml_total_pages} (Showing {ml_start_idx+1}-{min(ml_end_idx, ml_total_rows)} of {ml_total_rows})</div>", unsafe_allow_html=True)
                    with mpc3:
                        if st.button("Next ➡️", key="ml_bt_next", disabled=(st.session_state.ml_bt_page >= ml_total_pages), use_container_width=True):
                            st.session_state.ml_bt_page += 1
                            st.rerun()
                else:
                    st.info("No ML predictions could be simulated for the target date. Check if best_model.pth is available.")

    if selected_tab == "Combos":
        st.markdown("### 2,700-Stock Universal AI Screener & SIP Projections")
        st.write("These algorithmic portfolios mathematically filter the **entire 2,700+ Shariah-compliant universe** based on your specific risk profile and SIP budget.")
        
        if st.button("🌟 1-Click: Best FUNDAMENTAL SCORE 90+ Portfolios", use_container_width=True):
            st.session_state["sip_input"] = 10000
            st.session_state["risk_input"] = "Balanced"
            st.session_state["strat_input"] = "Fundamental Score 90+ (Quality)"
            st.session_state["force_run_combos"] = True
            
        with st.form("universal_screener_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                monthly_sip = st.number_input("Monthly SIP (₹)", min_value=1000, max_value=500000, value=10000, step=1000, key="sip_input")
            with col2:
                risk_profile = st.selectbox("Risk Tolerance", ["Balanced", "Conservative (Low Risk)", "Aggressive (High Risk)"], key="risk_input")
            with col3:
                strategy = st.selectbox("Strategy Goal", ["Growth (Momentum)", "Value (Low P/E)", "Income (Dividends)", "Fundamental Score 90+ (Quality)"], key="strat_input")
                
            submitted = st.form_submit_button("Execute Global Market Scan", use_container_width=True)
            
        if submitted or st.session_state.get("force_run_combos"):
            st.session_state["force_run_combos"] = False
            with st.spinner("Synthesizing algorithmic portfolios..."):
                portfolios = generate_dynamic_portfolios(stock_data, monthly_sip, risk_profile, strategy)
            
            st.markdown("<div style='margin-bottom: 25px; padding: 15px; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); display: flex; flex-wrap: wrap; gap: 15px; font-size: 0.75rem;'> <div style='color: #94a3b8; margin-right: 10px; font-weight: 600; font-family: \"Space Grotesk\", sans-serif; letter-spacing: 1px;'>SECTOR LEGEND</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #0ea5e9;'></span> Tech/IT</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #10b981;'></span> Pharma/Healthcare</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #8b5cf6;'></span> Auto/Financials</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #eab308;'></span> Consumer/Energy</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #ec4899;'></span> FMCG/Real Estate</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #06b6d4;'></span> Chemicals/Utilities</div> <div style='display: flex; align-items: center; gap: 6px;'><span style='width: 10px; height: 10px; border-radius: 50%; background: #64748b;'></span> Industrials/Others</div> </div>", unsafe_allow_html=True)
        else:
            st.info("Set your parameters and click Run Universal Screener to generate custom portfolios.")
            portfolios = {}
        
        for p_name, p_data_info in portfolios.items():
            holding_defs = p_data_info["holdings"]
            if not holding_defs: 
                # Don't render empty portfolios
                continue
            
            p_tickers_no_ns = [h["ticker"] for h in holding_defs]
            p_tickers = [h.get("full_ticker", h["ticker"] + ".NS") for h in holding_defs]
            p_data = stock_data[stock_data["Symbol"].isin(p_tickers_no_ns)]
            
            cagr = fetch_portfolio_cagr(p_tickers)
            monthly_deployed = p_data_info.get("monthly_invested", monthly_sip)
            future_value = calculate_future_value(monthly_deployed, cagr, p_data_info["horizon"])
            total_invested = monthly_deployed * 12 * p_data_info["horizon"]
            
            # Precise dynamic calculations
            active_assets = len(holding_defs)
            avg_score = sum([h.get("score", 85.0) for h in holding_defs]) / active_assets if active_assets > 0 else 0
            avg_return = p_data["% Change"].mean() if not p_data.empty else 0.0
            
            if avg_score >= 80: p_color = "#10b981" # Green
            elif avg_score >= 60: p_color = "#f59e0b" # Orange
            else: p_color = "#ef4444" # Red
            
            return_color = "#10b981" if avg_return > 0 else "#ef4444"
            
            holdings_html = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 20px;'>"
            for h in holding_defs:
                qty = h.get("qty", 0)
                actual_spend = h.get("actual_spend", 0)
                live_price = h.get("price", 1)
                
                holdings_html += f"<div style='background: rgba(0,0,0,0.15); padding: 12px 16px; border-radius: 4px; border-left: 2px solid {h['color']};'><div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;'><strong style='color: #f1f5f9; font-size: 0.95rem; font-family: \"Space Grotesk\", sans-serif;'>{h['ticker']}</strong><span style='color: #e2e8f0; font-weight: 500; font-size: 0.85rem;'>₹{actual_spend:,.0f}</span></div><div style='display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-size: 0.75rem;'><span>{qty} shares @ ₹{live_price:,.0f}</span><span>Alloc: {h['weight']:.1f}%</span></div></div>"
            
            uninvested = p_data_info.get("uninvested_cash", 0)
            if uninvested > 0:
                holdings_html += f"<div style='background: rgba(255,255,255,0.02); padding: 12px 16px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;'><span style='color: #94a3b8; font-size: 0.85rem;'>Uninvested Cash Balance</span><span style='color: #e2e8f0; font-weight: 500; font-size: 0.85rem;'>₹{uninvested:,.0f}</span></div>"
            holdings_html += "</div>"
            
            clean_name = p_name.replace("🛡️", "").replace("🚀", "").replace("⚖️", "").strip()
            
            st.markdown(f"""
<div style='margin-bottom: 30px; padding: 25px; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(148, 163, 184, 0.1); border-radius: 6px;'>
    <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 25px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 15px;'>
        <div>
            <h3 style='margin:0 0 5px 0; font-family: "Space Grotesk", sans-serif; font-size: 1.2rem; font-weight: 600; color: #f8fafc;'>{clean_name}</h3>
            <div style='color: #94a3b8; font-size: 0.8rem; letter-spacing: 0.5px;'>INSTITUTIONAL SIP PROJECTION</div>
        </div>
        <div style='text-align: right;'>
            <div style='font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px;'>FUNDAMENTAL SCORE</div>
            <div style='font-size: 1.5rem; font-weight: 600; color: {p_color};'>{avg_score:.1f}</div>
        </div>
    </div>
    <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px;'>
        <div>
            <div style='color: #94a3b8; font-size: 0.75rem; margin-bottom: 4px; text-transform: uppercase;'>Total Invested</div>
            <div style='font-size: 1.1rem; font-weight: 500; color: #e2e8f0;'>₹{total_invested:,.0f}</div>
        </div>
        <div>
            <div style='color: #94a3b8; font-size: 0.75rem; margin-bottom: 4px; text-transform: uppercase;'>Projected Value</div>
            <div style='font-size: 1.1rem; font-weight: 500; color: #10b981;'>₹{future_value:,.0f}</div>
        </div>
        <div>
            <div style='color: #94a3b8; font-size: 0.75rem; margin-bottom: 4px; text-transform: uppercase;'>Hist. 5Y CAGR</div>
            <div style='font-size: 1.1rem; font-weight: 500; color: #8b5cf6;'>{cagr*100:.1f}%</div>
        </div>
        <div>
            <div style='color: #94a3b8; font-size: 0.75rem; margin-bottom: 4px; text-transform: uppercase;'>Active Assets</div>
            <div style='font-size: 1.1rem; font-weight: 500; color: #e2e8f0;'>{active_assets}</div>
        </div>
    </div>
    {holdings_html}
</div>
""", unsafe_allow_html=True)

    if selected_tab == "Guide":
        st.markdown("""
        ### 📖 How Shareq Equities Works
        
        Welcome to **Shareq Equities**, an institutional-grade, Shariah-compliant algorithmic screener. This dashboard does not just show you prices; it uses complex mathematics to find the absolute best assets to buy *today*.
        
        #### 1. The Algorithmic Buy Score
        The LIVE TRACKER tab displays the top Shariah-compliant assets, ranked by our proprietary Buy Score. 
        - **How to use it:** Look for assets with a score of 85 or higher—these are flagged as "Strong Buys". You can use the sliders in the left sidebar to filter the dashboard and find stocks that match your exact risk profile.
        
        #### 2. Portfolio Combos (Smart SIP Allocator)
        The PORTFOLIO COMBOS tab builds complete investment portfolios for you based on different time horizons.
        - **How to use it:** Simply drag the "Monthly SIP Investment" slider to match your budget. The Smart Engine will automatically calculate exactly how many shares of each stock you should buy today so that you don't waste a single rupee. It even calculates your projected 5-year returns!
        
        #### 3. Real-World Backtesting
        The ALGO ACCURACY tab proves whether the algorithm actually works by tracking its historical performance.
        - **How to use it:** Click the tab to see a verified Win/Loss percentage. The system automatically looks back exactly 30 days into our live cloud database, checks what the algorithm recommended back then, and compares it to the live prices today.
        
        #### 4. Shareq AI Core
        The Shareq AI Core acts as your personal, institutional-grade quantitative analyst.
        - **How to use it:** Enter your free Google Gemini API Key into the left sidebar to unlock the AI terminal. You can ask it to analyze any stock on the dashboard (e.g., "Give me a breakdown of TCS financials"), and it will instantly respond with deep, context-aware insights.
        """)