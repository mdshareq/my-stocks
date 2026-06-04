import json
import time
import os
import random
import requests
import yfinance as yf
import pandas as pd

# Configure custom session to avoid basic rate limits
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
})

def safe_get(df, index_name, default=0.0):
    """Safely extract a value from a yfinance dataframe, handling missing data."""
    if df is not None and not df.empty and index_name in df.index:
        try:
            val = df.loc[index_name].iloc[0]
            if pd.isna(val):
                return default
            return float(val)
        except Exception:
            return default
    return default

def main():
    print("Starting Halal Metrics Ingestion (yfinance Anti-Block Mode)...", flush=True)
    
    universe_path = "halal_universe.json"
    metrics_path = "halal_metrics.json"
    
    if not os.path.exists(universe_path):
        print(f"Error: {universe_path} not found.")
        return
        
    with open(universe_path, "r", encoding="utf-8") as f:
        universe = json.load(f)
        
    print(f"Loaded {len(universe)} symbols from universe.")
    
    metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            try:
                metrics = json.load(f)
            except json.JSONDecodeError:
                metrics = {}
                
    print(f"Found {len(metrics)} symbols already in metrics database.")
    
    pending_symbols = []
    for sym in universe.keys():
        if sym not in metrics:
            pending_symbols.append(sym)
        elif "error" in metrics[sym] and metrics[sym]["error"] != "invalid":
            pending_symbols.append(sym)
            
    print(f"Remaining symbols to fetch: {len(pending_symbols)}")
    
    # Chunking: Limit to 350 to stay under the radar
    batch_size = min(350, len(pending_symbols))
    batch_symbols = pending_symbols[:batch_size]
    
    print(f"Processing batch of {batch_size} symbols...")
    
    count = 0
    success_count = 0
    
    for symbol in batch_symbols:
        name = universe[symbol]
        count += 1
        if count % 10 == 0:
            print(f"Processed {count}/{batch_size} in this batch... (Success: {success_count})", flush=True)
            
        try:
            t = yf.Ticker(symbol, session=session)
            info = t.info
            
            # Use fast_info for price/mcap as it's faster and sometimes more reliable
            fast = t.fast_info
            
            price = fast.last_price if hasattr(fast, 'last_price') else info.get('currentPrice', 0.0)
            mcap = fast.market_cap if hasattr(fast, 'market_cap') else info.get('marketCap', 0.0)
            
            if price is None or price <= 0:
                metrics[symbol] = {"symbol": symbol, "error": "invalid"}
                continue
                
            # Fetch balance sheet
            bs = t.balance_sheet
            
            total_assets = safe_get(bs, "Total Assets")
            total_debt = safe_get(bs, "Total Debt")
            cash = safe_get(bs, "Cash And Cash Equivalents")
            receivables = safe_get(bs, "Net Receivables") 
            if receivables == 0.0:
                 receivables = safe_get(bs, "Accounts Receivable")
            
            # AAOIFI Ratios
            denominator = total_assets if total_assets > 0 else mcap
            
            debt_ratio = (total_debt / denominator) if denominator else 0.0
            liquidity_ratio = (cash / denominator) if denominator else 0.0
            receivables_ratio = (receivables / denominator) if denominator else 0.0
            
            metrics[symbol] = {
                "symbol": symbol,
                "name": name,
                "price": price,
                "market_cap": mcap,
                "beta": info.get("beta", 1.0) if info.get("beta") is not None else 1.0,
                "pe": info.get("trailingPE", 0.0) if info.get("trailingPE") is not None else 0.0,
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "dividend_yield": info.get("dividendYield", 0.0) if info.get("dividendYield") is not None else 0.0,
                "total_assets": total_assets,
                "total_debt": total_debt,
                "cash_and_equivalents": cash,
                "net_receivables": receivables,
                "debt_ratio": debt_ratio,
                "liquidity_ratio": liquidity_ratio,
                "receivables_ratio": receivables_ratio,
                "is_compliant": bool(debt_ratio < 0.33 and liquidity_ratio < 0.33 and receivables_ratio < 0.49)
            }
            success_count += 1
            
        except Exception as e:
            err_msg = str(e).lower()
            if "delisted" in err_msg or "not found" in err_msg or "404" in err_msg:
                metrics[symbol] = {"symbol": symbol, "error": "invalid"}
            elif "too many requests" in err_msg or "429" in err_msg:
                print(f"Yahoo Rate Limit Hit at symbol {symbol}. Pausing until tomorrow.", flush=True)
                break
            else:
                metrics[symbol] = {"symbol": symbol, "error": "transient_failed"}
                
        # Random sleep to avoid getting blocked
        time.sleep(random.uniform(0.5, 1.5))

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Batch complete. Total metrics database size: {len(metrics)}", flush=True)
    print("Saved to halal_metrics.json", flush=True)

if __name__ == "__main__":
    main()
