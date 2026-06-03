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

- **Momentum Filter:** `+15` points if the current price is above the 50-day Simple Moving Average (SMA50).
- **RSI Filter:** `+20` points if RSI < 40 (Oversold/Undervalued indicator); `-20` points if RSI > 70 (Overbought/Overvalued indicator).
- **Debt Compliance:** `+15` points if the debt-to-equity ratio is below 33% (a core Shariah financial ratio screening parameter).
- **Strong Buy Signal:** Achieved when the total score is `≥ 75`.

---

## Installation & Setup

Follow these steps to set up and run the application locally:

### 1. Clone or Download the Repository
Extract the project files into your local directory.

### 2. Set Up a Virtual Environment (Recommended)
Create and activate a virtual environment to manage dependencies:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required packages:
```bash
pip install streamlit yfinance pandas plotly requests google-generativeai
```

### 4. Run the Application
Execute the Streamlit application from your terminal:
```bash
streamlit run halal_dashboard.py
py -m streamlit run halal_dashboard.py
```
*(Alternatively, if Streamlit is not added to your PATH: `python -m streamlit run halal_dashboard.py`)*

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
