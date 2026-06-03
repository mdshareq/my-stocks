# Shareq Equities

**Institutional Shariah-Compliant Algorithmic Screener**

Shareq Equities is a modern, futuristic web dashboard built with Streamlit that tracks, analyzes, and provides AI-driven insights on the top 50+ Shariah-compliant Indian stocks. It features algorithmic buy scoring, dynamic portfolio generation, historical backtesting powered by Firebase, real-time news radar, and interactive technical charts.

---

## 🌟 Key Features

- **📊 Live Market Tracker:** Real-time tracking of Halal stocks with custom SVG Sparklines showing 30-day closing trends, Relative Strength Index (RSI), Simple Moving Average (SMA50), and 14-Day return metrics.
- **🧠 Algorithmic Buy Score:** A proprietary mathematical engine that evaluates stock momentum, MACD Crossovers, RSI, Bollinger Bands, and debt-to-equity ratios.
- **💼 Dynamic Model Portfolios:** A "Smart Waterfall Allocator" that takes your monthly SIP budget and dynamically builds Short-Term Momentum, Mid-Term Balanced, and Long-Term Compounder portfolios, calculating exact share quantities to buy without wasting a single rupee.
- **🤖 Advanced AI Advisor:** Integrated with Google's Gemini Pro AI to provide minimalist, institutional financial insights via an interactive chat terminal.
- **🗄️ Firebase Data Telemetry:** Secure, NoSQL data persistence that logs daily algorithmic snapshots to Firebase Firestore.
- **🎯 Real-World Backtesting:** The *Algo Accuracy* engine actively queries Firebase for predictions made exactly 30 days ago, comparing them to live prices today to calculate the algorithm's actual Win/Loss percentage.
- **📈 Advanced Charts & News:** Interactive 90-day technical price action charts and live RSS headlines from Google News.

---

## 📖 How to Use the App

### The Core Modules
- **System Settings (Sidebar):** Filter assets to monitor, trigger a manual scan, or configure the AI core by entering your Gemini API key.
- **Model Portfolios (SIP Calculator):** Drag the "Monthly SIP Investment" slider. The engine will instantly recalculate exactly which stocks you should buy today, how many shares you can afford, and exactly how much uninvested cash will be leftover in your brokerage.
- **Algo Accuracy Tab:** Check this tab to see a real-world backtest of how the algorithm's "Strong Buy" signals from 30 days ago actually performed in the market today.

### Setting up the Gemini AI Advisor
To unlock the Interactive Terminal:
1. Obtain an API Key from [Google AI Studio](https://aistudio.google.com/).
2. **Local Usage:** Paste it into the sidebar. It will securely save to a local `.env_gemini_key` file.
3. **Cloud Usage:** If deploying to Streamlit Cloud, add `GEMINI_API_KEY = "your-key"` to your App Settings -> Secrets.

---

## 🚀 Installation & Setup

Follow these steps to set up and run the application locally:

### 1. Clone the Repository
Open a terminal in the directory where you want the project to live.

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
Install all required Python packages via pip:
```bash
pip install -r requirements.txt
```

### 4. Firebase Configuration (Optional but Recommended)
To enable historical data telemetry and real-world backtesting:
1. Create a [Firebase Project](https://console.firebase.google.com/) with a Firestore database.
2. Generate a Service Account JSON key from your project settings.
3. Rename the downloaded file to exactly `.firebase_key.json` and place it in the root directory. *(Note: This file is ignored by git and will never be uploaded).*

### 5. Run the Application
Execute the Streamlit application from your terminal:
```bash
py -m streamlit run halal_dashboard.py
```
*(Once run, a browser tab will automatically open at `http://localhost:8501`)*

---

## ⚠️ Disclaimer
This project is for educational and informational purposes only. The "Algorithmic Buy Score", SIP Portfolios, and AI advice are simulated metrics and should not be considered professional financial advice. Always perform your own due diligence before making investment decisions.
