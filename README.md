# Shareq Equities

**Institutional Shariah-Compliant Algorithmic Screener**

Shareq Equities is a modern, futuristic web dashboard built with Streamlit that tracks, analyzes, and provides AI-driven insights on the top 50 Shariah-compliant Indian stocks. It features algorithmic buy scoring, historical backtesting, real-time news radar, and interactive technical charts.


---

## Key Features

- **Live Market Tracker:** Real-time tracking of top 50 Halal stocks with custom SVG Sparklines showing 30-day closing trends, Relative Strength Index (RSI), and Simple Moving Average (SMA50) metrics.
- **Algorithmic Buy Score:** A proprietary algorithmic score evaluating stock momentum, RSI, and debt-to-equity ratios.
- **Advanced AI Advisor:** Integrated with Google's Gemini Pro AI to provide minimalist, institutional financial insights via an interactive chat terminal (requires API Key).
- **Advanced Charts:** Interactive 90-day technical price action charts powered by Plotly.
- **News Radar:** Fetches recent, relevant headlines from Google News RSS for any selected asset.
- **Algo Accuracy Backtester:** Simulates historical telemetry from 30 days ago to test the success rate of past 'Strong Buy' signals.
- **Futuristic UI:** Custom minimalist, dark-themed CSS with neon accents.

---

## Algorithmic Buy Score Logic

The screener evaluates each asset based on a proprietary algorithmic scoring system (Base: 50 points):

- **Trend & Momentum:** `+5` points if Price > 50-Day SMA. `+10` points if Price > 200-Day SMA.
- **MACD Crossover:** `+15` points for a fresh Bullish MACD Crossover, or `+5` points for ongoing bullish momentum.
- **Oversold Indicators (RSI & Bollinger):** `+10` points if RSI < 30 (`+5` if RSI < 40); `-20` points if RSI > 70. `+10` points if Price is at or below the Lower Bollinger Band.
- **Volume Surge:** `+10` points if current daily volume exceeds the 20-day average.
- **Shariah Financials:** `+10` points if Debt/Equity < 33%; `+10` points if Cash/Assets < 33%.
- **Broader Market Filter:** `-15` points penalty if the NIFTY 50 index is trading below its 50-Day SMA (protects against market crashes).
- **Strong Buy Signal:** Achieved when the total score is `≥ 85`.

---

## How to Run the App (Installation & Setup)

Follow these steps to set up and run the application locally on your machine:

### 1. Clone or Download the Repository
Open a terminal in the directory where you want the project to live, or extract the downloaded zip file into a folder.

### 2. Set Up a Virtual Environment (Recommended)
Create and activate a virtual environment to manage dependencies securely without breaking global Python packages:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required Python packages via pip:
```bash
pip install streamlit yfinance pandas plotly requests google-generativeai
```

### 4. Run the Application
Execute the Streamlit application from your terminal:
```bash
# Recommended command for Windows
py -m streamlit run halal_dashboard.py

# Alternative for macOS/Linux
streamlit run halal_dashboard.py
```
*(Once run, a browser tab will automatically open at `http://localhost:8501`)*

---

## Platform Navigation & Usage

- **System Settings (Sidebar):** Filter assets to monitor, trigger a manual scan, or configure the AI core.
- **API Key Management:** Input your Gemini API Key in the sidebar to activate the **Advanced AI Advisor** module. The key is securely saved locally to an `.env_gemini_key` file (which is ignored by Git via `.gitignore`) to preserve state across sessions.
- **Interactive Tabs:**
  - **📊 Live Tracker:** Grid view of all assets with dynamic sparkline charts and indicator telemetry.
  - **📈 Advanced Charts:** Deep dive into 90 days of historical price action.
  - **📰 News Radar:** RSS-parsed recent news feed regarding the selected stock.
  - **🎯 Algo Accuracy:** Displays the historical win-rate of the algorithm's recommendations from 30 days ago.

---

## Project Structure

- `halal_dashboard.py`: Core Streamlit application containing the dashboard layout, data fetching logic from `yfinance`, technical calculations, and the Gemini AI integration.
- `.gitignore`: Configured to exclude system caches, virtual environments, and the local `.env_gemini_key` file to prevent accidental leaks of your API keys.
- `README.md`: System documentation (this file).

---

## Disclaimer
This project is for educational and informational purposes only. The "Algorithmic Buy Score" and AI advice are simulated metrics and should not be considered professional financial advice. Always perform your own due diligence before making investment decisions.
