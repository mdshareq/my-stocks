import pandas as pd
import yfinance as yf

HALAL_STOCKS = {"TCS.NS": "TCS", "INFY.NS": "Infosys", "WIPRO.NS": "Wipro"}

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

def fetch_live_and_spark_data():
    tickers = list(HALAL_STOCKS.keys())
    data = []
    
    nifty = yf.download("^NSEI", period="2y", interval="1d", progress=False)
    market_healthy = True
    if not nifty.empty and len(nifty) >= 50:
        nifty_close = nifty["Close"]
        if isinstance(nifty_close, pd.DataFrame):
            nifty_close = nifty_close.iloc[:, 0]
        nifty_sma50 = nifty_close.rolling(window=50).mean().iloc[-1]
        nifty_price = nifty_close.iloc[-1]
        market_healthy = bool(float(nifty_price) > float(nifty_sma50))
        
    live_data = yf.download(tickers, period="2y", interval="1d", progress=False, group_by="ticker")
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            if isinstance(live_data.columns, pd.MultiIndex) and ticker in live_data.columns.levels[0]:
                hist = live_data[ticker].copy()
            elif "Close" in live_data.columns and len(tickers) == 1:
                hist = live_data.copy()
            else:
                continue
                
            if hist.empty or len(hist) < 200: continue
            
            current_price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2]
            
            sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
            sma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]
            current_rsi = calculate_rsi(hist).iloc[-1]
            macd, signal = calculate_macd(hist)
            upper_bb, lower_bb = calculate_bollinger_bands(hist)
            
            score = 50 
            
            if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                score += 15
            elif macd.iloc[-1] > signal.iloc[-1]:
                score += 5
                
            if current_price <= lower_bb.iloc[-1] * 1.02:
                score += 10
                
            if not market_healthy:
                score -= 15
            
            data.append({"Symbol": ticker, "Buy Score": score})
        except Exception as e:
            print(f"Error on {ticker}: {e}")

    df = pd.DataFrame(data)
    print(df)

fetch_live_and_spark_data()
